from rest_framework import permissions

from apps.users.models import UserProfile
from apps.users.utils import get_user_role, user_is_admin

user_role = get_user_role


class IsAdminRole(permissions.BasePermission):
    """CRUD panel: centros, tomas, clientes, etc."""

    def has_permission(self, request, view):
        return user_is_admin(request.user)


class IsClientRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and get_user_role(request.user) == UserProfile.Role.CLIENT
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """List/retrieve público; escritura solo admin (no usado en catálogo público)."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return user_is_admin(request.user)
