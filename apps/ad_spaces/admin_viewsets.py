from django.db.models import Q

from apps.ad_spaces.admin_serializers import AdSpaceAdminSerializer
from apps.ad_spaces.models import AdSpace
from apps.users.base_viewsets import AdminModelViewSet


class AdSpaceAdminViewSet(AdminModelViewSet):
    """CRUD tomas / espacios publicitarios (solo rol admin)."""

    serializer_class = AdSpaceAdminSerializer

    def get_queryset(self):
        qs = AdSpace.objects.select_related("shopping_center").all().order_by(
            "shopping_center__code", "code"
        )
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
