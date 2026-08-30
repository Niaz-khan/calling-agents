from datetime import timedelta

import json

import pytest
from django.utils import timezone

from agents.models import Agent
from ai.provider import LLMError
from conversations.models import (
    Conversation,
    ConversationMessage,
    ConversationOutcome,
    PhoneCall,
    PhoneCallStatus,
)

pytestmark = pytest.mark.django_db


def _agent(org):
    return Agent.objects.create(organization=org, name="Front Desk", system_prompt="p")


def _conv(org, agent, status=PhoneCallStatus.COMPLETED, **kwargs):
    conversation = Conversation.objects.create(organization=org, agent=agent, **kwargs)
    PhoneCall.objects.create(
        conversation=conversation,
        caller_number="+15553334444",
        provider_status=status,
    )
    if status == PhoneCallStatus.COMPLETED:
        conversation.ended_at = conversation.started_at + timedelta(seconds=90)
        conversation.save(update_fields=["ended_at"])
    return conversation


def test_calls_require_auth(api_client):
    assert api_client.get("/calls").status_code == 401


def test_create_call(tenant):
    _, org, client = tenant
    agent = _agent(org)

    missing_agent = client.post(
        f"/calls?agent_id=9999", {"caller_number": "+15553334444"}
    )
    assert missing_agent.status_code == 404

    created = client.post(
        f"/calls?agent_id={agent.id}",
        {"caller_number": "+15553334444", "direction": "inbound"},
    )
    assert created.status_code == 201
    data = created.json()
    assert data["agent_id"] == agent.id
    assert data["caller_number"] == "+15553334444"
    assert data["direction"] == "inbound"
    assert data["status"] == "in_progress"
    assert data["messages"] == []
    assert data["customer_id"] is not None

    from crm.models import Customer

    assert Customer.objects.filter(phone_number="+15553334444").count() == 1


def test_call_list_shape(tenant):
    _, org, client = tenant
    agent = _agent(org)
    _conv(org, agent)
    _conv(org, agent, status=PhoneCallStatus.RINGING)

    listing = client.get("/calls")
    assert listing.status_code == 200
    calls = listing.json()
    assert len(calls) == 2
    first = calls[0]
    assert first["agent_name"] == "Front Desk"
    assert first["status"] == "ringing"
    assert first["direction"] == "inbound"
    assert first["caller_number"] == "+15553334444"
    assert "duration_seconds" in first and "summary" in first

    filtered = client.get(f"/calls?agent_id={agent.id}")
    assert len(filtered.json()) == 2


def test_call_detail_messages(tenant):
    _, org, client = tenant
    agent = _agent(org)
    conversation = _conv(org, agent)
    ConversationMessage.objects.create(
        conversation=conversation, role="USER", content="I need an appointment"
    )
    ConversationMessage.objects.create(
        conversation=conversation, role="ASSISTANT", content="Anytime works"
    )

    detail = client.get(f"/calls/{conversation.id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["status"] == "completed"
    roles = [message["role"] for message in data["messages"]]
    assert roles == ["user", "assistant"]
    assert data["messages"][0]["content"] == "I need an appointment"

    messages = client.get(f"/calls/{conversation.id}/messages")
    assert messages.status_code == 200
    assert [message["role"] for message in messages.json()] == ["user", "assistant"]


def test_call_end(tenant):
    _, org, client = tenant
    agent = _agent(org)
    conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)

    ended = client.post(f"/calls/{conversation.id}/end")
    assert ended.status_code == 200
    assert ended.json()["status"] == "completed"

    conversation.refresh_from_db()
    assert conversation.status == "CLOSED"
    assert conversation.ended_at is not None
    assert conversation.phone_call.provider_status == "COMPLETED"


def test_calls_org_isolation(tenant, stranger):
    _, org, client = tenant
    _, _, other = stranger
    agent = _agent(org)
    conversation = _conv(org, agent)

    assert other.get(f"/calls/{conversation.id}").status_code == 404
    assert other.get(f"/calls/{conversation.id}/messages").status_code == 404
    assert other.post(f"/calls/{conversation.id}/end").status_code == 404
    assert other.get("/calls").json() == []


def test_call_not_found(tenant):
    _, _, client = tenant
    assert client.get("/calls/999999").status_code == 404


class TestSendMessage:
    def _post(self, client, conversation_id, message):
        return client.post(
            f"/calls/{conversation_id}/messages",
            {"message": message},
            format="json",
        )

    def test_direct_response(self, tenant, monkeypatch):
        _, org, client = tenant
        agent = _agent(org)
        conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)

        monkeypatch.setattr(
            "ai.agent.generate_response",
            lambda messages, tools=None: {
                "content": "Hello, how can I help?",
                "tool_calls": [],
            },
        )

        response = self._post(client, conversation.id, "I need help")
        assert response.status_code == 200
        data = response.json()
        assert data["call_id"] == conversation.id
        assert data["role"] == "assistant"
        assert data["message"] == "Hello, how can I help?"

        roles = list(
            ConversationMessage.objects.filter(conversation=conversation)
            .order_by("created_at")
            .values_list("role", flat=True)
        )
        assert roles == ["USER", "ASSISTANT"]

    def test_tool_flow_persists_and_honors_history(self, tenant, monkeypatch):
        _, org, client = tenant
        agent = _agent(org)
        conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)

        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(minutes=30)
        calls = iter([
            {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "check_appointment_availability",
                            "arguments": json.dumps({
                                "start_time": start.isoformat(),
                                "end_time": end.isoformat(),
                            }),
                        },
                    }
                ],
            },
            {"content": "Sure, let me check that.", "tool_calls": []},
            {"content": "Would you like to book it?", "tool_calls": []},
        ])

        def fake_provider(messages, tools=None):
            assert isinstance(messages, list)
            return next(calls)

        monkeypatch.setattr("ai.agent.generate_response", fake_provider)

        first = self._post(client, conversation.id, "Is 3 PM available tomorrow?")
        assert first.status_code == 200
        assert first.json()["message"] == "Sure, let me check that."

        roles = list(
            ConversationMessage.objects.filter(conversation=conversation)
            .order_by("id")
            .values_list("role", flat=True)
        )
        assert roles == ["USER", "ASSISTANT", "TOOL", "ASSISTANT"]
        tool_message = ConversationMessage.objects.get(
            conversation=conversation, role="TOOL"
        )
        assert tool_message.tool_call_id == "call_1"
        assert json.loads(tool_message.content)["available"] is True

        second = self._post(client, conversation.id, "Yes please")
        assert second.status_code == 200
        assert second.json()["message"] == "Would you like to book it?"

    def test_customer_memory_injected_into_history(self, tenant, monkeypatch):
        _, org, client = tenant
        agent = _agent(org)
        conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)
        from crm.models import Customer

        customer = Customer.objects.create(
            organization=org,
            phone_number="+15553334444",
            name="Jane",
            memory="Customer prefers morning appointments.",
        )
        conversation.customer = customer
        conversation.save(update_fields=["customer"])

        seen = {}

        def fake(messages, tools=None):
            seen["messages"] = messages
            return {"content": "Hello!", "tool_calls": []}

        monkeypatch.setattr("ai.agent.generate_response", fake)

        response = self._post(client, conversation.id, "I need help")
        assert response.status_code == 200

        sent = seen["messages"]
        system_notes = [
            message
            for message in sent
            if message["role"] == "system"
            and "Customer prefers morning appointments." in message["content"]
        ]
        assert system_notes
        assert sent[-1] == {"role": "user", "content": "I need help"}

    def test_history_normalizes_assistant_tool_call_type(self, tenant):
        _, org, _ = tenant
        agent = _agent(org)
        conversation = _conv(org, agent)

        stored = {
            "content": None,
            "tool_calls": [
                {"id": "call_1", "function": {"name": "x", "arguments": "{}"}}
            ],
        }
        ConversationMessage.objects.create(
            conversation=conversation,
            role=ConversationMessage.Role.ASSISTANT,
            content=json.dumps(stored),
        )

        from conversations.services import build_conversation_history

        history = build_conversation_history(conversation)
        assistant_msgs = [m for m in history if m["role"] == "assistant"]
        assert assistant_msgs
        assert assistant_msgs[0]["tool_calls"][0]["id"] == "call_1"
        assert assistant_msgs[0]["tool_calls"][0]["type"] == "function"

    def test_message_rejected_when_call_closed(self, tenant, monkeypatch):
        _, org, client = tenant
        agent = _agent(org)
        conversation = _conv(org, agent, status=PhoneCallStatus.COMPLETED)
        conversation.close()
        conversation.save()

        monkeypatch.setattr(
            "ai.agent.generate_response",
            lambda messages, tools=None: {"content": "x", "tool_calls": []},
        )

        response = self._post(client, conversation.id, "hello")
        assert response.status_code == 400
        assert response.json()["detail"] == "Call is not active"

    def test_llm_unavailable_returns_503(self, tenant, monkeypatch):
        _, org, client = tenant
        agent = _agent(org)
        conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)

        def boom(messages, tools=None):
            raise LLMError("LLM down")

        monkeypatch.setattr("ai.agent.generate_response", boom)

        response = self._post(client, conversation.id, "hello")
        assert response.status_code == 503
        assert response.json()["detail"] == "AI service is currently unavailable"

        assert ConversationMessage.objects.filter(
            conversation=conversation, role="USER"
        ).count() == 1


def test_end_classifies_appointment_outcome(tenant):
    _, org, client = tenant
    agent = _agent(org)
    conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)
    from appointments.models import Appointment

    Appointment.objects.create(
        organization=org,
        agent=agent,
        conversation=conversation,
        customer_name="Jane",
        customer_phone="+15551234567",
        start_time=timezone.now() + timedelta(days=1),
        end_time=timezone.now() + timedelta(days=1, minutes=30),
    )

    ended = client.post(f"/calls/{conversation.id}/end")
    assert ended.status_code == 200
    assert ended.json()["outcome"] == "appointment_booked"
    conversation.refresh_from_db()
    assert conversation.outcome == ConversationOutcome.APPOINTMENT_BOOKED


def test_transfer_then_end_preserves_transferred_outcome(tenant):
    _, org, client = tenant
    agent = _agent(org)
    conversation = _conv(org, agent, status=PhoneCallStatus.IN_PROGRESS)

    from ai.tools import TOOLS, execute_tool

    assert "transfer_to_human" in TOOLS

    result = json.loads(
        execute_tool(
            org, agent.id, conversation.id, "transfer_to_human",
            json.dumps({"reason": "Customer requested a human"}),
        )
    )
    assert result["success"] is True

    conversation.refresh_from_db()
    assert conversation.status == "CLOSED"
    assert conversation.phone_call.provider_status == "TRANSFERRED"

    ended = client.post(f"/calls/{conversation.id}/end")
    assert ended.status_code == 200
    assert ended.json()["outcome"] == "transferred_to_human"