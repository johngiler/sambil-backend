from django.db.models import Q

from apps.malls.models import ShoppingCenter
from apps.malls.serializers import ShoppingCenterSerializer
from apps.users.base_viewsets import AdminModelViewSet
from apps.workspaces.tenant import enforce_workspace_for_non_superuser, get_workspace_for_request


class ShoppingCenterAdminViewSet(AdminModelViewSet):
    """CRUD centros comerciales (solo rol admin)."""

    serializer_class = ShoppingCenterSerializer

    def perform_create(self, serializer):
        tw = enforce_workspace_for_non_superuser(
            self.request,
            serializer.validated_data.get("workspace"),
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
        qs = ShoppingCenter.objects.all().order_by("listing_order", "code")
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
                    Q(code__icontains=search)
                    | Q(name__icontains=search)
                    | Q(city__icontains=search)
                    | Q(district__icontains=search)
                )
        return qs
