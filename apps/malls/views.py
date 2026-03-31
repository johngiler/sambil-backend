from django.db.models import Q
from rest_framework import viewsets

from apps.malls.models import ShoppingCenter
from apps.malls.serializers import ShoppingCenterSerializer


class ShoppingCenterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Listado público de centros para la portada (`on_homepage`).
    Detalle por código (`/api/centers/SCC/`).

    Listado: filtros opcionales `search`, `catalog_status` (all|available|soon),
    `location` (all|caracas|other). Paginación estándar (20 por página).
    """

    queryset = ShoppingCenter.objects.filter(on_homepage=True).order_by("listing_order", "code")
    serializer_class = ShoppingCenterSerializer
    lookup_field = "code"
    lookup_value_regex = r"[A-Za-z0-9]+"

    def get_queryset(self):
        qs = ShoppingCenter.objects.filter(on_homepage=True).order_by("listing_order", "code")
        if self.action != "list":
            return qs
        params = self.request.query_params
        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(city__icontains=search)
                | Q(district__icontains=search)
                | Q(code__icontains=search)
            )
        catalog_status = params.get("catalog_status", "all")
        if catalog_status == "available":
            qs = qs.filter(is_active=True, marketplace_catalog_enabled=True)
        elif catalog_status == "soon":
            qs = qs.filter(is_active=True, marketplace_catalog_enabled=False)
        location = params.get("location", "all")
        if location == "caracas":
            qs = qs.filter(
                Q(name__icontains="caracas")
                | Q(city__icontains="caracas")
                | Q(district__icontains="caracas")
            )
        elif location == "other":
            caracas_q = (
                Q(name__icontains="caracas")
                | Q(city__icontains="caracas")
                | Q(district__icontains="caracas")
            )
            qs = qs.exclude(caracas_q)
        return qs
