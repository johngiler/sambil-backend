"""CORP en ``/media/`` cuando la petición llega a Django (Gunicorn). Si Nginx sirve ``alias`` a disco, usa la misma cabecera en Nginx (ver ``scripts/nginx-api.*.conf``)."""


class MediaCrossOriginResourcePolicyMiddleware:
    """``Cross-Origin-Resource-Policy: cross-origin`` en ``/media/`` si el navegador pide el fichero desde otro origen."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/media/"):
            response["Cross-Origin-Resource-Policy"] = "cross-origin"
        return response
