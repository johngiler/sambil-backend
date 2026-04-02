from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.workspaces.tenant import default_workspace_slug, get_workspace_for_request


class TenantJWTAuthentication(JWTAuthentication):
    """
    Tras validar el JWT, exige que el claim `workspace_slug` coincida con el owner
    resuelto por Host/Origin (un token de un owner no sirve en el subdominio de otro).
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        request = getattr(self, "request", None)
        if request is None:
            return user

        ws = get_workspace_for_request(request)
        if ws is None:
            return user

        token_ws = validated_token.get("workspace_slug")
        if token_ws is None:
            token_ws = default_workspace_slug()

        if token_ws != ws.slug:
            raise InvalidToken(
                {
                    "detail": "Token no válido para este sitio.",
                    "code": "token_workspace_mismatch",
                },
            )

        return user
