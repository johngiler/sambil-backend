from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.orders.models import Order
from apps.orders.serializers import (
    OrderAdminPatchSerializer,
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
                {"detail": "No tienes permiso para esta acción."},
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
                {"detail": "No tienes permiso para esta acción."},
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
        from rest_framework import serializers as drf_serializers

        order = self.get_object()
        try:
            submit_draft_order(
                order,
                actor=request.user if request.user.is_authenticated else None,
            )
        except drf_serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        return Response(OrderSerializer(order).data)
