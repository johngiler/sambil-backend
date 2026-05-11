"""
Logo del workspace en correos transaccionales (adjunto inline + CID).

Muchos clientes no muestran SVG en <img> de correo; solo se usan PNG, JPEG, GIF o WebP.
Se intenta ``logo`` (logotipo completo) y luego ``logo_mark``.
"""

from __future__ import annotations

from pathlib import Path

# Debe coincidir con el ``src="cid:…"`` del HTML generado en plantillas de pedidos/activación.
TENANT_TRANSACTIONAL_EMAIL_LOGO_CID = "tenant-email-logo"

_RASTER_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

_MIME_BY_EXT: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def prepare_workspace_email_logo_for_inline(ws) -> tuple[bytes, str, str] | None:
    """
    Lee bytes del logo del tenant para un único adjunto inline por mensaje.

    Retorna ``(raw_bytes, filename_disposition, mime_completo)`` o ``None`` si no hay raster usable.
    """
    if ws is None:
        return None
    for field_name in ("logo", "logo_mark"):
        f = getattr(ws, field_name, None)
        if not f or not getattr(f, "name", None):
            continue
        path = Path(str(f.name))
        ext = path.suffix.lower()
        if ext not in _RASTER_EXT:
            continue
        mime = _MIME_BY_EXT.get(ext)
        if not mime:
            continue
        try:
            f.open("rb")
            try:
                raw = f.read()
            finally:
                f.close()
        except OSError:
            continue
        if not raw:
            continue
        disposition_name = path.name or f"workspace-logo{ext}"
        return (raw, disposition_name, mime)
    return None
