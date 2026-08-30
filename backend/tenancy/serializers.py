from rest_framework import serializers

from tenancy.models import Organization

from .services import normalize_business_hours, validate_timezone


class BusinessConfigSerializer(serializers.Serializer):
    """Business-facing configuration for the request organization."""

    organization_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    business_name = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=255
    )
    timezone = serializers.CharField(required=False, max_length=64)
    business_hours = serializers.JSONField(required=False)
    contact_phone = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=50
    )
    transfer_phone_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=50
    )
    address = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    website_url = serializers.URLField(
        required=False, allow_null=True, allow_blank=True, max_length=500
    )

    def validate_timezone(self, value):
        if not value:
            return value
        try:
            return validate_timezone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def validate_business_hours(self, value):
        if value in (None, ""):
            return {}
        try:
            return normalize_business_hours(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["organization_id"] = instance.id
        data["name"] = instance.name
        data["business_name"] = instance.business_name or None
        data["timezone"] = instance.timezone or "UTC"
        data["business_hours"] = instance.business_hours or {}
        data["contact_phone"] = instance.contact_phone or None
        data["transfer_phone_number"] = instance.transfer_phone_number or None
        data["address"] = instance.address or None
        data["website_url"] = instance.website_url or None
        return data

    class Meta:
        model = Organization