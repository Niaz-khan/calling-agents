import re

from rest_framework import serializers

from .models import Agent, AgentDeployment

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$")


class AgentSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(min_length=1, max_length=255)
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    system_prompt = serializers.CharField(min_length=1)

    class Meta:
        model = Agent
        fields = [
            "id",
            "organization_id",
            "name",
            "description",
            "system_prompt",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization_id", "created_at", "updated_at"]


class AgentDeploymentSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True)
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    public_identifier = serializers.CharField(read_only=True)
    channel = serializers.ChoiceField(choices=AgentDeployment.Channel.choices)
    allowed_domains = serializers.ListField(
        child=serializers.CharField(max_length=255), required=False
    )
    widget_title = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=255
    )
    widget_primary_color = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=20
    )
    welcome_message = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=500
    )

    def validate_widget_primary_color(self, value):
        if value in (None, ""):
            return value
        if not _HEX_COLOR.fullmatch(value):
            raise serializers.ValidationError("must be a hex color like #4f46e5")
        return value

    class Meta:
        model = AgentDeployment
        fields = [
            "id",
            "organization_id",
            "agent_id",
            "agent_name",
            "channel",
            "name",
            "enabled",
            "public_identifier",
            "allowed_domains",
            "widget_title",
            "widget_primary_color",
            "welcome_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization_id",
            "public_identifier",
            "created_at",
            "updated_at",
        ]