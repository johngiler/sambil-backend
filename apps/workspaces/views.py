from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.serializers import WorkspacePublicSerializer
from apps.workspaces.tenant import get_workspace_for_request


class WorkspaceCurrentView(APIView):
    """
    Datos públicos del owner (Workspace) según Host / Origin de la petición.
    El front usa esto para marca, título y colores sin acoplar nombres fijos.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        ws = get_workspace_for_request(request)
        if ws is None:
            return Response(
                {"detail": "No hay workspace para este contexto."},
                status=404,
            )
        ser = WorkspacePublicSerializer(ws, context={"request": request})
        return Response(ser.data)
