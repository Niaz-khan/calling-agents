from rest_framework import serializers
from rest_framework.exceptions import NotFound

from apps.agents.models import Agent
from apps.services.models import Service
from apps.tenancy.access import get_request_organization
from apps.tenancy.drf import Conflict

from .models import Appointment
from .services import check_availability


class AppointmentSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    agent_id = serializers.IntegerField()
    call_id = serializers.IntegerField(source="conversation_id", read_only=True)
    service_id = serializers.IntegerField(required=False, allow_null=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    customer_name = serializers.CharField(min_length=1, max_length=255)
    customer_phone = serializers.CharField(min_length=1, max_length=50)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    status = serializers.CharField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "organization_id",
            "agent_id",
            "call_id",
            "service_id",
            "service_name",
            "customer_name",
            "customer_phone",
            "start_time",
            "end_time",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "organization_id", "call_id", "service_name", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("status"):
            data["status"] = data["status"].lower()
        if instance.service is not None:
            data["service_name"] = instance.service.name
        return data

    def validate_service_id(self, value):
        if value in (None, ""):
            return None
        request = self.context.get("request")
        organization = get_request_organization(request) if request else None
        if organization is None:
            return value
        if not Service.objects.filter(
            id=value, organization=organization, active=True
        ).exists():
            raise serializers.ValidationError("Service not found")
        return value

    def validate_status(self, value):
        normalized = (value or "").upper()
        if normalized not in Appointment.Status.values:
            raise serializers.ValidationError("Invalid appointment status")
        return normalized

    def validate(self, attrs):
        instance = self.instance
        request = self.context.get("request")
        organization = get_request_organization(request) if request else None

        agent_id = attrs.get("agent_id", instance.agent_id if instance else None)
        if agent_id is not None and organization is not None:
            if not Agent.objects.filter(id=agent_id, organization=organization).exists():
                raise NotFound("Agent not found")

        start = attrs.get("start_time", instance.start_time if instance else None)
        end = attrs.get("end_time", instance.end_time if instance else None)

        if start is not None and end is not None:
            if end <= start:
                raise serializers.ValidationError(
                    "Appointment end time must be after start time"
                )
            if agent_id is not None and organization is not None:
                if not check_availability(
                    organization,
                    agent_id,
                    start,
                    end,
                    exclude_id=instance.pk if instance else None,
                ):
                    raise Conflict("The requested time is not available")
        return attrs