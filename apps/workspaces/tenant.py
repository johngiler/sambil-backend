"""
Resolución de owner (Workspace) por petición y reglas de aislamiento SaaS.

- En producción el API suele ser un host fijo (p. ej. api.publivalla.com) para todos los tenants;
  el navegador envía Origin/Referer con el subdominio del SPA ({slug}.publivalla.com) y de ahí se obtiene el slug.
- Host: `{slug}.TENANT_BASE_DOMAIN` cuando la petición llega con ese Host.
- Subdominios reservados (api, www, cdn) no son slug de tenant.
"""

from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings

from apps.users.models import UserProfile
from apps.workspaces.models import Workspace

RESERVED_SUBDOMAINS = frozenset({"www", "api", "cdn"})


def _slug_from_host(host: str, base_domain: str) -> str | None:
    if not host or not base_domain:
        return None
    host = host.lower().split(":")[0]
    base = base_domain.lower().strip().strip(".")
    if not base:
        return None
    if host == base:
        return None
    suffix = f".{base}"
    if not host.endswith(suffix):
        return None
    sub = host[: -len(suffix)]
    if not sub or "." in sub:
        return None
    if sub in RESERVED_SUBDOMAINS:
        return None
    return sub


def _slug_from_url(url: str, base_domain: str) -> str | None:
    if not url or not base_domain:
        return None
    try:
        parsed = urlparse(url)
        h = (parsed.hostname or "").lower()
    except ValueError:
        return None
    return _slug_from_host(h, base_domain)


def resolve_request_workspace(request) -> tuple[Workspace | None, str | None]:
    """
    Devuelve (workspace, error_code).
    error_code: 'unknown_slug' si se infirió un slug explícito que no existe en BD.
    """
    base = getattr(settings, "TENANT_BASE_DOMAIN", "").strip()
    if not base:
        return get_default_workspace_safely(), None

    host = request.get_host().split(":")[0].lower()
    slug = _slug_from_host(host, base)

    if slug is None:
        origin = request.META.get("HTTP_ORIGIN", "")
        slug = _slug_from_url(origin, base)
    if slug is None:
        ref = request.META.get("HTTP_REFERER", "")
        slug = _slug_from_url(ref, base)

    if slug:
        ws = Workspace.objects.filter(slug=slug, is_active=True).first()
        if ws is None:
            return None, "unknown_slug"
        return ws, None

    return get_default_workspace_safely(), None


def default_workspace_slug() -> str:
    """Slug por defecto (desarrollo / un solo tenant). Único lugar con fallback literal."""
    raw = getattr(settings, "DEFAULT_WORKSPACE_SLUG", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    return "sambil"


def get_default_workspace_safely() -> Workspace | None:
    slug = default_workspace_slug()
    ws = Workspace.objects.filter(slug=slug, is_active=True).first()
    if ws:
        return ws
    return Workspace.objects.filter(is_active=True).order_by("id").first()


def get_workspace_for_request(request) -> Workspace | None:
    """Preferir lo resuelto por middleware; si no hay request, usar default."""
    if request is not None:
        ws = getattr(request, "workspace", None)
        if ws is not None:
            return ws
        err = getattr(request, "workspace_resolution_error", None)
        if err == "unknown_slug":
            return None
    return get_default_workspace_safely()


def user_can_access_workspace(user, workspace: Workspace) -> bool:
    """¿Puede este usuario iniciar sesión (JWT) en el contexto de este owner?"""
    if not user or not user.is_authenticated or workspace is None:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    if profile is None:
        return False
    if profile.role == UserProfile.Role.ADMIN:
        return profile.workspace_id == workspace.id
    if profile.role == UserProfile.Role.CLIENT:
        c = profile.client
        return c is not None and c.workspace_id == workspace.id
    return False


def enforce_workspace_for_non_superuser(request, explicit_workspace: Workspace | None) -> Workspace:
    """
    Escrituras: admin comercial no puede mandar otro workspace que el del tenant resuelto.
    Superusuario puede fijar workspace explícito.
    """
    from rest_framework.exceptions import ValidationError

    req_ws = get_workspace_for_request(request)
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_superuser", False):
        return explicit_workspace or req_ws or get_default_workspace_safely()
    if req_ws is None:
        raise ValidationError(
            {"workspace": "No se pudo determinar el owner de esta petición (Host u Origin)."}
        )
    if explicit_workspace is not None and explicit_workspace.id != req_ws.id:
        raise ValidationError({"workspace": "No puedes crear o asignar recursos de otro owner."})
    return req_ws
