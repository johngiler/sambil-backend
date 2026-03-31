from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

from apps.users.utils import get_user_role


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class UserMeSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    client_id = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role", "client_id", "cover_image")

    def get_role(self, obj):
        return get_user_role(obj)

    def get_client_id(self, obj):
        p = getattr(obj, "profile", None)
        return p.client_id if p and p.client_id else None

    def get_cover_image(self, obj):
        p = getattr(obj, "profile", None)
        if p and p.cover_image:
            return p.cover_image.url
        return None


class UserMeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Incluye `role` (y claims de perfil) en cada access token al refrescar,
    para que no quede el rol obsoleto del login anterior.
    """

    def validate(self, attrs: dict[str, Any]) -> dict[str, str]:
        refresh = self.token_class(attrs["refresh"])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        user = None
        if user_id:
            user = get_user_model().objects.get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
            if not api_settings.USER_AUTHENTICATION_RULE(user):
                raise AuthenticationFailed(
                    self.error_messages["no_active_account"],
                    "no_active_account",
                )

        access = refresh.access_token
        if user is not None:
            access["role"] = get_user_role(user) or "client"
            access["email"] = user.email or ""
            access["username"] = user.username

        data: dict[str, str] = {"access": str(access)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    refresh.blacklist()
                except AttributeError:
                    pass

            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            refresh.outstand()

            data["refresh"] = str(refresh)

        return data


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    # El mensaje por defecto de Simple JWT (“no hay cuenta activa”) confunde cuando en realidad
    # la clave es incorrecta (authenticate devuelve None en ambos casos).
    default_error_messages = {
        **TokenObtainPairSerializer.default_error_messages,
        "no_active_account": "Usuario o contraseña incorrectos.",
    }

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = get_user_role(user) or "client"
        token["email"] = user.email or ""
        token["username"] = user.username
        return token
