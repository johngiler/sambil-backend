import re
from datetime import timedelta
from decimal import Decimal

from django.db.models import Prefetch, Q, Sum
from django.utils import timezone
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


def _build_order_admin_list_search_q(search: str) -> Q:
    """
    Búsqueda en listado admin: nombre de cliente, id numérico del pedido o referencia
    tipo #SLUG-ORDER-000004 (con o sin #, espacios ignorados), y texto en code.
    """
    raw = search.strip()
    q = Q(client__company_name__icontains=raw) | Q(code__icontains=raw)
    norm = re.sub(r"\s+", "", raw).upper()
    if norm.isdigit():
        try:
            q |= Q(pk=int(norm))
        except (ValueError, OverflowError):
            pass
    m = re.search(r"-ORDER-(\d+)$", norm)
    if m:
        try:
            q |= Q(pk=int(m.group(1)))
        except (ValueError, OverflowError):
            pass
    return q


# Estados entre envío y activación (no incluye borrador ni activa/vencida/cancel/rechazo).
_ORDER_PIPELINE_STATUSES = (
    OrderStatus.SUBMITTED,
    OrderStatus.CLIENT_APPROVED,
    OrderStatus.ART_APPROVED,
    OrderStatus.INVOICED,
    OrderStatus.PAID,
    OrderStatus.PERMIT_PENDING,
    OrderStatus.INSTALLATION,
)


def _client_orders_summary_for_list(*, client) -> dict:
    """
    Totales globales del cliente para la cabecera de «Mis pedidos» (sin depender de filtros de página).
    """
    base = Order.objects.filter(client=client)
    today = timezone.localdate()
    soon = today + timedelta(days=30)

    committed = base.exclude(
        status__in=(
            OrderStatus.DRAFT,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        )
    )
    total_committed = committed.aggregate(s=Sum("total_amount"))["s"] or Decimal("0")

    orders_ending_soon = (
        base.filter(
            status=OrderStatus.ACTIVE,
            items__start_date__lte=today,
            items__end_date__gte=today,
            items__end_date__lte=soon,
        )
        .distinct()
        .count()
    )

    return {
        "committed_total_subtotal": str(total_committed.quantize(Decimal("0.01"))),
        "order_counts": {
            "total": base.count(),
            "active": base.filter(status=OrderStatus.ACTIVE).count(),
            "expired": base.filter(status=OrderStatus.EXPIRED).count(),
            "pipeline": base.filter(status__in=_ORDER_PIPELINE_STATUSES).count(),
            "draft": base.filter(status=OrderStatus.DRAFT).count(),
            "cancelled": base.filter(status=OrderStatus.CANCELLED).count(),
            "rejected": base.filter(status=OrderStatus.REJECTED).count(),
        },
        "orders_ending_within_30_days": orders_ending_soon,
    }


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
            Order.objects.select_related("client", "client__workspace")
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
                qs = qs.filter(_build_order_admin_list_search_q(search))
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

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            return response
        if user_is_admin(request.user):
            return response
        client = get_marketplace_client(request.user)
        if client is None:
            return response
        payload = response.data
        if isinstance(payload, dict) and "results" in payload:
            payload["summary"] = _client_orders_summary_for_list(client=client)
        return response

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
