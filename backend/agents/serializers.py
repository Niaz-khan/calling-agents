from rest_framework import serializers

from .models import Agent, AgentDeployment


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
    public_identifier = serializers.CharField(read_only=True)
    channel = serializers.ChoiceField(choices=AgentDeployment.Channel.choices)
    allowed_domains = serializers.ListField(
        child=serializers.CharField(max_length=255), required=False
    )

    class Meta:
        model = AgentDeployment
        fields = [
            "id",
            "organization_id",
            "agent_id",
            "channel",
            "name",
            "enabled",
            "public_identifier",
            "allowed_domains",
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