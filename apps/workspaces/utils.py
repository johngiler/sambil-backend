"""Compat: scripts y código que no tienen `request` (middleware)."""

from apps.workspaces.tenant import get_default_workspace_safely, get_workspace_for_request

# Re-export
__all__ = ["get_default_workspace", "get_workspace_for_request"]


def get_default_workspace():
    """Workspace por `DEFAULT_WORKSPACE_SLUG` o el primero activo (seeds, shell)."""
    return get_default_workspace_safely()
