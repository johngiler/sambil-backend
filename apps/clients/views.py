from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clients.models import Client
from apps.clients.serializers import (
    ClientAdminSerializer,
    MyCompanySerializer,
)
from apps.users.base_viewsets import AdminModelViewSet
from apps.users.models import UserProfile
from apps.users.utils import get_marketplace_client, user_is_admin


class ClientViewSet(AdminModelViewSet):
    """Alta/gestión de clientes (empresa) — solo administradores."""

    serializer_class = ClientAdminSerializer

    def get_queryset(self):
        qs = Client.objects.all().order_by("company_name").prefetch_related(
            Prefetch(
                "member_profiles",
                queryset=UserProfile.objects.only("id", "user_id", "client_id"),
            ),
        )
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st and st != "all":
                qs = qs.filter(status=st)
            search = self.request.query_params.get("search", "").strip()
            if search:
                qs = qs.filter(
                    Q(company_name__icontains=search)
                    | Q(rif__icontains=search)
                    | Q(email__icontains=search)
                    | Q(contact_name__icontains=search)
                )
        return qs


class MyCompanyView(APIView):
    """
    Cliente autenticado: crear o actualizar su ficha de empresa (una por usuario).
    Requerido antes de generar órdenes desde el marketplace.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        c = get_marketplace_client(request.user)
        if c is None:
            return Response(None, status=status.HTTP_204_NO_CONTENT)
        return Response(ClientAdminSerializer(c).data)

    def post(self, request):
        if user_is_admin(request.user):
            return Response(
                {"detail": "Los administradores gestionan clientes desde el panel API /api/clients/."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if get_marketplace_client(request.user):
            return Response(
                {"detail": "Ya existe una ficha. Usa PATCH para actualizar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = MyCompanySerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        c = ser.save()
        return Response(ClientAdminSerializer(c).data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        c = get_marketplace_client(request.user)
        if c is None:
            return Response(
                {"detail": "No hay ficha. Crea una con POST."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if user_is_admin(request.user):
            return Response(
                {"detail": "Usa el panel de administración."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = MyCompanySerializer(c, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ClientAdminSerializer(c).data)
