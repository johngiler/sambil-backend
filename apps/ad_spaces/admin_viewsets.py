from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.ad_spaces.admin_serializers import AdSpaceAdminSerializer
from apps.ad_spaces.models import AdSpace
from apps.users.base_viewsets import AdminModelViewSet
from apps.workspaces.tenant import get_workspace_for_request


class AdSpaceAdminViewSet(AdminModelViewSet):
    """CRUD tomas / espacios publicitarios (solo rol admin)."""

    serializer_class = AdSpaceAdminSerializer

    def _assert_center_in_tenant(self, center):
        if center is None:
            return
        ws = get_workspace_for_request(self.request)
        if ws is None:
            raise ValidationError(
                {"shopping_center": "No se pudo determinar el owner de esta petición."}
            )
        if center.workspace_id != ws.id:
            raise ValidationError(
                {"shopping_center": "Este centro no pertenece al owner de este sitio."}
            )

    def perform_create(self, serializer):
        self._assert_center_in_tenant(serializer.validated_data.get("shopping_center"))
        serializer.save()

    def perform_update(self, serializer):
        center = serializer.validated_data.get("shopping_center")
        if center is not None:
            self._assert_center_in_tenant(center)
        serializer.save()

    def get_queryset(self):
        qs = AdSpace.objects.select_related("shopping_center").all().order_by(
            "shopping_center__code", "code"
        )
        ws = get_workspace_for_request(self.request)
        if ws is not None:
            qs = qs.filter(shopping_center__workspace=ws)
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st and st != "all":
                qs = qs.filter(status=st)
            search = self.request.query_params.get("search", "").strip()
            if search:
                qs = qs.filter(
                    Q(code__icontains=search)
                    | Q(title__icontains=search)
                    | Q(shopping_center__code__icontains=search)
                    | Q(shopping_center__name__icontains=search)
                )
        return qs
