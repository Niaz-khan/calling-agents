from datetime import timedelta

import pytest
from django.utils import timezone

from agents.models import Agent
from conversations.models import (
    Conversation,
    ConversationMessage,
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