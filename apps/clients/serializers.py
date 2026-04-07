from rest_framework import serializers

from apps.clients.models import Client, ClientStatus
from apps.users.models import UserProfile
from apps.users.utils import is_platform_staff
from apps.workspaces.tenant import get_workspace_for_request


class ClientAdminSerializer(serializers.ModelSerializer):
    """Admin: datos de empresa. Usuarios enlazados vía UserProfile.client (varios por empresa)."""

    linked_user_ids = serializers.SerializerMethodField()
    linked_usernames = serializers.SerializerMethodField()
    orders_count = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            "id",
            "workspace",
            "linked_user_ids",
            "linked_usernames",
            "orders_count",
            "company_name",
            "rif",
            "contact_name",
            "email",
            "phone",
            "address",
            "city",
            "notes",
            "status",
            "status_label",
            "cover_image",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("linked_user_ids", "linked_usernames", "created_at", "updated_at")
        extra_kwargs = {
            "workspace": {"required": False, "allow_null": True},
            "cover_image": {"required": False, "allow_null": True},
        }

    def get_linked_user_ids(self, obj):
        return sorted(obj.member_profiles.values_list("user_id", flat=True))

    def get_linked_usernames(self, obj):
        profiles = obj.member_profiles.select_related("user").order_by("user__username")
        return [p.user.username for p in profiles]

    def get_orders_count(self, obj):
        if hasattr(obj, "_orders_count"):
            return obj._orders_count
        return obj.orders.count()

    def get_status_label(self, obj):
        return obj.get_status_display()


class MyCompanySerializer(serializers.ModelSerializer):
    rif = serializers.CharField(
        max_length=32,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    class Meta:
        model = Client
        fields = ("company_name", "rif", "contact_name", "email", "phone", "address", "city")

    def validate_rif(self, value):
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    def create(self, validated_data):
        request = self.context["request"]
        if is_platform_staff(request.user):
            raise serializers.ValidationError({"detail": "No se pudo completar la solicitud."})
        ws = get_workspace_for_request(request)
        if not ws:
            raise serializers.ValidationError(
                {
                    "detail": "No hay workspace para esta petición. Revisa el subdominio o configura DEFAULT_WORKSPACE_SLUG."
                }
            )
        c = Client.objects.create(
            status=ClientStatus.ACTIVE,
            workspace=ws,
            **validated_data,
        )
        prof, _ = UserProfile.objects.get_or_create(user=request.user)
        prof.client = c
        prof.save(update_fields=["client"])
        return c
