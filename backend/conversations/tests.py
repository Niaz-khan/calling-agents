import pytest
from django.db import IntegrityError
from django.utils import timezone

from agents.models import Agent
from conversations.models import (
    Conversation,
    ConversationChannel,
    ConversationMessage,
    ConversationOutcome,
    ConversationStatus,
    PhoneCall,
    PhoneCallDirection,
    PhoneCallStatus,
)
from crm.models import Customer
from tenancy.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def org_agent():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="Hitman", system_prompt="p")
    return org, agent


def test_conversation_creates_phone_profile(org_agent):
    org, agent = org_agent
    conv = Conversation.objects.create(
        organization=org, agent=agent, channel=ConversationChannel.PHONE
    )
    phone = PhoneCall.objects.create(
        conversation=conv, direction=PhoneCallDirection.INBOUND, caller_number="+1555"
    )
    assert conv.phone_call.pk == phone.pk
    assert conv.status == ConversationStatus.OPEN
    assert phone.provider_status == PhoneCallStatus.RINGING


def test_close_marks_closed_and_ended(org_agent):
    org, agent = org_agent
    conv = Conversation.objects.create(organization=org, agent=agent)
    conv.close()
    conv.save()
    conv.refresh_from_db()
    assert conv.status == ConversationStatus.CLOSED
    assert conv.ended_at is not None


def test_messages_roles_and_ordering(org_agent):
    org, agent = org_agent
    conv = Conversation.objects.create(organization=org, agent=agent)
    for role, content in [("USER", "hi"), ("ASSISTANT", "hello"), ("TOOL", "{}"), ("SYSTEM", "sys")]:
        ConversationMessage.objects.create(conversation=conv, role=role, content=content)
    assert list(conv.messages.values_list("role", flat=True)) == ["USER", "ASSISTANT", "TOOL", "SYSTEM"]
    assert ConversationMessage.Role.values == ["USER", "ASSISTANT", "SYSTEM", "TOOL"]


def test_enum_legacy_parity():
    assert ConversationChannel.values == ["phone", "website", "api"]
    assert ConversationOutcome.values == [
        "APPOINTMENT_BOOKED",
        "APPOINTMENT_REQUESTED",
        "INFORMATION_PROVIDED",
        "CALLBACK_REQUESTED",
        "TRANSFERRED_TO_HUMAN",
        "NO_RESOLUTION",
        "CUSTOMER_HUNG_UP",
        "UNKNOWN",
    ]
    assert PhoneCallStatus.values == ["RINGING", "IN_PROGRESS", "COMPLETED", "FAILED", "TRANSFERRED"]
    assert PhoneCallDirection.values == ["INBOUND", "OUTBOUND"]


def test_customer_set_null_when_deleted(org_agent):
    org, agent = org_agent
    customer = Customer.objects.create(organization=org, phone_number="+1")
    conv = Conversation.objects.create(organization=org, agent=agent, customer=customer)
    customer.delete()
    conv.refresh_from_db()
    assert conv.customer_id is None


def test_provider_call_id_unique(org_agent):
    org, agent = org_agent
    conv = Conversation.objects.create(organization=org, agent=agent)
    PhoneCall.objects.create(conversation=conv, provider_call_id="CA-1")
    conv2 = Conversation.objects.create(organization=org, agent=agent)
    with pytest.raises(IntegrityError):
        PhoneCall.objects.create(conversation=conv2, provider_call_id="CA-1")


def test_conversation_timestamps(org_agent):
    org, agent = org_agent
    before = timezone.now()
    conv = Conversation.objects.create(organization=org, agent=agent)
    assert conv.started_at >= before
    assert conv.ended_at is None