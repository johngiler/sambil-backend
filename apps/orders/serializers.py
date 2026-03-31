from decimal import Decimal

from rest_framework import serializers

from apps.ad_spaces.models import AdSpace
from apps.catalog_access import shopping_center_allows_public_catalog
from apps.clients.models import Client
from apps.orders.models import Order, OrderItem, OrderStatus, OrderStatusEvent
from apps.orders.services import log_order_status_transition
from apps.orders.validators import contract_meets_min_months, line_subtotal
from apps.users.utils import get_marketplace_client, user_is_admin


def _status_label(value: str) -> str:
    if not value:
        return ""
    try:
        return OrderStatus(value).label
    except ValueError:
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    ad_space_code = serializers.CharField(source="ad_space.code", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "ad_space",
            "ad_space_code",
            "start_date",
            "end_date",
            "monthly_price",
            "subtotal",
        )


class OrderStatusEventSerializer(serializers.ModelSerializer):
    from_label = serializers.SerializerMethodField()
    to_label = serializers.SerializerMethodField()
    actor_username = serializers.CharField(
        source="actor.username", read_only=True, allow_null=True
    )

    class Meta:
        model = OrderStatusEvent
        fields = (
            "id",
            "from_status",
            "to_status",
            "from_label",
            "to_label",
            "created_at",
            "actor_username",
            "note",
        )
        read_only_fields = fields

    def get_from_label(self, obj):
        return _status_label(obj.from_status)

    def get_to_label(self, obj):
        return _status_label(obj.to_status)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_timeline = OrderStatusEventSerializer(
        source="status_events", many=True, read_only=True
    )
    status_label = serializers.SerializerMethodField()
    client_company_name = serializers.CharField(
        source="client.company_name", read_only=True
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "client",
            "client_company_name",
            "status",
            "status_label",
            "total_amount",
            "submitted_at",
            "hold_expires_at",
            "created_at",
            "items",
            "status_timeline",
        )
        read_only_fields = (
            "status",
            "status_label",
            "total_amount",
            "submitted_at",
            "hold_expires_at",
            "created_at",
        )

    def get_status_label(self, obj):
        return _status_label(obj.status)


class OrderAdminPatchSerializer(serializers.ModelSerializer):
    """Solo administradores: cambiar estado operativo de la orden."""

    class Meta:
        model = Order
        fields = ("status",)

    def update(self, instance, validated_data):
        prev = instance.status
        instance = super().update(instance, validated_data)
        if prev != instance.status:
            request = self.context.get("request")
            actor = request.user if request and request.user.is_authenticated else None
            log_order_status_transition(
                instance,
                prev,
                instance.status,
                actor=actor,
            )
        return instance


class OrderItemWriteSerializer(serializers.Serializer):
    """Solo espacio y fechas; precio y subtotal los fija el servidor."""

    ad_space = serializers.PrimaryKeyRelatedField(queryset=AdSpace.objects.all())
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        start = data["start_date"]
        end = data["end_date"]
        if end < start:
            raise serializers.ValidationError(
                {"end_date": "La fecha fin debe ser posterior o igual al inicio."}
            )
        if not contract_meets_min_months(start, end):
            raise serializers.ValidationError(
                {
                    "end_date": "El contrato debe cubrir al menos 5 meses de calendario (regla Fase 1)."
                }
            )
        monthly = data["ad_space"].monthly_price_usd
        data["_monthly_price"] = monthly
        data["_subtotal"] = line_subtotal(monthly, start, end)
        return data


class OrderCreateSerializer(serializers.Serializer):
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        required=False,
        allow_null=True,
    )
    items = OrderItemWriteSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Agrega al menos una toma.")
        return value

    def validate(self, data):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Debes iniciar sesión para crear una orden.")

        if user_is_admin(request.user):
            if not data.get("client"):
                raise serializers.ValidationError(
                    {"client": "Como administrador, indica el cliente (ID) de la orden."}
                )
        else:
            ce = get_marketplace_client(request.user)
            if ce is None:
                raise serializers.ValidationError(
                    {
                        "detail": "Completa los datos de tu empresa (Mi cuenta) antes de pedir una reserva."
                    }
                )
            data["client"] = ce
            for row in data["items"]:
                sc = row["ad_space"].shopping_center
                if not shopping_center_allows_public_catalog(sc):
                    raise serializers.ValidationError(
                        {"items": f"La toma {row['ad_space'].code} no está disponible en el marketplace público."}
                    )
        return data

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        client = validated_data.pop("client")
        order = Order.objects.create(
            client=client,
            status=OrderStatus.DRAFT,
            total_amount=Decimal("0"),
        )
        total = Decimal("0")
        for row in items_data:
            OrderItem.objects.create(
                order=order,
                ad_space=row["ad_space"],
                start_date=row["start_date"],
                end_date=row["end_date"],
                monthly_price=row["_monthly_price"],
                subtotal=row["_subtotal"],
            )
            total += row["_subtotal"]
        order.total_amount = total.quantize(Decimal("0.01"))
        order.save(update_fields=["total_amount"])

        request = self.context.get("request")
        actor = request.user if request and request.user.is_authenticated else None
        log_order_status_transition(
            order,
            "",
            OrderStatus.DRAFT,
            actor=actor,
            note="Orden creada (borrador).",
        )
        return order
