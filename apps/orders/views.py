from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.orders.models import Order, OrderStatus
from apps.orders.serializers import (
    OrderAdminPatchSerializer,
    OrderCreateSerializer,
    OrderSerializer,
)
from apps.orders.services import log_order_status_transition
from apps.orders.validators import (
    contract_meets_min_months,
    hold_expires_at_from_now,
    line_subtotal,
    order_item_conflicts,
)
from apps.users.utils import get_marketplace_client, user_is_admin


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = (
            Order.objects.select_related("client")
            .prefetch_related(
                "items__ad_space",
                "status_events__actor",
            )
            .all()
            .order_by("-created_at")
        )
        if user_is_admin(self.request.user):
            pass
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
        if self.action in ("partial_update", "update"):
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
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        if not user_is_admin(request.user):
            return Response(
                {"detail": "Solo administradores pueden actualizar el estado de órdenes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        ser = OrderAdminPatchSerializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        instance.refresh_from_db()
        return Response(OrderSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        if not user_is_admin(request.user):
            return Response(
                {"detail": "Solo administradores pueden actualizar el estado de órdenes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        instance = self.get_object()
        ser = OrderAdminPatchSerializer(instance, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        instance.refresh_from_db()
        return Response(OrderSerializer(instance).data)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        order = self.get_object()
        if order.status != OrderStatus.DRAFT:
            return Response(
                {"detail": "Solo se pueden enviar órdenes en borrador."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for item in order.items.select_related("ad_space"):
            if not contract_meets_min_months(item.start_date, item.end_date):
                return Response(
                    {
                        "detail": f"La línea {item.ad_space.code} no cumple el mínimo de 5 meses.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if order_item_conflicts(
                item.ad_space_id,
                item.start_date,
                item.end_date,
                exclude_order_id=order.id,
            ):
                return Response(
                    {
                        "detail": (
                            f"Las fechas de {item.ad_space.code} chocan con otra reserva o bloqueo."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        total = Decimal("0")
        for item in order.items.select_related("ad_space"):
            monthly = item.ad_space.monthly_price_usd
            sub = line_subtotal(monthly, item.start_date, item.end_date)
            item.monthly_price = monthly
            item.subtotal = sub
            item.save(update_fields=["monthly_price", "subtotal"])
            total += sub
        order.total_amount = total.quantize(Decimal("0.01"))
        order.status = OrderStatus.SUBMITTED
        order.submitted_at = timezone.now()
        order.hold_expires_at = hold_expires_at_from_now(72)
        order.save(
            update_fields=[
                "total_amount",
                "status",
                "submitted_at",
                "hold_expires_at",
            ]
        )

        log_order_status_transition(
            order,
            OrderStatus.DRAFT,
            OrderStatus.SUBMITTED,
            actor=request.user if request.user.is_authenticated else None,
            note="Solicitud enviada por el cliente.",
        )

        order.refresh_from_db()
        return Response(OrderSerializer(order).data)
