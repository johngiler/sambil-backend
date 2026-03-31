from apps.users.models import UserProfile


def get_marketplace_client(user):
    """
    Empresa (Client) asociada al usuario vía UserProfile.client.
    Solo aplica a usuarios con rol cliente marketplace.
    """
    if not user or not user.is_authenticated:
        return None
    p = getattr(user, "profile", None)
    if not p or p.role != UserProfile.Role.CLIENT:
        return None
    return p.client


def get_user_role(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return UserProfile.Role.ADMIN
    profile = getattr(user, "profile", None)
    if profile is None:
        return UserProfile.Role.CLIENT
    return profile.role


def user_is_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return get_user_role(user) == UserProfile.Role.ADMIN
