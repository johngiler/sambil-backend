from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.ad_spaces.models import AdSpace
from apps.ad_spaces.nomenclature import validate_toma_code_for_center
from apps.malls.models import ShoppingCenter


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
    status_label = serializers.SerializerMethodField()

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
            "status_label",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self, "instance", None) is not None:
            self.fields["code"].read_only = True

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is None:
            code = attrs.get("code")
            sc = attrs.get("shopping_center")
            if code is not None and sc is not None:
                try:
                    center = ShoppingCenter.objects.get(pk=sc)
                except ShoppingCenter.DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"shopping_center": "Centro comercial no encontrado."}
                    ) from exc
                try:
                    attrs["code"] = validate_toma_code_for_center(code, center.code)
                except DjangoValidationError as exc:
                    raise serializers.ValidationError(
                        {"code": list(exc.messages)}
                    ) from exc
        return attrs

    def get_status_label(self, obj):
        return obj.get_status_display()
