from django.db.models import Count, Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ad_spaces.models import AdSpace
from apps.ad_spaces.serializers import AdSpaceSerializer
from apps.ad_spaces.models import AdSpaceStatus
from apps.orders.validators import (
    contract_meets_min_months,
    order_item_conflicts,
)
from apps.workspaces.tenant import get_workspace_for_request

_EMPTY_CITY_SENTINEL = "__empty__"


class CheckRentalRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class AdSpaceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdSpaceSerializer

    @staticmethod
    def _apply_list_search(qs, search: str):
        if not search:
            return qs
        return qs.filter(
            Q(code__icontains=search)
            | Q(title__icontains=search)
            | Q(venue_zone__icontains=search)
            | Q(description__icontains=search)
            | Q(location_description__icontains=search)
            | Q(shopping_center__name__icontains=search)
            | Q(shopping_center__city__icontains=search)
            | Q(shopping_center__district__icontains=search)
        )

    def get_queryset(self):
        qs = AdSpace.objects.select_related("shopping_center").filter(
            shopping_center__marketplace_catalog_enabled=True,
            shopping_center__is_active=True,
            is_active=True,
        )
        ws = get_workspace_for_request(self.request)
        if ws is not None:
            qs = qs.filter(shopping_center__workspace=ws)
        center = self.request.query_params.get("center")
        if center:
            qs = qs.filter(shopping_center__code=center)
        if self.action == "list":
            search = self.request.query_params.get("search", "").strip()
            qs = self._apply_list_search(qs, search)
            city = self.request.query_params.get("city", "").strip()
            if city == _EMPTY_CITY_SENTINEL:
                qs = qs.filter(shopping_center__city="")
            elif city:
                qs = qs.filter(shopping_center__city__iexact=city)
        return qs.prefetch_related("gallery_images").order_by("-created_at", "-id")

    @action(detail=True, methods=["post"], url_path="check-rental-range")
    def check_rental_range(self, request, pk=None):
        """
        Comprueba solapamiento con órdenes en pipeline y bloques (misma regla que al enviar la orden).
        """
        space = self.get_object()
        ser = CheckRentalRangeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        start = ser.validated_data["start_date"]
        end = ser.validated_data["end_date"]
        if space.status != AdSpaceStatus.AVAILABLE:
            return Response(
                {
                    "ok": False,
                    "detail": (
                        "Esta toma no admite nuevas reservas en el marketplace "
                        f"(estado: {space.get_status_display()})."
                    ),
                },
                status=200,
            )
        if not contract_meets_min_months(start, end):
            return Response(
                {"ok": False, "detail": "El período no cumple el mínimo de 5 meses."},
                status=200,
            )
        if order_item_conflicts(space.pk, start, end):
            title = (space.title or "").strip() or "esta toma"
            return Response(
                {
                    "ok": False,
                    "detail": f'Las fechas elegidas para «{title}» chocan con otra reserva o bloqueo.',
                },
                status=200,
            )
        return Response({"ok": True}, status=200)

    @action(detail=False, methods=["get"], url_path="location-facets")
    def location_facets(self, request):
        """
        Conteos por ciudad del centro (para pills en portada). Respeta tenant y búsqueda de listado.
        """
        qs = AdSpace.objects.select_related("shopping_center").filter(
            shopping_center__marketplace_catalog_enabled=True,
            shopping_center__is_active=True,
            is_active=True,
        )
        ws = get_workspace_for_request(request)
        if ws is not None:
            qs = qs.filter(shopping_center__workspace=ws)
        search = request.query_params.get("search", "").strip()
        qs = self._apply_list_search(qs, search)
        total = qs.count()
        rows = (
            qs.exclude(shopping_center__city="")
            .values("shopping_center__city")
            .annotate(count=Count("id"))
            .order_by("-count", "shopping_center__city")
        )
        items = [
            {"city": r["shopping_center__city"], "count": r["count"]} for r in rows
        ]
        empty_city = qs.filter(shopping_center__city="").count()
        if empty_city:
            items.append(
                {"city": _EMPTY_CITY_SENTINEL, "label": "Sin ciudad", "count": empty_city}
            )
        return Response({"total": total, "items": items})
