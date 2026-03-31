from django.db.models import Q
from rest_framework import viewsets

from apps.ad_spaces.models import AdSpace
from apps.ad_spaces.serializers import AdSpaceSerializer


class AdSpaceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdSpaceSerializer

    def get_queryset(self):
        qs = AdSpace.objects.select_related("shopping_center").filter(
            shopping_center__marketplace_catalog_enabled=True,
            shopping_center__is_active=True,
            is_active=True,
        )
        center = self.request.query_params.get("center")
        if center:
            qs = qs.filter(shopping_center__code=center)
        if self.action == "list":
            search = self.request.query_params.get("search", "").strip()
            if search:
                qs = qs.filter(
                    Q(code__icontains=search)
                    | Q(title__icontains=search)
                    | Q(venue_zone__icontains=search)
                )
        return qs
