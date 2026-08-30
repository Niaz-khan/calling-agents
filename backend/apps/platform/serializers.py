from rest_framework import serializers

from apps.accounts.models import User
from apps.agents.models import Agent, AgentDeployment
from apps.appointments.models import Appointment
from apps.conversations.models import Conversation
from apps.crm.models import Customer
from apps.knowledge.models import KnowledgeBase
from apps.services.models import Service
from apps.telephony.models import PhoneNumber
from apps.tenancy.models import Organization, OrganizationMember


class OrgRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "is_active"]


class AgentRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["id", "name", "is_active"]


def _membership_map(user):
    return sorted(
        OrganizationMember.objects.filter(user=user)
        .select_related("organization")
        .values_list("organization__name", "role", "organization_id"),
        key=lambda row: row[0].lower(),
    )


class PlatformUserSerializer(serializers.ModelSerializer):
    organizations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "platform_role",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "default_organization",
            "organizations",
        ]

    def get_organizations(self, obj):
        return [
            {"id": org_id, "name": name, "role": role}
            for name, role, org_id in _membership_map(obj)
        ]


class PlatformOrganizationSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(read_only=True)
    agents_count = serializers.IntegerField(read_only=True)
    deployments_count = serializers.IntegerField(read_only=True)
    phone_numbers_count = serializers.IntegerField(read_only=True)
    calls_count = serializers.IntegerField(read_only=True)
    customers_count = serializers.IntegerField(read_only=True)
    appointments_count = serializers.IntegerField(read_only=True)
    knowledge_bases_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "business_name",
            "is_active",
            "timezone",
            "contact_phone",
            "address",
            "website_url",
            "created_at",
            "members_count",
            "agents_count",
            "deployments_count",
            "phone_numbers_count",
            "calls_count",
            "customers_count",
            "appointments_count",
            "knowledge_bases_count",
        ]
        read_only_fields = ["id", "created_at"]


class PlatformAgentSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    deployments_count = serializers.IntegerField(read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Agent
        fields = [
            "id",
            "name",
            "description",
            "is_active",
            "voice_greeting",
            "created_at",
            "organization",
            "deployments_count",
            "conversations_count",
        ]


class PlatformDeploymentSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    agent = AgentRefSerializer(read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AgentDeployment
        fields = [
            "id",
            "name",
            "channel",
            "enabled",
            "public_identifier",
            "allowed_domains",
            "widget_title",
            "created_at",
            "organization",
            "agent",
            "conversations_count",
        ]


class PlatformCallSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    agent = AgentRefSerializer(read_only=True)
    caller_number = serializers.CharField(source="phone_call.caller_number", read_only=True)
    direction = serializers.CharField(source="phone_call.direction", read_only=True)
    provider_status = serializers.CharField(source="phone_call.provider_status", read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "channel",
            "status",
            "outcome",
            "started_at",
            "ended_at",
            "caller_number",
            "direction",
            "provider_status",
            "duration_seconds",
            "organization",
            "agent",
        ]

    def get_duration_seconds(self, obj):
        if obj.started_at and obj.ended_at:
            return int((obj.ended_at - obj.started_at).total_seconds())
        return None

    def get_fields(self):
        fields = super().get_fields()
        if getattr(self, "context", {}).get("include_transcript"):
            fields["transcript"] = serializers.CharField(read_only=True)
        return fields


class PlatformCustomerSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone_number",
            "email",
            "notes",
            "created_at",
            "organization",
            "conversations_count",
        ]


class PlatformAppointmentSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    agent = AgentRefSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "customer_name",
            "customer_phone",
            "start_time",
            "end_time",
            "status",
            "notes",
            "created_at",
            "organization",
            "agent",
            "service_name",
        ]


class PlatformPhoneNumberSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    agent = AgentRefSerializer(read_only=True)

    class Meta:
        model = PhoneNumber
        fields = [
            "id",
            "phone_number",
            "provider",
            "capabilities",
            "inbound_enabled",
            "outbound_enabled",
            "is_active",
            "created_at",
            "organization",
            "agent",
        ]


class PlatformKnowledgeSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)
    agent = AgentRefSerializer(read_only=True)
    documents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = KnowledgeBase
        fields = [
            "id",
            "name",
            "description",
            "documents_count",
            "created_at",
            "updated_at",
            "organization",
            "agent",
        ]


class PlatformServiceSerializer(serializers.ModelSerializer):
    organization = OrgRefSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "description",
            "duration_minutes",
            "price",
            "currency",
            "active",
            "created_at",
            "organization",
        ]


class PlatformRoleChangeSerializer(serializers.Serializer):
    platform_role = serializers.ChoiceField(choices=[""] + User.PlatformRole.values, required=False)
    is_active = serializers.BooleanField(required=False)