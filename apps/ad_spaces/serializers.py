from django.utils import timezone
from rest_framework import serializers

from apps.ad_spaces.availability_calendar import year_months_occupied
from apps.ad_spaces.models import AdSpace
from apps.catalog_access import shopping_center_allows_public_catalog


class AdSpaceSerializer(serializers.ModelSerializer):
    shopping_center_slug = serializers.CharField(
        source="shopping_center.slug", read_only=True
    )
    shopping_center_name = serializers.CharField(
        source="shopping_center.name", read_only=True
    )
    shopping_center_city = serializers.CharField(
        source="shopping_center.city", read_only=True
    )
    catalog_public = serializers.SerializerMethodField(read_only=True)
    availability_year = serializers.SerializerMethodField(read_only=True)
    months_occupied = serializers.SerializerMethodField(read_only=True)
    status_label = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    gallery_images = serializers.SerializerMethodField()

    class Meta:
        model = AdSpace
        fields = (
            "id",
            "code",
            "shopping_center",
            "shopping_center_slug",
            "shopping_center_name",
            "shopping_center_city",
            "catalog_public",
            "availability_year",
            "months_occupied",
            "type",
            "title",
            "description",
            "width",
            "height",
            "quantity",
            "material",
            "location_description",
            "level",
            "monthly_price_usd",
            "status",
            "status_label",
            "cover_image",
            "gallery_images",
            "venue_zone",
            "double_sided",
            "production_specs",
            "installation_notes",
            "hem_pocket_top_cm",
        )
        read_only_fields = ("status",)

    def get_catalog_public(self, obj):
        return shopping_center_allows_public_catalog(obj.shopping_center)

    def get_availability_year(self, obj):
        return timezone.now().date().year

    def get_months_occupied(self, obj):
        y = self.get_availability_year(obj)
        return year_months_occupied(obj.pk, y)

    def get_status_label(self, obj):
        return obj.get_status_display()

    def _absolute_media_url(self, url: str) -> str:
        if not url:
            return ""
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_cover_image(self, obj):
        first = (
            obj.gallery_images.all()
            .order_by("sort_order", "id")
            .first()
        )
        if first and first.image:
            return self._absolute_media_url(first.image.url)
        if obj.cover_image:
            return self._absolute_media_url(obj.cover_image.url)
        return None

    def get_gallery_images(self, obj):
        request = self.context.get("request")
        out = []
        for i in obj.gallery_images.all().order_by("sort_order", "id"):
            if not i.image:
                continue
            u = i.image.url
            out.append(request.build_absolute_uri(u) if request else u)
        return out
