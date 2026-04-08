from decimal import Decimal

from rest_framework import serializers

from apps.ad_spaces.models import AdSpace
from apps.catalog_access import shopping_center_allows_public_catalog
from apps.clients.models import Client
from apps.orders.models import (
    Order,
    OrderItem,
    OrderPaymentMethod,
    OrderStatus,
    OrderStatusEvent,
)
from apps.orders.services import log_order_status_transition
from apps.orders.validators import (
    ad_space_allows_marketplace_reservation,
    contract_meets_min_months,
    line_subtotal,
)
from apps.users.utils import get_marketplace_client, is_platform_staff, user_is_admin
from apps.workspaces.tenant import get_workspace_for_request


_RECEIPT_MAX_BYTES = 5 * 1024 * 1024
_RECEIPT_ALLOWED_CT = frozenset(
    {"image/jpeg", "image/png", "image/webp", "application/pdf"}
)


def validate_order_receipt_file(value):
    if value is None:
        return value
    if getattr(value, "size", 0) > _RECEIPT_MAX_BYTES:
        raise serializers.ValidationError("El archivo no puede superar 5 MB.")
    ct = (getattr(value, "content_type", None) or "").strip()
    if ct and ct not in _RECEIPT_ALLOWED_CT:
        raise serializers.ValidationError(
            "Formato no permitido. Usa JPG, PNG, WebP o PDF."
        )
    return value


def _status_label(value: str) -> str:
    if not value:
        return ""
    try:
        return OrderStatus(value).label
    except ValueError:
        return value


class OrderClientSnapshotSerializer(serializers.ModelSerializer):
    """Datos de la empresa en respuestas de pedido (admin y cliente)."""

    status_label = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            "id",
            "company_name",
            "rif",
            "contact_name",
            "email",
            "phone",
            "address",
            "city",
            "status",
            "status_label",
        )
        read_only_fields = fields

    def get_status_label(self, obj):
        return obj.get_status_display()


class OrderItemSerializer(serializers.ModelSerializer):
    ad_space_code = serializers.CharField(source="ad_space.code", read_only=True)
    ad_space_title = serializers.CharField(source="ad_space.title", read_only=True)
    shopping_center_name = serializers.CharField(
        source="ad_space.shopping_center.name", read_only=True
    )
    shopping_center_slug = serializers.CharField(
        source="ad_space.shopping_center.slug", read_only=True
    )
    shopping_center_city = serializers.CharField(
        source="ad_space.shopping_center.city", read_only=True
    )
    ad_space_cover_image = serializers.SerializerMethodField()
    ad_space_gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "ad_space",
            "ad_space_code",
            "ad_space_title",
            "ad_space_cover_image",
            "ad_space_gallery_images",
            "shopping_center_slug",
            "shopping_center_city",
            "shopping_center_name",
            "start_date",
            "end_date",
            "monthly_price",
            "subtotal",
        )

    def get_ad_space_gallery_images(self, obj):
        ad = obj.ad_space
        out = []
        for row in ad.gallery_images.all():
            if row.image:
                out.append(row.image.url)
        return out

    def get_ad_space_cover_image(self, obj):
        ad = obj.ad_space
        first = ad.gallery_images.all().first()
        if first and first.image:
            return first.image.url
        img = ad.cover_image
        if not img:
            return None
        return img.url


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
    payment_method_label = serializers.SerializerMethodField()
    payment_receipt_url = serializers.SerializerMethodField()
    client_company_name = serializers.CharField(
        source="client.company_name", read_only=True
    )
    client_detail = OrderClientSnapshotSerializer(source="client", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "client",
            "client_company_name",
            "client_detail",
            "status",
            "status_label",
            "total_amount",
            "submitted_at",
            "hold_expires_at",
            "created_at",
            "payment_method",
            "payment_method_label",
            "payment_receipt_url",
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
            "payment_method",
            "payment_method_label",
            "payment_receipt_url",
        )

    def get_status_label(self, obj):
        return _status_label(obj.status)

    def get_payment_method_label(self, obj):
        v = obj.payment_method or ""
        if not v:
            return OrderPaymentMethod.UNSET.label
        try:
            return OrderPaymentMethod(v).label
        except ValueError:
            return v

    def get_payment_receipt_url(self, obj):
        f = obj.payment_receipt
        if not f:
            return None
        return f.url


class OrderClientPaymentPatchSerializer(serializers.ModelSerializer):
    """
    Solo el cliente dueño del pedido: método y comprobante (p. ej. tras checkout).
    No expuesto al admin.
    """

    _BLOCKED = frozenset(
        {
            OrderStatus.DRAFT,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED,
            OrderStatus.PAID,
            OrderStatus.ACTIVE,
        }
    )

    class Meta:
        model = Order
        fields = ("payment_method", "payment_receipt")
        extra_kwargs = {
            "payment_receipt": {"required": False, "allow_null": True},
            "payment_method": {"required": False},
        }

    def validate_payment_receipt(self, value):
        return validate_order_receipt_file(value)

    def validate(self, attrs):
        if self.instance and self.instance.status in self._BLOCKED:
            raise serializers.ValidationError(
                {
                    "detail": "No puedes modificar los datos de pago en el estado actual del pedido."
                }
            )
        return attrs

    def update(self, instance, validated_data):
        old_receipt = instance.payment_receipt if instance.payment_receipt else None
        has_new = (
            "payment_receipt" in validated_data
            and validated_data.get("payment_receipt") is not None
        )
        instance = super().update(instance, validated_data)
        if has_new and old_receipt:
            new = instance.payment_receipt
            if new and getattr(old_receipt, "name", None) != getattr(new, "name", None):
                old_receipt.delete(save=False)
        return instance


class OrderAdminPatchSerializer(serializers.ModelSerializer):
    """Solo administradores: cambiar estado operativo de la orden."""

    class Meta:
        model = Order
        fields = ("status",)

    def update(self, instance, validated_data):
        from apps.clients.notifications import notify_client_after_order_client_approved

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
            if (
                instance.status == OrderStatus.CLIENT_APPROVED
                and prev != OrderStatus.CLIENT_APPROVED
            ):
                notify_client_after_order_client_approved(instance)
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
        ad = data["ad_space"]
        if not ad_space_allows_marketplace_reservation(ad):
            raise serializers.ValidationError(
                {
                    "ad_space": (
                        f"La toma {ad.code} no admite nuevas reservas "
                        f"(estado: {ad.get_status_display()})."
                    )
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
        if is_platform_staff(request.user):
            raise serializers.ValidationError({"detail": "No se pudo completar la operación."})

        ws = get_workspace_for_request(request)

        if user_is_admin(request.user):
            raise serializers.ValidationError({"detail": "No se pudo completar la operación."})

        ce = get_marketplace_client(request.user)
        if ce is None:
            raise serializers.ValidationError(
                {
                    "detail": "Completa los datos de tu empresa (Mi cuenta) antes de pedir una reserva."
                }
            )
        # Siempre la empresa del perfil; un usuario no puede enviar otro client_id en el cuerpo.
        data["client"] = ce
        for row in data["items"]:
            sc = row["ad_space"].shopping_center
            if not shopping_center_allows_public_catalog(sc):
                raise serializers.ValidationError(
                    {"items": f"La toma {row['ad_space'].code} no está disponible en el marketplace público."}
                )
            if ce.workspace_id != sc.workspace_id:
                raise serializers.ValidationError(
                    {
                        "items": f"La toma {row['ad_space'].code} no pertenece al mismo owner que tu empresa."
                    }
                )

        for row in data["items"]:
            sc = row["ad_space"].shopping_center
            if ws is not None and sc.workspace_id != ws.id:
                raise serializers.ValidationError(
                    {"items": f"La toma {row['ad_space'].code} no pertenece al owner de este sitio."}
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
