from django.db.models import Prefetch, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.ad_spaces.models import AdSpaceImage
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.serializers import (
    OrderAdminPatchSerializer,
    OrderClientPaymentPatchSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
from apps.orders.services import submit_draft_order
from apps.users.utils import get_marketplace_client, user_is_admin
from apps.workspaces.tenant import get_workspace_for_request


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = (
            Order.objects.select_related("client")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related(
                        "ad_space__shopping_center",
                    ).prefetch_related(
                        Prefetch(
                            "ad_space__gallery_images",
                            queryset=AdSpaceImage.objects.order_by("sort_order", "id"),
                        ),
                    ),
                ),
                "status_events__actor",
            )
            .all()
            .order_by("-created_at", "-id")
        )
        ws = get_workspace_for_request(self.request)
        if user_is_admin(self.request.user):
            if ws is not None:
                qs = qs.filter(client__workspace=ws)
            else:
                return qs.none()
        else:
            client = get_marketplace_client(self.request.user)
            if client is None:
                return qs.none()
            qs = qs.filter(client=client)
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st and st != "all":
                qs = qs.filter(status=st)
            search = self.request.query_params.get("search", "").strip()
            if search:
                q = Q(client__company_name__icontains=search)
                if search.isdigit():
                    q |= Q(pk=int(search))
                qs = qs.filter(q)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action == "update":
            return OrderAdminPatchSerializer
        return OrderSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            OrderSerializer(order, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        ctx = self.get_serializer_context()
        if user_is_admin(request.user):
            ser = OrderAdminPatchSerializer(
                instance, data=request.data, partial=True, context=ctx
            )
        else:
            client = get_marketplace_client(request.user)
            if client is None or instance.client_id != client.pk:
                return Response(
                    {"detail": "No tienes permiso para modificar este pedido."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            ser = OrderClientPaymentPatchSerializer(
                instance, data=request.data, partial=True, context=ctx
            )
        ser.is_valid(raise_exception=True)
        ser.save()
        instance.refresh_from_db()
        return Response(OrderSerializer(instance, context=ctx).data)

    def update(self, request, *args, **kwargs):
        if not user_is_admin(request.user):
            return Response(
                {"detail": "No tienes permiso para esta acción."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        ser = OrderAdminPatchSerializer(instance, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        instance.refresh_from_db()
        return Response(
            OrderSerializer(instance, context=self.get_serializer_context()).data
        )

    def destroy(self, request, *args, **kwargs):
        if not user_is_admin(request.user):
            return Response(
                {"detail": "No tienes permiso para esta acción."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        if instance.status != OrderStatus.DRAFT:
            return Response(
                {
                    "detail": "Solo se pueden eliminar pedidos en borrador.",
                    "code": "order_not_draft",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        from rest_framework import serializers as drf_serializers

        order = self.get_object()
        try:
            submit_draft_order(
                order,
                actor=request.user if request.user.is_authenticated else None,
            )
        except drf_serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)
