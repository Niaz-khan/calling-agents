from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(min_length=1, max_length=255)
    duration_minutes = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
    )
    currency = serializers.CharField(max_length=3)
    active = serializers.BooleanField(required=False)

    class Meta:
        model = Service
        fields = [
            "id",
            "organization_id",
            "name",
            "description",
            "duration_minutes",
            "price",
            "currency",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization_id", "created_at", "updated_at"]

    def validate_currency(self, value):
        normalized = (value or "").strip().upper()
        if not normalized or len(normalized) != 3:
            raise serializers.ValidationError("Currency must be a 3-letter code like USD")
        return normalized