from rest_framework import serializers

from apps.ad_spaces.models import AdSpace
from apps.catalog_access import shopping_center_allows_public_catalog


class AdSpaceSerializer(serializers.ModelSerializer):
    shopping_center_code = serializers.CharField(
        source="shopping_center.code", read_only=True
    )
    shopping_center_name = serializers.CharField(
        source="shopping_center.name", read_only=True
    )
    catalog_public = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AdSpace
        fields = (
            "id",
            "code",
            "shopping_center",
            "shopping_center_code",
            "shopping_center_name",
            "catalog_public",
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
            "cover_image",
            "venue_zone",
            "double_sided",
            "production_specs",
            "installation_notes",
            "hem_pocket_top_cm",
        )
        read_only_fields = ("status",)
        extra_kwargs = {"cover_image": {"required": False, "allow_null": True}}

    def get_catalog_public(self, obj):
        return shopping_center_allows_public_catalog(obj.shopping_center)
