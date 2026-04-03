from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import UserProfile


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return
    # Plataforma (staff/superuser): sin fila en UserProfile — solo operan vía Django admin.
    if instance.is_staff or instance.is_superuser:
        UserProfile.objects.filter(user=instance).delete()
        return
    profile, _ = UserProfile.objects.get_or_create(user=instance)
    # El rol de marketplace (admin owner / cliente) lo define el panel o datos migrados.
    if created:
        profile.role = UserProfile.Role.CLIENT
        profile.save(update_fields=["role"])
