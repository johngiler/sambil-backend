"""Checkout sin sesión: crea empresa (Client), orden enviada y opcionalmente usuario marketplace."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.catalog_access import shopping_center_allows_public_catalog
from apps.clients.models import Client, ClientStatus
from apps.orders.models import Order, OrderItem, OrderStatus
from apps.orders.serializers import OrderItemWriteSerializer, OrderSerializer
from apps.orders.services import log_order_status_transition, submit_draft_order
from apps.users.admin_serializers import revoke_django_privileges
from apps.users.models import UserProfile
from apps.users.password_policy import marketplace_password_policy_errors
from apps.workspaces.tenant import get_workspace_for_request

User = get_user_model()


class GuestCheckoutEmailCheckSerializer(serializers.Serializer):
    email = serializers.EmailField()


class GuestCheckoutEmailCheckView(APIView):
    """
    POST público: indica si el correo está libre para «crear cuenta al comprar»
    (misma regla que GuestCheckoutView al crear usuario).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "guest_checkout_email"

    def post(self, request, *args, **kwargs):
        ws = get_workspace_for_request(request)
        if ws is None:
            return Response(
                {
                    "detail": "No se identificó el espacio de trabajo. Usa el subdominio o la cabecera del tenant.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = GuestCheckoutEmailCheckSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"].strip().lower()
        taken = User.objects.filter(username__iexact=email).exists() or User.objects.filter(
            email__iexact=email
        ).exists()
        if taken:
            return Response(
                {
                    "available": False,
                    "detail": "Ya existe un usuario con este correo. Inicia sesión o usa otro email.",
                    "code": "email_taken",
                },
                status=status.HTTP_200_OK,
            )
        return Response({"available": True}, status=status.HTTP_200_OK)


class GuestCheckoutSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    rif = serializers.CharField(max_length=32)
    contact_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, allow_blank=True, default="")
    address = serializers.CharField(allow_blank=True, default="", required=False)
    city = serializers.CharField(allow_blank=True, default="", max_length=120, required=False)
    create_account = serializers.BooleanField(default=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")
    items = OrderItemWriteSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Agrega al menos una toma.")
        return value

    def validate(self, attrs):
        if attrs.get("create_account"):
            p1 = (attrs.get("password") or "").strip()
            p2 = (attrs.get("password_confirm") or "").strip()
            if p1 != p2:
                raise serializers.ValidationError(
                    {"password_confirm": "Las contraseñas no coinciden."}
                )
            policy_errs = marketplace_password_policy_errors(p1)
            if policy_errs:
                raise serializers.ValidationError({"password": policy_errs})
            attrs["_password"] = p1
        return attrs

    def validate_rif(self, value):
        s = (value or "").strip()
        if not s:
            raise serializers.ValidationError("Indica el RIF.")
        return s


class GuestCheckoutView(APIView):
    """
    POST público: datos de empresa + líneas del carrito.
    Crea o reutiliza Client (mismo RIF en el workspace sin usuario aún), genera orden enviada.
    Opcionalmente crea usuario marketplace con contraseña (crear cuenta al comprar).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "guest_checkout"

    def post(self, request, *args, **kwargs):
        ws = get_workspace_for_request(request)
        if ws is None:
            return Response(
                {
                    "detail": "No se identificó el espacio de trabajo. Usa el subdominio o la cabecera del tenant.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = GuestCheckoutSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        email = data["email"].strip().lower()
        rif = data["rif"].strip()

        items_data = data["items"]
        for row in items_data:
            sc = row["ad_space"].shopping_center
            if not shopping_center_allows_public_catalog(sc):
                return Response(
                    {
                        "detail": f"La toma {row['ad_space'].code} no está disponible en el marketplace público.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if sc.workspace_id != ws.id:
                return Response(
                    {
                        "detail": f"La toma {row['ad_space'].code} no pertenece a este sitio.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            client = Client.objects.get(workspace=ws, rif=rif)
        except Client.DoesNotExist:
            client = None

        if client is not None:
            if UserProfile.objects.filter(client=client, role=UserProfile.Role.CLIENT).exists():
                return Response(
                    {
                        "detail": "Este RIF ya tiene una cuenta en el marketplace. Inicia sesión para completar la reserva.",
                        "code": "rif_has_account",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            client.company_name = data["company_name"].strip()
            client.contact_name = data["contact_name"].strip()
            client.email = email
            client.phone = (data.get("phone") or "").strip()
            client.address = (data.get("address") or "").strip()
            client.city = (data.get("city") or "").strip()
            client.save()
        else:
            client = Client.objects.create(
                workspace=ws,
                company_name=data["company_name"].strip(),
                rif=rif,
                contact_name=data["contact_name"].strip(),
                email=email,
                phone=(data.get("phone") or "").strip(),
                address=(data.get("address") or "").strip(),
                city=(data.get("city") or "").strip(),
                status=ClientStatus.PENDING,
            )

        if data.get("create_account"):
            if User.objects.filter(username__iexact=email).exists() or User.objects.filter(
                email__iexact=email
            ).exists():
                return Response(
                    {
                        "detail": "Ya existe un usuario con este correo. Inicia sesión o usa otro email.",
                        "code": "email_taken",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
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

                log_order_status_transition(
                    order,
                    "",
                    OrderStatus.DRAFT,
                    actor=None,
                    note="Orden creada (checkout invitado, borrador).",
                )

                actor_user = None
                if data.get("create_account"):
                    pwd = data["_password"]
                    uname = email[:150]
                    user = User.objects.create_user(username=uname, email=email, password=pwd)
                    profile = user.profile
                    profile.role = UserProfile.Role.CLIENT
                    profile.client = client
                    profile.workspace = ws
                    profile.save()
                    revoke_django_privileges(user)
                    actor_user = user

                submit_draft_order(order, actor=actor_user)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        order.refresh_from_db()
        return Response(
            OrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
