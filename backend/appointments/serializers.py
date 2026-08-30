from rest_framework import serializers
from rest_framework.exceptions import NotFound

from agents.models import Agent
from tenancy.access import get_request_organization
from tenancy.drf import Conflict

from .models import Appointment
from .services import check_availability


class AppointmentSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    agent_id = serializers.IntegerField()
    call_id = serializers.IntegerField(source="conversation_id", read_only=True)
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
            "customer_name",
            "customer_phone",
            "start_time",
            "end_time",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "organization_id", "call_id", "created_at"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get("status"):
            data["status"] = data["status"].lower()
        return data

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