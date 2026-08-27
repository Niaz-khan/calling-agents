from rest_framework import serializers

from .models import Conversation, ConversationMessage


class MessageDetailSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = ConversationMessage
        fields = ["id", "role", "content", "tool_call_id", "created_at"]

    def get_role(self, obj):
        return obj.role.lower()


def _phone(obj):
    return getattr(obj, "phone_call", None)


def _capacity_seconds(obj):
    if obj.ended_at is not None and obj.started_at is not None:
        return int((obj.ended_at - obj.started_at).total_seconds())
    return None


class CallSerializer(serializers.ModelSerializer):
    """Legacy ``CallResponse`` shape backed by a phone ``Conversation``."""

    customer_id = serializers.IntegerField(read_only=True)
    caller_number = serializers.SerializerMethodField()
    direction = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    outcome = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "agent_id",
            "customer_id",
            "caller_number",
            "direction",
            "status",
            "outcome",
            "summary",
            "started_at",
            "ended_at",
        ]

    def get_caller_number(self, obj):
        return _phone(obj).caller_number if _phone(obj) else ""

    def get_direction(self, obj):
        return _phone(obj).direction.lower() if _phone(obj) else ""

    def get_status(self, obj):
        return _phone(obj).provider_status.lower() if _phone(obj) else ""

    def get_outcome(self, obj):
        return obj.outcome.lower() if obj.outcome else None


class CallListSerializer(CallSerializer):
    """Legacy ``CallListResponse`` shape (joins the agent name + duration)."""

    agent_name = serializers.CharField(source="agent.name", read_only=True)
    duration_seconds = serializers.SerializerMethodField()

    class Meta(CallSerializer.Meta):
        fields = CallSerializer.Meta.fields + ["agent_name", "duration_seconds"]

    def get_duration_seconds(self, obj):
        return _capacity_seconds(obj)


class CallDetailSerializer(CallSerializer):
    """Legacy ``CallDetailResponse`` shape (embeds the message transcript)."""

    messages = serializers.SerializerMethodField()

    class Meta(CallSerializer.Meta):
        fields = CallSerializer.Meta.fields + ["messages"]

    def get_messages(self, obj):
        return MessageDetailSerializer(obj.messages.all(), many=True).data