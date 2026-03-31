from django.db.models import Q

from apps.malls.models import ShoppingCenter
from apps.malls.serializers import ShoppingCenterSerializer
from apps.users.base_viewsets import AdminModelViewSet


class ShoppingCenterAdminViewSet(AdminModelViewSet):
    """CRUD centros comerciales (solo rol admin)."""

    serializer_class = ShoppingCenterSerializer

    def get_queryset(self):
        qs = ShoppingCenter.objects.all().order_by("listing_order", "code")
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
