from rest_framework import serializers
from rest_framework.exceptions import NotFound

from agents.models import Agent
from tenancy.access import get_request_organization
from tenancy.drf import Conflict

from .models import PhoneNumber


class PhoneNumberSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    agent_id = serializers.IntegerField()
    phone_number = serializers.CharField(min_length=1, max_length=50)
    provider = serializers.CharField(min_length=1, max_length=50, default="twilio")
    provider_number_id = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=100
    )

    class Meta:
        model = PhoneNumber
        fields = [
            "id",
            "organization_id",
            "agent_id",
            "phone_number",
            "provider",
            "provider_number_id",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "organization_id", "created_at"]

    def validate(self, attrs):
        instance = self.instance
        request = self.context.get("request")
        organization = get_request_organization(request) if request else None

        agent_id = attrs.get("agent_id", instance.agent_id if instance else None)
        if agent_id is not None and organization is not None:
            if not Agent.objects.filter(id=agent_id, organization=organization).exists():
                raise NotFound("Agent not found")

        phone = attrs.get("phone_number", instance.phone_number if instance else None)
        if phone is not None:
            existing = PhoneNumber.objects.filter(phone_number=phone)
            if instance is not None:
                existing = existing.exclude(pk=instance.pk)
            if existing.exists():
                raise Conflict("Phone number already registered")
        return attrs