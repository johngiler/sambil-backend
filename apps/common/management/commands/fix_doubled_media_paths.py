"""
Repara rutas de ImageField tras el bug de WebP (ruta completa en ``FieldFile.save`` → prefijos
duplicados), renombra ``covers/*`` legacy a ``centers/covers`` y ``spaces/covers``, colapsa
``spaces/covers/…/spaces/gallery/…`` y alinea BD con ``.webp`` en disco cuando el raster ya migró.

    python manage.py fix_doubled_media_paths [--dry-run]
"""

from __future__ import annotations

import re

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

# Prefijos duplicados si ``FieldFile.save()`` recibió la ruta completa además de ``upload_to``.
_PREFIXES = (
    "spaces/gallery",
    "spaces/covers",
    "centers/covers",
    "covers/spaces",
    "covers/centers",
)


def _dedupe_once(name: str) -> str | None:
    n = name.replace("\\", "/").strip()
    for p in _PREFIXES:
        pat = re.compile(
            rf"^({re.escape(p)}/\d{{4}}/\d{{2}}/)"
            + re.escape(p)
            + r"/\d{4}/\d{2}/(?P<rest>.+)$"
        )
        m = pat.match(n)
        if m:
            return f"{m.group(1)}{m.group('rest')}"
    return None


def dedupe_path_fully(name: str) -> str:
    n = name.replace("\\", "/")
    while True:
        nxt = _dedupe_once(n)
        if nxt is None:
            return n
        n = nxt


def normalize_centers_spaces_prefix(name: str) -> str:
    """``covers/centers`` → ``centers/covers``; ``covers/spaces`` → ``spaces/covers``."""
    n = name.replace("\\", "/").strip()
    if n.startswith("covers/centers/"):
        return "centers/covers/" + n[len("covers/centers/") :]
    if n.startswith("covers/spaces/"):
        return "spaces/covers/" + n[len("covers/spaces/") :]
    return n


def collapse_embedded_gallery_under_spaces_covers(name: str) -> str:
    """
    Bug WebP/Django: copias bajo ``spaces/covers/Y/M/spaces/gallery/Y/M/archivo``.
    Debe quedar ``spaces/covers/Y/M/archivo`` (mismo Y/M que el segmento exterior).
    """
    n = name.replace("\\", "/").strip()
    m = re.match(
        r"^(spaces/covers/\d{4}/\d{2}/)spaces/gallery/\d{4}/\d{2}/(?P<rest>.+)$",
        n,
    )
    if m:
        return f"{m.group(1)}{m.group('rest')}"
    return n


def nested_spaces_covers_gallery_variant(short_name: str) -> str | None:
    """Si ``spaces/covers/Y/M/f`` no existe, el fichero puede estar en la variante anidada."""
    n = short_name.replace("\\", "/").strip()
    m = re.match(r"^(spaces/covers/(\d{4})/(\d{2})/)(?P<rest>.+)$", n)
    if not m:
        return None
    prefix, y, mo, rest = m.group(1), m.group(2), m.group(3), m.group("rest")
    if rest.startswith("spaces/gallery/"):
        return None
    return f"{prefix}spaces/gallery/{y}/{mo}/{rest}"


def webp_raster_alternate_if_missing(name: str) -> str | None:
    """Tras ``ensure_imagefields_webp``, la BD puede seguir apuntando a .jpeg; en disco solo hay .webp."""
    n = name.replace("\\", "/").strip()
    if default_storage.exists(n):
        return n
    if not re.search(r"\.(jpe?g|png|gif)$", n, re.I):
        return None
    w = re.sub(r"\.(jpe?g|png|gif)$", ".webp", n, count=1, flags=re.I)
    if w != n and default_storage.exists(w):
        return w
    return None


def resolve_physical_image_name(name: str) -> str | None:
    """Primera ruta relativa al storage donde el fichero existe (anidada covers, o .webp)."""
    if not name:
        return None
    n = name.replace("\\", "/").strip()
    if default_storage.exists(n):
        return n
    alt = nested_spaces_covers_gallery_variant(n)
    if alt and default_storage.exists(alt):
        return alt
    return webp_raster_alternate_if_missing(n)


def reconcile_stored_path(name: str) -> str:
    n = dedupe_path_fully(name)
    n = normalize_centers_spaces_prefix(n)
    return collapse_embedded_gallery_under_spaces_covers(n)


class Command(BaseCommand):
    help = (
        "Dedplica rutas rotas y normaliza prefijos: centers/covers, spaces/covers, spaces/gallery."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo lista cambios, no escribe en disco ni en la base de datos.",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        from apps.ad_spaces.models import AdSpace, AdSpaceImage
        from apps.malls.models import ShoppingCenter

        fixed = 0
        skipped = 0

        def process_qs(qs, field: str, label: str):
            nonlocal fixed, skipped
            for obj in qs.iterator():
                f = getattr(obj, field)
                name = getattr(f, "name", None) or ""
                if not name:
                    skipped += 1
                    continue
                orig = name
                phys = resolve_physical_image_name(name)
                if not phys:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{label} id={obj.pk}] Sin fichero en storage: {orig}"
                        )
                    )
                    skipped += 1
                    continue
                new_name = reconcile_stored_path(phys)
                if new_name == orig and phys == orig:
                    skipped += 1
                    continue
                self.stdout.write(
                    f"[{label} id={obj.pk}]\n  de (BD): {orig}\n  físico: {phys}\n  a:  {new_name}"
                )
                if dry:
                    fixed += 1
                    continue
                with transaction.atomic():
                    if new_name != phys:
                        if default_storage.exists(new_name):
                            default_storage.delete(phys)
                        else:
                            with default_storage.open(phys, "rb") as fh:
                                stored_name = default_storage.save(new_name, File(fh))
                            default_storage.delete(phys)
                            new_name = stored_name
                    f.name = new_name
                    obj.save(update_fields=[field])
                fixed += 1

        qs_img = AdSpaceImage.objects.exclude(image="").order_by("id")
        process_qs(qs_img, "image", "AdSpaceImage")

        qs_ad = AdSpace.objects.exclude(cover_image="").order_by("id")
        process_qs(qs_ad, "cover_image", "AdSpace")

        qs_mall = ShoppingCenter.objects.exclude(cover_image="").order_by("id")
        process_qs(qs_mall, "cover_image", "ShoppingCenter")

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo. Corregidas: {fixed}. Sin cambio o sin fichero: {skipped}. Dry-run={dry}."
            )
        )
