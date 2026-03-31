from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    profile, _ = UserProfile.objects.get_or_create(user=instance)
    # Solo superusuario: is_staff es para /admin/ de Django, no debe pisar el rol de marketplace.
    if instance.is_superuser:
        if profile.role != UserProfile.Role.ADMIN:
            profile.role = UserProfile.Role.ADMIN
            profile.save(update_fields=["role"])
    elif created:
        profile.role = UserProfile.Role.CLIENT
        profile.save(update_fields=["role"])
