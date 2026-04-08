"""
Carga datos reales de catálogo: centros SCC (Sambil Chacao) y SLC (Sambil La Candelaria).

- SCC-T1…SCC-T8: según el PDF «Sambil Caracas (1).pdf» (Chacao); imágenes planas TOMA 1A/1B, TOMA 2…
- SLC: carpetas con nomenclatura histórica CAND-* bajo «Sambil La Candelaria»; se relacionan con
  la misma *lógica de capítulos* que el PDF de Chacao (accesos/sur → gigantografías por plaza →
  cinturones y pendones), no hay PDF de Candelaria en el repositorio. SLC-T1A / SLC-T1B coinciden
  con el inventario oficial (ascensor entrada sur: vista calle / vista mall).

Uso (puedes pasar una o ambas carpetas):
  python manage.py seed_production_catalog \\
    --chacao-dir=\"…/Sambil Chacao\" \\
    --candelaria-dir=\"…/Sambil La Candelaria\"

- No repite la importación SCC ni SLC si ya constó en el workspace (salvo --force).
- Exige el primer usuario «Administrador marketplace» de ese workspace (date_joined, id) como
  referencia de carga (`Workspace.catalog_seed_feeder`).

Idempotencia: centros por (workspace, slug); tomas por código; con --force la galería se sustituye.
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
from apps.malls.models import ShoppingCenter
from apps.users.models import UserProfile
from apps.workspaces.models import Workspace
from apps.workspaces.utils import get_default_workspace

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


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


def _slc_toma_definitions():
    """
    Una fila por carpeta bajo «Sambil La Candelaria». Orden aproximado al PDF de Chacao:
    (1) accesos / sur / ascensor, (2) gigantografías por plaza, (3) cinturones AB, (4) pendón PE,
    (5) cinturones NP/NM/NG/NS.

    Canon mensual en USD: el PDF entregado es de Chacao; aquí va 1.00 como marcador hasta cargar
    tarifario real en el admin (el texto lo indica).
    """
    _p = Decimal("1.00")
    return [
        {
            "code": "SLC-T1A",
            "source_folder": "CAND-SUR-A00",
            "type": AdSpaceType.ELEVATOR,
            "title": "Ascensor entrada sur — vista calle",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Entrada sur",
            "level": "",
            "material": "",
            "description": (
                "Espacio publicitario asociado al ascensor en entrada sur (referencia a calle). "
                "Imágenes: carpeta histórica CAND-SUR-A00 (planos espacio 5). "
                "Precio mensual (USD): pendiente de asignar en administración (valor 1,00 es marcador de importación)."
            ),
            "location_description": "Sambil La Candelaria — sector sur.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T1B",
            "source_folder": "CAND-AB-A01",
            "type": AdSpaceType.ELEVATOR,
            "title": "Ascensor entrada sur — vista interior (mall)",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Entrada sur — interior",
            "level": "",
            "material": "",
            "description": (
                "Espacio publicitario asociado al ascensor en entrada sur (vista hacia el interior del mall). "
                "Imágenes: CAND-AB-A01. "
                "Precio mensual (USD): pendiente de asignar en administración (valor 1,00 es marcador de importación)."
            ),
            "location_description": "Sambil La Candelaria — acceso interior.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T2",
            "source_folder": "CAND-AB-PA01-ACC N",
            "type": AdSpaceType.OTHER,
            "title": "Pasillo acceso PA01 — Acceso norte (código CAND)",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Acceso / pasillo",
            "level": "",
            "material": "",
            "description": (
                "Superficie referenciada por la carpeta histórica CAND-AB-PA01-ACC N (aprox. equivalente a "
                "«accesos / circulación» en el PDF de Chacao). "
                "Precio mensual (USD): pendiente de asignar en administración."
            ),
            "location_description": "La Candelaria — nomenclatura interna PA01 / ACC N.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T3",
            "source_folder": "CAND-ZG01-PZA E",
            "type": AdSpaceType.GIGANTOGRAFIA_FACHADA,
            "title": "Gigantografía — ZG01 Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "",
            "material": "",
            "description": (
                "Formato grande (ZG) en Plaza Este; análogo a capítulo de gigantografías/fachadas del PDF de Chacao. "
                "Precio y medidas: completar en administración."
            ),
            "location_description": "Plaza Este — CAND-ZG01-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T4",
            "source_folder": "CAND-ZG01-PZA O",
            "type": AdSpaceType.GIGANTOGRAFIA_FACHADA,
            "title": "Gigantografía — ZG01 Plaza Oeste",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Oeste",
            "level": "",
            "material": "",
            "description": (
                "Formato grande (ZG) en Plaza Oeste. Precio y medidas: completar en administración."
            ),
            "location_description": "Plaza Oeste — CAND-ZG01-PZA O.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T5",
            "source_folder": "CAND-AB-CINT00",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón publicitario AB — CINT00",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Cinturón / corredor",
            "level": "Ala baja",
            "material": "",
            "description": (
                "Paquete visual en corredor (cinturón 00), equivalente conceptual a pendones de pasillo del PDF de Chacao. "
                "Medidas y canon: completar en administración."
            ),
            "location_description": "CAND-AB-CINT00.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T6",
            "source_folder": "CAND-AB-CINT00-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón AB — CINT00 frente Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "Ala baja",
            "material": "",
            "description": "Cinturón 00 con referencia a Plaza Este. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-CINT00-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T7",
            "source_folder": "CAND-AB-CINT01-CENTRAL",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón AB — CINT01 central",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Corredor central",
            "level": "Ala baja",
            "material": "",
            "description": "Cinturón central 01. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-CINT01-CENTRAL.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T8",
            "source_folder": "CAND-AB-CINT02-LAT",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón AB — CINT02 lateral",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Corredor lateral",
            "level": "Ala baja",
            "material": "",
            "description": "Cinturón lateral 02. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-CINT02-LAT.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T9",
            "source_folder": "CAND-AB-CINT02-LAT-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón AB — CINT02 lateral Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "Ala baja",
            "material": "",
            "description": "Cinturón 02 lateral con referencia Plaza Este. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-CINT02-LAT-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T10",
            "source_folder": "CAND-AB-CINT03-LAT",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón AB — CINT03 lateral",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Corredor lateral",
            "level": "Ala baja",
            "material": "",
            "description": "Cinturón lateral 03. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-CINT03-LAT.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T11",
            "source_folder": "CAND-AB-CINT03-LAT-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón AB — CINT03 lateral Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "Ala baja",
            "material": "",
            "description": "Cinturón 03 lateral con referencia Plaza Este. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-CINT03-LAT-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T12",
            "source_folder": "CAND-AB-PE02",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Pendón — PE02 (ala baja)",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Pasillo / circulación",
            "level": "Ala baja",
            "material": "",
            "description": "Superficie PE02. Medidas y canon: completar en administración.",
            "location_description": "CAND-AB-PE02.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T13",
            "source_folder": "CAND-NP-CINT01-CENTRAL-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón NP — CINT01 central Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "",
            "material": "",
            "description": "Cinturón nomenclatura NP. Medidas y canon: completar en administración.",
            "location_description": "CAND-NP-CINT01-CENTRAL-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T14",
            "source_folder": "CAND-NP-CINT04-CENTRAL",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón NP — CINT04 central",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Corredor central",
            "level": "",
            "material": "",
            "description": "Cinturón NP CINT04. Medidas y canon: completar en administración.",
            "location_description": "CAND-NP-CINT04-CENTRAL.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T15",
            "source_folder": "CAND-NM-CINT02-CENTRAL-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón NM — CINT02 central Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "",
            "material": "",
            "description": "Cinturón nomenclatura NM. Medidas y canon: completar en administración.",
            "location_description": "CAND-NM-CINT02-CENTRAL-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T16",
            "source_folder": "CAND-NG-CINT03-CENTRAL",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón NG — CINT03 central",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Corredor central",
            "level": "",
            "material": "",
            "description": "Cinturón nomenclatura NG. Medidas y canon: completar en administración.",
            "location_description": "CAND-NG-CINT03-CENTRAL.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T17",
            "source_folder": "CAND-NG-CINT03-CENTRAL-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón NG — CINT03 central Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "",
            "material": "",
            "description": "Cinturón NG con referencia Plaza Este. Medidas y canon: completar en administración.",
            "location_description": "CAND-NG-CINT03-CENTRAL-PZA E.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T18",
            "source_folder": "CAND-NS-CINT05-CENTRAL",
            "type": AdSpaceType.PENDON_PASILLO,
            "title": "Cinturón NS — CINT05 central",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Corredor central",
            "level": "",
            "material": "",
            "description": "Cinturón nomenclatura NS. Medidas y canon: completar en administración.",
            "location_description": "CAND-NS-CINT05-CENTRAL.",
            "production_specs": "",
            "installation_notes": "",
            "hem_pocket_top_cm": None,
        },
        {
            "code": "SLC-T19",
            "source_folder": "CAND-NS-CINT05-CENTRAL-PZA E",
            "type": AdSpaceType.PENDON_PLAZA,
            "title": "Cinturón NS — CINT05 central Plaza Este",
            "monthly_price_usd": _p,
            "width": None,
            "height": None,
            "quantity": 1,
            "double_sided": False,
            "venue_zone": "Plaza Este",
            "level": "",
            "material": "",
            "description": "Cinturón NS con referencia Plaza Este. Medidas y canon: completar en administración.",
            "location_description": "CAND-NS-CINT05-CENTRAL-PZA E.",
            "production_specs": "",
            "installation_notes": "",
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
    help = (
        "Carga centros SCC y SLC; tomas SCC desde carpeta Chacao; tomas SLC desde subcarpetas CAND-* (La Candelaria)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--chacao-dir",
            type=str,
            default="",
            help="Carpeta con imágenes TOMA 1A/1B, TOMA 2… (Sambil Chacao). Opcional si pasas solo --candelaria-dir.",
        )
        parser.add_argument(
            "--candelaria-dir",
            type=str,
            default="",
            help="Carpeta «Sambil La Candelaria» con subcarpetas CAND-*. Opcional si pasas solo --chacao-dir.",
        )
        parser.add_argument(
            "--centers-only",
            action="store_true",
            help="Solo crea o actualiza los centros SCC y SLC (sin tomas ni imágenes).",
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

        chacao_raw = (options.get("chacao_dir") or "").strip()
        candelaria_raw = (options.get("candelaria_dir") or "").strip()
        centers_only = bool(options.get("centers_only"))
        force = bool(options.get("force"))

        if not centers_only and not chacao_raw and not candelaria_raw:
            raise CommandError(
                "Indica --chacao-dir y/o --candelaria-dir, o usa --centers-only."
            )

        chacao_dir = Path(chacao_raw).expanduser().resolve() if chacao_raw else None
        candelaria_dir = Path(candelaria_raw).expanduser().resolve() if candelaria_raw else None

        if not centers_only and chacao_raw and (not chacao_dir or not chacao_dir.is_dir()):
            raise CommandError(f"No existe el directorio de imágenes Chacao: {chacao_dir}")
        if not centers_only and candelaria_raw and (not candelaria_dir or not candelaria_dir.is_dir()):
            raise CommandError(f"No existe el directorio de imágenes La Candelaria: {candelaria_dir}")

        feeder = None
        if not centers_only:
            feeder = _first_marketplace_admin_for_workspace(ws)
            if feeder is None:
                raise CommandError(
                    "No hay ningún usuario con rol «Administrador marketplace» vinculado a este "
                    "workspace. Crea primero ese usuario para el owner y vuelve a ejecutar el comando."
                )

        centers_spec = [
            {
                "slug": "scc",
                "name": "Sambil Chacao",
                "city": "Caracas",
                "district": "Chacao",
                "address": "Av. Libertador, Chacao, Caracas",
                "listing_order": 10,
                "description": "Centro comercial Sambil Chacao (Caracas).",
            },
            {
                "slug": "slc",
                "name": "Sambil La Candelaria",
                "city": "Caracas",
                "district": "La Candelaria",
                "address": "La Candelaria, Caracas",
                "listing_order": 20,
                "description": "Centro comercial Sambil La Candelaria (Caracas).",
            },
        ]

        with transaction.atomic():
            ws_locked = ws
            if not centers_only:
                ws_locked = Workspace.objects.select_for_update().get(pk=ws.pk)
                if not force:
                    if chacao_dir is not None and ws_locked.catalog_scc_seeded_at:
                        raise CommandError(
                            "Las tomas SCC (Chacao) ya fueron importadas para este workspace. "
                            "Usa --force para volver a cargarlas (sobrescribe datos e imágenes)."
                        )
                    if candelaria_dir is not None and ws_locked.catalog_slc_seeded_at:
                        raise CommandError(
                            "Las tomas SLC (La Candelaria) ya fueron importadas para este workspace. "
                            "Usa --force para volver a cargarlas (sobrescribe datos e imágenes)."
                        )

            scc = None
            slc = None
            for row in centers_spec:
                center, created = ShoppingCenter.objects.update_or_create(
                    workspace=ws,
                    slug=row["slug"],
                    defaults={
                        "name": row["name"],
                        "city": row["city"],
                        "district": row["district"],
                        "address": row["address"],
                        "country": "Venezuela",
                        "on_homepage": True,
                        "listing_order": row["listing_order"],
                        "marketplace_catalog_enabled": True,
                        "is_active": True,
                        "description": row["description"],
                    },
                )
                verb = "Creado" if created else "Actualizado"
                self.stdout.write(self.style.SUCCESS(f"{verb} centro {row['slug']}: {row['name']}"))
                if row["slug"] == "scc":
                    scc = center
                elif row["slug"] == "slc":
                    slc = center

            if centers_only:
                self.stdout.write(self.style.SUCCESS("Listo (solo centros)."))
                return

            if chacao_dir is not None:
                assert scc is not None
                for spec in _scc_toma_definitions():
                    code = spec["code"]
                    paths = _collect_image_paths(chacao_dir, code)
                    if not paths:
                        raise CommandError(
                            f"No se encontraron imágenes para {code} en {chacao_dir}. "
                            "Revisa los nombres de archivo (TOMA 1A/1B, TOMA 2, …)."
                        )

                    defaults = {k: v for k, v in spec.items() if k != "code"}
                    defaults["shopping_center"] = scc
                    defaults["status"] = AdSpaceStatus.AVAILABLE
                    defaults["is_active"] = True

                    ad, _created = AdSpace.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                    _apply_toma_gallery(ad, paths)

                    self.stdout.write(
                        self.style.SUCCESS(f"Toma {code}: {len(paths)} imagen(es) — {spec['title']}")
                    )

            if candelaria_dir is not None:
                assert slc is not None
                for spec in _slc_toma_definitions():
                    code = spec["code"]
                    folder = spec["source_folder"]
                    paths = _collect_cand_folder_images(candelaria_dir, folder)
                    if not paths:
                        raise CommandError(
                            f"No se encontraron imágenes para {code} en la carpeta «{folder}» "
                            f"bajo {candelaria_dir}."
                        )

                    defaults = {k: v for k, v in spec.items() if k not in ("code", "source_folder")}
                    defaults["shopping_center"] = slc
                    defaults["status"] = AdSpaceStatus.AVAILABLE
                    defaults["is_active"] = True

                    ad, _created = AdSpace.objects.update_or_create(
                        code=code,
                        defaults=defaults,
                    )
                    _apply_toma_gallery(ad, paths)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Toma {code}: {len(paths)} imagen(es) — {spec['title']} [{folder}]"
                        )
                    )

            if not centers_only:
                now = timezone.now()
                audit_updates: dict = {}
                if chacao_dir is not None:
                    audit_updates["catalog_scc_seeded_at"] = now
                if candelaria_dir is not None:
                    audit_updates["catalog_slc_seeded_at"] = now
                if ws_locked.catalog_seed_feeder_id is None:
                    audit_updates["catalog_seed_feeder_id"] = feeder.pk
                if audit_updates:
                    Workspace.objects.filter(pk=ws_locked.pk).update(**audit_updates)
                self.stdout.write(
                    self.style.NOTICE(
                        f"Referencia de carga: administrador marketplace inicial «{feeder.username}» "
                        f"(usuario más antiguo con ese rol en el workspace)."
                    )
                )

        parts = []
        if chacao_dir is not None:
            parts.append("SCC (SCC-T1…SCC-T8)")
        if candelaria_dir is not None:
            parts.append("SLC (SLC-T1A/T1B y SLC-T2…SLC-T19)")
        self.stdout.write(self.style.SUCCESS(f"Catálogo listo: {', '.join(parts)}."))
