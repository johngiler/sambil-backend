from django.contrib.auth.models import User
from rest_framework import serializers

from apps.clients.models import Client
from apps.users.models import UserProfile


class NullableClientIdField(serializers.IntegerField):
    """FormData envía cadena vacía para «sin empresa»; JSON puede mandar null."""

    def to_internal_value(self, data):
        if data in ("", None):
            if self.allow_null:
                return None
        return super().to_internal_value(data)


def revoke_django_privileges(user):
    """Quita staff/superuser de Django al pasar a cliente marketplace."""
    if not user.is_staff and not user.is_superuser:
        return
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=["is_staff", "is_superuser"])


def set_user_client_link(user, client_id):
    """Asigna o quita la empresa en UserProfile.client (varios usuarios pueden compartir el mismo Client)."""
    profile = user.profile
    if client_id is None:
        profile.client = None
        profile.save(update_fields=["client"])
        return
    c = Client.objects.get(pk=client_id)
    profile.client = c
    profile.save(update_fields=["client"])


class UserAdminSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    cover_image = serializers.ImageField(
        source="profile.cover_image",
        read_only=True,
        allow_null=True,
    )
    client_id = serializers.SerializerMethodField()
    client_company_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "role",
            "cover_image",
            "client_id",
            "client_company_name",
            "is_staff",
            "is_superuser",
            "date_joined",
        )

    def get_client_id(self, obj):
        p = getattr(obj, "profile", None)
        return p.client_id if p and p.client_id else None

    def get_client_company_name(self, obj):
        p = getattr(obj, "profile", None)
        if p and p.client_id:
            c = getattr(p, "client", None)
            return c.company_name if c else None
        return None


class UserAdminCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(
        choices=UserProfile.Role.choices,
        default=UserProfile.Role.CLIENT,
    )
    cover_image = serializers.ImageField(required=False, allow_null=True)
    client_id = NullableClientIdField(required=False, allow_null=True)

    def validate_client_id(self, value):
        if value is None:
            return value
        if not Client.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Empresa (cliente) no encontrada.")
        return value

    def validate(self, attrs):
        role = attrs.get("role", UserProfile.Role.CLIENT)
        cid = attrs.get("client_id")
        if cid is not None and role != UserProfile.Role.CLIENT:
            raise serializers.ValidationError(
                {"client_id": "Solo los usuarios con rol «Cliente marketplace» pueden vincularse a una empresa."}
            )
        return attrs

    def create(self, validated_data):
        cover = validated_data.pop("cover_image", None)
        role = validated_data.pop("role")
        client_id = validated_data.pop("client_id", None)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )
        profile = user.profile
        profile.role = role
        if cover:
            profile.cover_image = cover
        profile.save(update_fields=["role", "cover_image"])
        if role == UserProfile.Role.CLIENT and client_id is not None:
            set_user_client_link(user, client_id)
        return user


class UserAdminUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    role = serializers.ChoiceField(choices=UserProfile.Role.choices, required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)
    client_id = NullableClientIdField(required=False, allow_null=True)

    def validate_client_id(self, value):
        if value is None:
            return value
        if not Client.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Empresa (cliente) no encontrada.")
        return value

    def validate(self, attrs):
        inst = self.instance
        role_after = attrs.get("role", inst.profile.role)
        if "client_id" in attrs and attrs["client_id"] is not None and role_after != UserProfile.Role.CLIENT:
            raise serializers.ValidationError(
                {"client_id": "Solo los usuarios con rol «Cliente marketplace» pueden vincularse a una empresa."}
            )
        return attrs

    def validate_password(self, value):
        if value and len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return value

    def update(self, instance, validated_data):
        client_id_provided = "client_id" in validated_data
        client_id = validated_data.pop("client_id", None) if client_id_provided else None

        if "password" in validated_data:
            pwd = validated_data.pop("password")
            if pwd:
                instance.set_password(pwd)
                instance.save(update_fields=["password"])

        if "email" in validated_data:
            instance.email = validated_data["email"]
            instance.save(update_fields=["email"])

        profile = instance.profile
        prof_fields = []
        if "role" in validated_data:
            profile.role = validated_data["role"]
            prof_fields.append("role")
        if "cover_image" in validated_data:
            profile.cover_image = validated_data["cover_image"]
            prof_fields.append("cover_image")
        if prof_fields:
            profile.save(update_fields=prof_fields)

        instance.refresh_from_db()
        profile.refresh_from_db()

        if "role" in validated_data and validated_data["role"] == UserProfile.Role.CLIENT:
            revoke_django_privileges(instance)

        if profile.role == UserProfile.Role.ADMIN:
            set_user_client_link(instance, None)
        elif client_id_provided:
            set_user_client_link(instance, client_id)

        return instance
