from rest_framework import serializers

from apps.ad_spaces.models import AdSpace


class AdSpaceAdminSerializer(serializers.ModelSerializer):
    shopping_center_code = serializers.CharField(
        source="shopping_center.code", read_only=True
    )
    shopping_center_name = serializers.CharField(
        source="shopping_center.name", read_only=True
    )
    shopping_center_city = serializers.CharField(
        source="shopping_center.city", read_only=True, allow_blank=True
    )

    class Meta:
        model = AdSpace
        fields = (
            "id",
            "code",
            "shopping_center",
            "shopping_center_code",
            "shopping_center_name",
            "shopping_center_city",
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
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {"cover_image": {"required": False, "allow_null": True}}
