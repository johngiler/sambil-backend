from django.db.models import Prefetch, Q
from rest_framework.exceptions import ValidationError

from apps.malls.models import ShoppingCenter, ShoppingCenterMountingProvider
from apps.malls.serializers import MountingProviderSerializer, ShoppingCenterSerializer
from apps.users.base_viewsets import AdminModelViewSet
from apps.workspaces.tenant import enforce_workspace_for_non_superuser, get_workspace_for_request


class MountingProviderAdminViewSet(AdminModelViewSet):
    """CRUD proveedores de montaje por centro (solo admin)."""

    queryset = ShoppingCenterMountingProvider.objects.all()
    serializer_class = MountingProviderSerializer

    def get_queryset(self):
        qs = ShoppingCenterMountingProvider.objects.select_related(
            "shopping_center", "shopping_center__workspace"
        ).order_by("shopping_center_id", "sort_order", "id")
        ws = get_workspace_for_request(self.request)
        if ws is not None:
            qs = qs.filter(shopping_center__workspace=ws)
        cid = self.request.query_params.get("shopping_center")
        if cid and str(cid).strip().isdigit():
            qs = qs.filter(shopping_center_id=int(cid))
        return qs


class ShoppingCenterAdminViewSet(AdminModelViewSet):
    """CRUD centros comerciales (solo rol admin)."""

    serializer_class = ShoppingCenterSerializer

    def perform_create(self, serializer):
        tw = enforce_workspace_for_non_superuser(
            self.request,
            serializer.validated_data.get("workspace"),
        )
        if not tw.can_create_shopping_centers:
            raise ValidationError(
                "No se pueden crear centros comerciales en este workspace. "
                "Si necesitas habilitarlo, contacta a la plataforma."
            )
        serializer.save(workspace=tw)

    def perform_update(self, serializer):
        extra = {}
        if "workspace" in serializer.validated_data:
            extra["workspace"] = enforce_workspace_for_non_superuser(
                self.request,
                serializer.validated_data.get("workspace"),
            )
        serializer.save(**extra)

    def get_queryset(self):
        qs = ShoppingCenter.objects.all().order_by("-created_at", "-id")
        ws = get_workspace_for_request(self.request)
        if ws is not None:
            qs = qs.filter(workspace=ws)
        if self.action == "list":
            active = self.request.query_params.get("active", "all")
            if active == "active":
                qs = qs.filter(is_active=True)
            elif active == "inactive":
                qs = qs.filter(is_active=False)
            search = self.request.query_params.get("search", "").strip()
            if search:
                qs = qs.filter(
                    Q(slug__icontains=search)
                    | Q(name__icontains=search)
                    | Q(city__icontains=search)
                    | Q(district__icontains=search)
                )
        return qs.prefetch_related(
            Prefetch(
                "mounting_providers",
                queryset=ShoppingCenterMountingProvider.objects.order_by("sort_order", "id"),
            ),
        )
