from rest_framework import serializers

from tenancy.access import get_request_organization
from tenancy.drf import Conflict

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=255
    )
    phone_number = serializers.CharField(min_length=1, max_length=50)
    email = serializers.EmailField(
        required=False, allow_blank=True, allow_null=True, max_length=255
    )
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "organization_id",
            "name",
            "phone_number",
            "email",
            "notes",
            "memory",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization_id", "memory", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        request = self.context.get("request")
        phone = attrs.get("phone_number", instance.phone_number if instance else None)
        if phone is not None:
            organization = get_request_organization(request) if request else None
            if organization is not None:
                existing = Customer.objects.filter(
                    organization=organization, phone_number=phone
                )
                if instance is not None:
                    existing = existing.exclude(pk=instance.pk)
                if existing.exists():
                    raise Conflict("A customer with that phone number already exists")
        return attrs