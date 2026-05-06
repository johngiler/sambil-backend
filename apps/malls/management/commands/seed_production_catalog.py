"""
Seed de catálogo en producción.

Flujo:

1) El comando recibe **siempre** un PDF (`--pdf`).
2) Parsea el PDF y genera `data.json` normalizado (se sobreescribe en cada ejecución).
3) Valida existencia de centro/tomas y aplica cambios a BD (`ShoppingCenter` + `AdSpace`).
4) Imágenes opcionales: si se pasan y se encuentran, se cargan a galería/portada.

Nota: el parser actual es heurístico (texto + detección de “TOMA n”). Si un PDF usa una
estructura distinta, el JSON resultante puede traer campos null y se ajusta el parser.

"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.ad_spaces.gallery import sync_cover_from_gallery
from apps.ad_spaces.models import AdSpace, AdSpaceImage, AdSpaceStatus, AdSpaceType
from apps.malls.catalog_pdf_parser import (
    _short_sambil_slug_candidates,
    parse_catalog_pdf_to_json_bundle,
    write_bundle_json,
)
from apps.malls.models import ShoppingCenter
from apps.users.models import UserProfile
from apps.workspaces.models import Workspace
from apps.workspaces.utils import get_default_workspace

_DATA_JSON_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "catalog" / "data.json"
).resolve()

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _dec(value):
    """Convierte string/number a Decimal; deja None."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    s = str(value).strip()
    if s == "":
        return None
    return Decimal(s)


def _validate_existing(ws: Workspace, *, center_slug: str, space_codes: list[str], force: bool) -> None:
    """
    Validación mínima:
    - `ShoppingCenter.slug` es único por workspace (update_or_create lo resuelve).
    - `AdSpace.code` es único global; si existe y apunta a otro centro del mismo workspace,
      por defecto se bloquea para no “mover” tomas entre centros.
    """
    if not space_codes:
        return
    existing = (
        AdSpace.objects.filter(code__in=space_codes)
        .select_related("shopping_center")
        .only("id", "code", "shopping_center_id", "shopping_center__slug", "shopping_center__workspace_id")
    )
    bad: list[str] = []
    for row in existing:
        sc = getattr(row, "shopping_center", None)
        if sc is None:
            continue
        if sc.workspace_id != ws.pk:
            bad.append(f"{row.code} (workspace distinto: {sc.slug})")
            continue
        if sc.slug != center_slug:
            bad.append(f"{row.code} (ya existe en {sc.slug})")
    if bad and not force:
        raise CommandError(
            "Conflicto: hay códigos de toma ya existentes en otro centro. "
            "Usa --force si estás seguro.\n- " + "\n- ".join(bad)
        )


def _resolve_center_slug_for_apply(ws: Workspace, parsed_center: dict) -> str:
    """
    Evita duplicados si el slug inferido cambió (p. ej. antes `sambil-valencia`, ahora `svl`).
    Si existe un centro con el mismo nombre en el workspace, se reutiliza y se renombra el slug
    (si está libre).
    """
    desired = str((parsed_center or {}).get("slug") or "").strip()
    name = str((parsed_center or {}).get("name") or "").strip()
    if not desired:
        return desired
    if not name:
        return desired

    # Si el slug deseado colisiona con otro centro, intenta alternativas cortas (Sambil …)
    if ShoppingCenter.objects.filter(workspace=ws, slug=desired).exclude(name__iexact=name).exists():
        for cand in _short_sambil_slug_candidates(name):
            if not ShoppingCenter.objects.filter(workspace=ws, slug=cand).exclude(name__iexact=name).exists():
                desired = cand
                break

    by_slug = ShoppingCenter.objects.filter(workspace=ws, slug=desired).only("id").first()
    if by_slug:
        return desired

    existing = (
        ShoppingCenter.objects.filter(workspace=ws, name__iexact=name)
        .only("id", "slug", "name")
        .first()
    )
    if not existing:
        return desired

    if existing.slug == desired:
        return desired

    # Renombra el slug si está libre
    exists_desired = ShoppingCenter.objects.filter(workspace=ws, slug=desired).exists()
    if not exists_desired:
        ShoppingCenter.objects.filter(pk=existing.pk).update(slug=desired)
        return desired
    # Si está ocupado, usa el slug existente (no duplicar).
    return existing.slug


def _code_prefix_for_center_slug(center_slug: str) -> str:
    """
    Prefijo para códigos de toma `XXX-Tn`:
    - Preserva históricos: scc -> SCC, slc -> SLC
    - Resto: slug en mayúsculas (3 letras típicamente: svl -> SVL, smg -> SMG)
    """
    s = (center_slug or "").strip().lower()
    if s == "scc":
        return "SCC"
    if s == "slc":
        return "SLC"
    return (center_slug or "").strip().upper()


def _rewrite_space_codes(spaces: list[dict], *, new_prefix: str) -> None:
    """
    Reescribe `code` en cada toma a `<new_prefix>-T...` manteniendo el sufijo `Tn[A-Z]`.
    """
    if not new_prefix:
        return
    for row in spaces:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        m = re.search(r"-T(?P<suf>\d{1,2}[A-Z]?)$", code)
        if not m:
            continue
        row["code"] = f"{new_prefix}-T{m.group('suf')}"


def _patterns_for_scc_code(code: str) -> list[re.Pattern[str]]:
    """Asocia códigos SCC-Tn con prefijos de archivo en la carpeta de imágenes."""
    if code == "SCC-T1":
        return [
            re.compile(r"^TOMA\s*1A", re.IGNORECASE),
            re.compile(r"^TOMA\s*1B", re.IGNORECASE),
        ]
    m = re.match(r"^SCC-T(\d+)$", code)
    if not m:
        raise ValueError(f"Código de toma no soportado: {code}")
    n = int(m.group(1))
    if n < 2 or n > 8:
        raise ValueError(f"Código de toma no soportado: {code}")
    return [re.compile(rf"^TOMA\s*{n}(?:[\s\._\(]|$)", re.IGNORECASE)]


def _is_readable_image_file(path: Path) -> bool:
    """True si el archivo es una imagen raster legible (Pillow); excluye vacíos y corruptos."""
    from PIL import Image, UnidentifiedImageError

    try:
        if not path.is_file():
            return False
        if path.stat().st_size == 0:
            return False
        with Image.open(path) as im:
            im.verify()
    except (OSError, UnidentifiedImageError, ValueError, SyntaxError):
        return False
    return True


def _filter_seed_image_paths(paths: list[Path]) -> tuple[list[Path], list[str]]:
    """Devuelve rutas válidas y nombres omitidos (no imagen / corrupto / 0 bytes)."""
    valid: list[Path] = []
    skipped: list[str] = []
    for p in paths:
        if _is_readable_image_file(p):
            valid.append(p)
        else:
            skipped.append(p.name)
    return valid, skipped


def _sort_gallery_paths(paths: list[Path]) -> list[Path]:
    """Orden: archivo base sin (n) primero; luego (1), (2), …; después orden alfabético del nombre."""

    def sort_key(p: Path) -> tuple:
        stem = p.stem
        m = re.match(r"^(?P<base>.+)\((?P<idx>\d+)\)$", stem)
        if m:
            return (m.group("base").strip().lower(), 1, int(m.group("idx")))
        return (stem.lower(), 0, 0)

    return sorted(paths, key=sort_key)


def _collect_image_paths(chacao_dir: Path, code: str) -> list[Path]:
    patterns = _patterns_for_scc_code(code)
    found: list[Path] = []
    for p in chacao_dir.iterdir():
        if not p.is_file() or p.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        name = p.name
        if any(pat.search(name) for pat in patterns):
            found.append(p)
    return _sort_gallery_paths(found)


def _collect_cand_folder_images(candelaria_dir: Path, folder_name: str) -> list[Path]:
    """Todas las imágenes dentro de una subcarpeta CAND-* (sin recorrer otras tomas)."""
    sub = candelaria_dir / folder_name
    if not sub.is_dir():
        return []
    found: list[Path] = []
    for p in sub.iterdir():
        if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES:
            found.append(p)
    return _sort_gallery_paths(found)


def _collect_images_for_code(images_dir: Path, code: str) -> list[Path]:
    """
    Heurística de imágenes cuando el seed viene de PDF:
    - Si el código es SCC-… usamos el mapeo legacy (patrones `TOMA 1A/1B`, `TOMA 2`, etc.).
    - Para el resto, buscamos por patrón `TOMA n[sufijo]` derivado del código `*-Tn[sufijo]`.
    """
    if not images_dir or not images_dir.is_dir():
        return []
    c = (code or "").strip()
    if not c:
        return []
    if c.startswith("SCC-"):
        return _collect_image_paths(images_dir, c)
    m = re.search(r"-T(?P<n>\d{1,2})(?P<suf>[A-Z])?$", c)
    if not m:
        return []
    n = m.group("n")
    suf = m.group("suf") or ""
    pat = re.compile(rf"^TOMA\s*{n}{suf}(?:[\s\._\(]|$)", re.IGNORECASE)
    found: list[Path] = []
    for p in images_dir.iterdir():
        if not p.is_file() or p.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        if pat.search(p.name):
            found.append(p)
    return _sort_gallery_paths(found)


def _slc_toma_definitions():
    """
    Catálogo según PDF «Sambil La Candelaria.pdf» (espacios publicitarios).
    Cada `source_folder` enlaza la carpeta CAND-* del paquete de fotos (mapeo plano ↔ ficha).

    Las carpetas CAND-NM/NG/NS adicionales no tienen ficha numérica propia en el PDF; no se crean
    tomas extra: puedes asociar esas fotos manualmente o ampliar este listado cuando lo definan.
    """
    return [
        {
            "code": "SLC-T1A",
            "source_folder": "CAND-SUR-A00",
            "type": AdSpaceType.ELEVATOR,
            "title": "TOMA 1A — Ascensor cara a la calle",
            "monthly_price_usd": Decimal("3200.00"),
            "width": Decimal("2.43"),
            "height": Decimal("7.50"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Entrada sur",
            "level": "",
            "material": "Vinil",
            "description": (
                "Ascensor de cara a la calle. Vista hacia la calle. "
                "Medidas 2,43 × 7,50 m, cantidad 1."
            ),
            "location_description": "Entrada sur, Sambil La Candelaria.",
            "production_specs": "Material: vinil.",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T1B",
            "source_folder": "CAND-AB-A01",
            "type": AdSpaceType.ELEVATOR,
            "title": "TOMA 1B — Ascensor cara al mall",
            "monthly_price_usd": Decimal("1700.00"),
            "width": Decimal("2.43"),
            "height": Decimal("4.00"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Salida sur",
            "level": "",
            "material": "Vinil",
            "description": (
                "Ascensor de cara al interior del centro comercial. Vista interna. "
                "Medidas 2,43 × 4,00 m, cantidad 1."
            ),
            "location_description": "Salida sur (interior), Sambil La Candelaria.",
            "production_specs": "Material: vinil.",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T2",
            "source_folder": "CAND-AB-PE02",
            "type": AdSpaceType.BANNER,
            "title": "TOMA 2 — Acceso al estacionamiento vertical",
            "monthly_price_usd": Decimal("1200.00"),
            "width": Decimal("1.90"),
            "height": Decimal("1.10"),
            "quantity": 2,
            "double_sided": False,
            "venue_zone": "Puertas de acceso al estacionamiento vertical",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": (
                "Ubicación en nivel Andrés Bello, puertas de acceso al estacionamiento vertical. "
                "Medidas 1,90 × 1,10 m, cantidad 2."
            ),
            "location_description": "Parte superior de las puertas, nivel Andrés Bello.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Montaje en parte superior de las puertas.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T3A",
            "source_folder": "CAND-AB-CINT02-LAT",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "TOMA 3A — Cintillo lateral plaza oeste",
            "monthly_price_usd": Decimal("1500.00"),
            "width": Decimal("7.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Laterales plaza oeste",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": "Cintillo 7,00 × 0,48 m, cantidad 1, laterales plaza oeste.",
            "location_description": "Nivel Andrés Bello, laterales plaza oeste.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T3B",
            "source_folder": "CAND-AB-CINT02-LAT-PZA E",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "TOMA 3B — Cintillo lateral plaza oeste (tramo complementario)",
            "monthly_price_usd": Decimal("1500.00"),
            "width": Decimal("7.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Laterales plaza oeste",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": (
                "Segundo cintillo de la ficha TOMA 3 (mismas medidas y canon que 3A). "
                "Imágenes en carpeta complementaria del paquete."
            ),
            "location_description": "Nivel Andrés Bello, laterales plaza oeste.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T4",
            "source_folder": "CAND-AB-CINT01-CENTRAL",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "TOMA 4 — Cintillo plaza oeste",
            "monthly_price_usd": Decimal("3000.00"),
            "width": Decimal("20.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza oeste",
            "level": "Nivel Miranda (según ficha del PDF)",
            "material": "Vinil impreso sobre PVC",
            "description": (
                "Cintillo 20,00 × 0,48 m, cantidad 1. "
                "El PDF indica ubicación «Nivel Miranda, plaza oeste» (el plano de sección menciona también Andrés Bello)."
            ),
            "location_description": "Plaza oeste; parte superior.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T5A",
            "source_folder": "CAND-AB-CINT00",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "TOMA 5A — Cintillo plaza oeste",
            "monthly_price_usd": Decimal("1000.00"),
            "width": Decimal("2.10"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza oeste",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": "Cintillo 2,10 × 0,48 m, cantidad 1.",
            "location_description": "Nivel Andrés Bello, plaza oeste; parte superior.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T5B",
            "source_folder": "CAND-AB-CINT00-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "TOMA 5B — Cintillo plaza este",
            "monthly_price_usd": Decimal("1000.00"),
            "width": Decimal("2.10"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza este",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": "Cintillo 2,10 × 0,48 m, cantidad 1.",
            "location_description": "Nivel Andrés Bello, plaza este; parte superior.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T6A",
            "source_folder": "CAND-AB-CINT03-LAT",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "TOMA 6A — Cintillo lateral plaza este",
            "monthly_price_usd": Decimal("1500.00"),
            "width": Decimal("7.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Laterales plaza este",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": "Cintillo 7,00 × 0,48 m, cantidad 1.",
            "location_description": "Nivel Andrés Bello, laterales plaza este.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T6B",
            "source_folder": "CAND-AB-CINT03-LAT-PZA E",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "TOMA 6B — Cintillo lateral plaza este (tramo complementario)",
            "monthly_price_usd": Decimal("1500.00"),
            "width": Decimal("7.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Laterales plaza este",
            "level": "Nivel Andrés Bello",
            "material": "Vinil impreso sobre PVC",
            "description": "Segundo cintillo de la ficha TOMA 6 (mismas medidas y canon que 6A).",
            "location_description": "Nivel Andrés Bello, laterales plaza este.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T7A",
            "source_folder": "CAND-NP-CINT01-CENTRAL-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "TOMA 7A — Cintillo plaza este (nivel galería)",
            "monthly_price_usd": Decimal("2000.00"),
            "width": Decimal("13.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza este",
            "level": "Nivel galería",
            "material": "Vinil impreso sobre PVC",
            "description": "Cintillo 13,00 × 0,48 m, cantidad 1. Ubicación: plaza este, nivel galería (texto del PDF).",
            "location_description": "Plaza este, nivel galería; parte superior.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T7B",
            "source_folder": "CAND-NP-CINT04-CENTRAL",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "TOMA 7B — Cintillo plaza este (nivel Miranda)",
            "monthly_price_usd": Decimal("2500.00"),
            "width": Decimal("17.00"),
            "height": Decimal("0.48"),
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza este",
            "level": "Nivel Miranda",
            "material": "Vinil impreso sobre PVC",
            "description": "Cintillo 17,00 × 0,48 m, cantidad 1. Ubicación: plaza este, nivel Miranda (texto del PDF).",
            "location_description": "Plaza este, nivel Miranda; parte superior.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T8",
            "source_folder": "CAND-AB-PA01-ACC N",
            "type": AdSpaceType.BANNER,
            "title": "TOMA 8 — Vidrios acceso norte",
            "monthly_price_usd": Decimal("2000.00"),
            "width": Decimal("1.45"),
            "height": Decimal("0.90"),
            "quantity": 10,
            "double_sided": False,
            "venue_zone": "Acceso norte",
            "level": "Nivel Andrés Bello",
            "material": "Vinil rotulado",
            "description": (
                "Diez piezas de 1,45 × 0,90 m en vidrios de acceso norte, nivel Andrés Bello."
            ),
            "location_description": "Nivel Andrés Bello, acceso norte; parte superior.",
            "production_specs": "Vinil rotulado.",
            "installation_notes": "Parte superior.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T9A",
            "source_folder": "CAND-ZG01-PZA O",
            "type": AdSpaceType.BANNER,
            "title": "TOMA 9A — Vinil jardinera zona gourmet (plaza oeste)",
            "monthly_price_usd": Decimal("1200.00"),
            "width": Decimal("2.10"),
            "height": Decimal("0.77"),
            "quantity": 2,
            "double_sided": False,
            "venue_zone": "Zona gourmet, plaza oeste",
            "level": "",
            "material": "Vinil impreso sobre PVC",
            "description": (
                "Dos piezas 2,10 × 0,77 m en jardinera. "
                "El PDF indica «Plaza oeste zona gourmet» en la ficha 9A."
            ),
            "location_description": "Jardinera, zona gourmet plaza oeste.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Jardinera.",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T9B",
            "source_folder": "CAND-ZG01-PZA E",
            "type": AdSpaceType.BANNER,
            "title": "TOMA 9B — Vinil jardinera zona gourmet (plaza este)",
            "monthly_price_usd": Decimal("1200.00"),
            "width": Decimal("2.10"),
            "height": Decimal("0.77"),
            "quantity": 2,
            "double_sided": False,
            "venue_zone": "Zona gourmet, plaza este",
            "level": "",
            "material": "Vinil impreso sobre PVC",
            "description": (
                "Dos piezas 2,10 × 0,77 m en jardinera. "
                "El PDF indica «Plaza este, zona gourmet» en la ficha 9B."
            ),
            "location_description": "Jardinera, zona gourmet plaza este.",
            "production_specs": "Vinil impreso sobre PVC.",
            "installation_notes": "Jardinera.",
            "hem_pocket_top_cm": None,
        },
    ]


def _scc_toma_definitions():
    """
    Textos y números según el PDF de espacios publicitarios Sambil Caracas (Chacao)
    (archivo de referencia usado para esta carga: «Sambil Caracas (1).pdf»).
    """
    return [
        {
            "code": "SCC-T1",
            "type": AdSpaceType.GIGANTOGRAFIA_FACHADA,
            "title": "Gigantografías fachada Av. Libertador",
            "monthly_price_usd": Decimal("5000.00"),
            "width": Decimal("3.82"),
            "height": Decimal("10.50"),
            "quantity": 3,
            "double_sided": True,
            "venue_zone": "Fachada Av. Libertador",
            "level": "",
            "material": "Lona frontlit",
            "description": (
                "Dos gigantografías verticales (3,82 × 10,50 m, cantidad 2) en fachada izquierda, "
                "ambos sentidos de circulación; una gigantografía horizontal (10,40 × 6,20 m, cantidad 1) "
                "en fachada derecha."
            ),
            "location_description": (
                "Fachada izquierda y derecha sobre Av. Libertador, Sambil Chacao."
            ),
            "production_specs": (
                "Especificaciones para artes y producción — Valla vertical: material lona frontlit, "
                "medias 3,82 × 10,50 m. Valla horizontal: material lona frontlit, medias 10,40 × 6,40 m."
            ),
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SCC-T2",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Pendones Plaza Jardín (balcón y atrio)",
            "monthly_price_usd": Decimal("4500.00"),
            "width": Decimal("0.70"),
            "height": Decimal("1.90"),
            "quantity": 23,
            "double_sided": True,
            "venue_zone": "Plaza Jardín",
            "level": "Diversión, feria, Libertador y acuario",
            "material": "Lona frontlit",
            "description": (
                "Pendones de balcón 0,70 × 1,90 m (cantidad 22) en balcones de los niveles indicados; "
                "pendón de atrio 3,00 × 10,00 m (cantidad 1) en Plaza Jardín. Elementos doble cara."
            ),
            "location_description": "Plaza Jardín; balcones y centro de atrio.",
            "production_specs": (
                "Pendón colgante en centro de atrio: medidas máx. 3,00 × 10,00 m, cantidad 1. "
                "Elementos con forma alusiva al producto o campaña, rotulado por ambas caras, intercalados, "
                "sin interrumpir la visual entre niveles. Pendones de balcón: lona frontlit 0,70 × 1,90 m."
            ),
            "installation_notes": "Prohibido colocar un pendón corrido.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
        {
            "code": "SCC-T3",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Pendones Plaza La Fuente (balcón y atrio)",
            "monthly_price_usd": Decimal("4500.00"),
            "width": Decimal("0.70"),
            "height": Decimal("1.90"),
            "quantity": 23,
            "double_sided": True,
            "venue_zone": "Plaza La Fuente",
            "level": "Diversión, feria, Libertador y acuario",
            "material": "Lona frontlit",
            "description": (
                "Pendones de balcón 0,70 × 1,90 m (cantidad 23) en balcones de los niveles indicados; "
                "pendón de atrio 3,00 × 10,00 m (cantidad 1) en la plaza. Elementos doble cara."
            ),
            "location_description": "Plaza La Fuente; balcones y centro de atrio.",
            "production_specs": (
                "Pendón colgante en centro de atrio: medidas máx. 3,00 × 10,00 m, cantidad 1. "
                "Pendones de balcón: lona frontlit 0,70 × 1,90 m."
            ),
            "installation_notes": "Prohibido colocar un pendón corrido.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
        {
            "code": "SCC-T4",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Pendones Plaza Central (balcón y atrio)",
            "monthly_price_usd": Decimal("4500.00"),
            "width": Decimal("0.70"),
            "height": Decimal("1.90"),
            "quantity": 21,
            "double_sided": True,
            "venue_zone": "Plaza Central",
            "level": "Diversión, feria, Libertador y acuario",
            "material": "Lona frontlit",
            "description": (
                "Pendones de balcón 0,70 × 1,90 m (cantidad 20) en balcones de los niveles indicados; "
                "pendón de atrio 3,00 × 10,00 m (cantidad 1) en Plaza Central. Elementos doble cara."
            ),
            "location_description": "Plaza Central; balcones y centro de atrio.",
            "production_specs": (
                "Pendón colgante en centro de atrio: medidas máx. 3,00 × 10,00 m, cantidad 1. "
                "Pendones de balcón: lona frontlit 0,70 × 1,90 m."
            ),
            "installation_notes": "Prohibido colocar un pendón corrido.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
        {
            "code": "SCC-T5",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Pendones pasillo Plaza Jardín – Plaza Central",
            "monthly_price_usd": Decimal("4000.00"),
            "width": Decimal("0.70"),
            "height": Decimal("1.90"),
            "quantity": 47,
            "double_sided": True,
            "venue_zone": "Pasillo Plaza Jardín a Plaza Central",
            "level": "Diversión, feria, Libertador y acuario",
            "material": "Lona frontlit",
            "description": (
                "Pendones de balcón 0,70 × 1,90 m (cantidad 47) en balcones de los niveles indicados. "
                "Elementos doble cara."
            ),
            "location_description": "Pasillo entre Plaza Jardín y Plaza Central.",
            "production_specs": "Lona frontlit 0,70 × 1,90 m.",
            "installation_notes": "Bolsillo hueco 4,5 cm solo en la parte superior.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
        {
            "code": "SCC-T6",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Pendones pasillo Plaza Jardín – Plaza La Fuente",
            "monthly_price_usd": Decimal("2500.00"),
            "width": Decimal("0.70"),
            "height": Decimal("1.90"),
            "quantity": 26,
            "double_sided": True,
            "venue_zone": "Pasillo Plaza Jardín a Plaza La Fuente",
            "level": "Diversión, feria, Libertador y acuario",
            "material": "Lona frontlit",
            "description": (
                "Pendones de balcón 0,70 × 1,90 m (cantidad 26) en balcones de los niveles indicados. "
                "Elementos doble cara."
            ),
            "location_description": "Pasillo entre Plaza Jardín y Plaza La Fuente.",
            "production_specs": "Lona frontlit 0,70 × 1,90 m.",
            "installation_notes": "Bolsillo hueco 4,5 cm solo en la parte superior.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
        {
            "code": "SCC-T7",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Pendones pasillo y Plaza La Música",
            "monthly_price_usd": Decimal("2000.00"),
            "width": Decimal("0.70"),
            "height": Decimal("1.90"),
            "quantity": 10,
            "double_sided": True,
            "venue_zone": "Pasillo Plaza Central – Plaza La Música; Plaza La Música",
            "level": "",
            "material": "Lona frontlit",
            "description": (
                "Pendones de pasillo 0,70 × 1,90 m (cantidad 4), pasillo de Plaza Central a Plaza La Música; "
                "pendones de plaza 0,70 × 1,90 m (cantidad 6) en balcones de Plaza La Música. "
                "Elementos doble cara."
            ),
            "location_description": "Pasillo y balcones de Plaza La Música.",
            "production_specs": "Lona frontlit 0,70 × 1,90 m.",
            "installation_notes": "Bolsillo hueco 4,5 cm solo en la parte superior.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
        {
            "code": "SCC-T8",
            "type": AdSpaceType.PENDON_COLUMNA,
            "title": "Pendones columna pasillo Plaza Central – Plaza El Arte",
            "monthly_price_usd": Decimal("1500.00"),
            "width": Decimal("0.85"),
            "height": Decimal("1.85"),
            "quantity": 6,
            "double_sided": True,
            "venue_zone": "Pasillo Plaza Central a Plaza El Arte",
            "level": "Acuario",
            "material": "Lona frontlit",
            "description": (
                "Pendones de columna 0,85 × 1,85 m (cantidad 6) en columnas del pasillo diagonal, nivel acuario. "
                "Elementos doble cara."
            ),
            "location_description": "Columnas de pasillo diagonal, nivel acuario.",
            "production_specs": "Lona frontlit 0,85 × 1,85 m.",
            "installation_notes": "Bolsillo hueco 4,5 cm solo en la parte superior.",
            "hem_pocket_top_cm": Decimal("4.5"),
        },
    ]


def _first_marketplace_admin_for_workspace(ws: Workspace):
    """
    Primer usuario del workspace con rol administrador marketplace (orden: date_joined, id).
    """
    User = get_user_model()
    return (
        User.objects.filter(
            profile__workspace_id=ws.pk,
            profile__role=UserProfile.Role.ADMIN,
        )
        .order_by("date_joined", "id")
        .first()
    )


def _apply_toma_gallery(ad: AdSpace, paths: list[Path]) -> None:
    ad.gallery_images.all().delete()
    for order, img_path in enumerate(paths):
        with img_path.open("rb") as fh:
            AdSpaceImage.objects.create(
                ad_space=ad,
                image=File(fh, name=img_path.name),
                sort_order=order,
            )
    sync_cover_from_gallery(ad)


class Command(BaseCommand):
    help = "Parsea un PDF de catálogo y siembra centro + tomas (imágenes opcionales)."

    def add_arguments(self, parser):
        parser.add_argument("--pdf", type=str, required=True, help="Ruta al PDF de catálogo (obligatorio).")
        parser.add_argument(
            "--images-dir",
            type=str,
            default="",
            help="Carpeta con imágenes (opcional). Si faltan, se crean tomas sin galería/portada.",
        )
        parser.add_argument(
            "--require-images",
            action="store_true",
            help="Falla si faltan imágenes (modo estricto). Por defecto, crea/actualiza tomas aunque no haya fotos.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parsea el PDF y genera data.json, pero no escribe en BD.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Vuelve a importar aunque SCC o SLC ya estén marcados como cargados en el workspace.",
        )

    def handle(self, *args, **options):
        ws = get_default_workspace()
        if not ws:
            raise CommandError(
                "No hay workspace activo. Define DEFAULT_WORKSPACE_SLUG o crea un workspace."
            )

        pdf_raw = (options.get("pdf") or "").strip()
        images_raw = (options.get("images_dir") or "").strip()
        allow_missing_images = not bool(options.get("require_images"))
        dry_run = bool(options.get("dry_run"))
        force = bool(options.get("force"))

        pdf_path = Path(pdf_raw).expanduser().resolve()
        if not pdf_path.is_file():
            raise CommandError(f"No existe el PDF: {pdf_path}")
        images_dir = Path(images_raw).expanduser().resolve() if images_raw else None
        if images_dir is not None and not images_dir.is_dir():
            raise CommandError(f"No existe el directorio de imágenes: {images_dir}")

        # 1) PDF → JSON normalizado (se sobreescribe siempre)
        try:
            parsed = parse_catalog_pdf_to_json_bundle(pdf_path)
        except Exception as exc:
            raise CommandError(f"No se pudo parsear el PDF: {exc}") from exc

        if dry_run:
            write_bundle_json(parsed, _DATA_JSON_PATH)
            self.stdout.write(self.style.SUCCESS(f"Generado data.json: {_DATA_JSON_PATH}"))
            self.stdout.write(
                self.style.NOTICE(
                    f"Centro detectado: {parsed.center.get('name')} (slug={parsed.center.get('slug')}) · "
                    f"Tomas detectadas: {len(parsed.ad_spaces)}"
                )
            )
            self.stdout.write(self.style.SUCCESS("Dry-run: no se escribieron cambios en BD."))
            return

        feeder = None
        feeder = _first_marketplace_admin_for_workspace(ws)
        if feeder is None:
            raise CommandError(
                "No hay ningún usuario con rol «Administrador marketplace» vinculado a este "
                "workspace. Crea primero ese usuario para el owner y vuelve a ejecutar el comando."
            )

        center_slug = _resolve_center_slug_for_apply(ws, parsed.center)
        if not center_slug:
            raise CommandError("El parser no pudo inferir center.slug.")
        # Alinear slug/prefijo/códigos con la versión final (evita colisiones entre centros como Maracaibo vs Margarita).
        parsed.center["slug"] = center_slug
        parsed.center["code_prefix"] = _code_prefix_for_center_slug(center_slug)
        _rewrite_space_codes(parsed.ad_spaces, new_prefix=parsed.center["code_prefix"])

        write_bundle_json(parsed, _DATA_JSON_PATH)
        self.stdout.write(self.style.SUCCESS(f"Generado data.json: {_DATA_JSON_PATH}"))
        self.stdout.write(
            self.style.NOTICE(
                f"Centro detectado: {parsed.center.get('name')} (slug={parsed.center.get('slug')}) · "
                f"Tomas detectadas: {len(parsed.ad_spaces)}"
            )
        )
        space_codes = [
            str(x.get("code") or "").strip()
            for x in parsed.ad_spaces
            if isinstance(x, dict)
        ]
        space_codes = [c for c in space_codes if c]
        _validate_existing(ws, center_slug=center_slug, space_codes=space_codes, force=force)

        with transaction.atomic():
            # Centro (siempre existe antes de tomas)
            c = parsed.center
            defaults = {k: v for k, v in c.items() if k not in ("slug", "catalog_pdf_path", "code_prefix")}
            defaults.setdefault("country", "Venezuela")
            defaults.setdefault("on_homepage", True)
            defaults.setdefault("marketplace_catalog_enabled", True)
            defaults.setdefault("is_active", True)
            center, created = ShoppingCenter.objects.update_or_create(
                workspace=ws,
                slug=center_slug,
                defaults=defaults,
            )
            verb = "Creado" if created else "Actualizado"
            self.stdout.write(self.style.SUCCESS(f"{verb} centro {center.slug}: {center.name}"))

            created_n = updated_n = 0
            for spec in parsed.ad_spaces:
                if not isinstance(spec, dict):
                    continue
                code = str(spec.get("code") or "").strip()
                if not code:
                    continue
                defaults = {k: v for k, v in spec.items() if k != "code"}
                defaults["shopping_center"] = center
                defaults["status"] = AdSpaceStatus.AVAILABLE
                defaults["is_active"] = True
                for dk in ("monthly_price_usd", "width", "height", "hem_pocket_top_cm"):
                    if dk in defaults:
                        defaults[dk] = _dec(defaults[dk])
                # No borrar campos si el parser no los encontró ("" o None).
                for k in (
                    "description",
                    "material",
                    "location_description",
                    "level",
                    "venue_zone",
                    "production_specs",
                    "installation_notes",
                ):
                    if k in defaults and (defaults[k] is None or str(defaults[k]).strip() == ""):
                        defaults.pop(k, None)
                # Si el parser no pudo inferir type, no lo sobrescribimos al actualizar.
                if defaults.get("type") in ("", None):
                    defaults.pop("type", None)
                # monthly_price_usd es requerido para crear.
                if "monthly_price_usd" not in defaults or defaults.get("monthly_price_usd") is None:
                    raise CommandError(f"{code}: falta Canon mensual en el PDF (monthly_price_usd).")
                ad, was_created = AdSpace.objects.update_or_create(code=code, defaults=defaults)
                created_n += 1 if was_created else 0
                updated_n += 0 if was_created else 1

                # Imágenes opcionales: intentamos patrones legacy cuando el prefijo coincide.
                paths: list[Path] = []
                if images_dir is not None:
                    paths = _collect_images_for_code(images_dir, code)
                paths, skipped_img = _filter_seed_image_paths(paths)
                for name in skipped_img:
                    self.stdout.write(self.style.WARNING(f"{code}: omitido «{name}» (no imagen válida)."))
                if paths:
                    _apply_toma_gallery(ad, paths)
                elif not allow_missing_images and images_dir is not None:
                    raise CommandError(
                        f"{code}: no se encontraron imágenes válidas en {images_dir} y está activo --require-images."
                    )

            now = timezone.now()
            audit_updates: dict = {}
            if center.slug == "scc":
                audit_updates["catalog_scc_seeded_at"] = now
            if center.slug == "slc":
                audit_updates["catalog_slc_seeded_at"] = now
            if ws.catalog_seed_feeder_id is None:
                audit_updates["catalog_seed_feeder_id"] = feeder.pk
            if audit_updates:
                Workspace.objects.filter(pk=ws.pk).update(**audit_updates)

        self.stdout.write(
            self.style.SUCCESS(
                f"Catálogo listo: {center_slug} · tomas={len(space_codes)} · creadas={created_n} · actualizadas={updated_n}."
            )
        )
