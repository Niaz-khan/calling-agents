import pytest

from agents.models import Agent
from conversations.models import Conversation
from tenancy.models import Organization

from .models import Appointment

pytestmark = pytest.mark.django_db


def test_appointment_defaults_to_scheduled():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    conv = Conversation.objects.create(organization=org, agent=agent)
    appointment = Appointment.objects.create(
        organization=org,
        agent=agent,
        conversation=conv,
        customer_name="John",
        customer_phone="+1",
        start_time="2026-09-01T10:00:00Z",
        end_time="2026-09-01T11:00:00Z",
    )
    assert appointment.status == Appointment.Status.SCHEDULED
    assert appointment.conversation_id == conv.id


def test_appointment_status_values_match_legacy():
    assert Appointment.Status.values == ["SCHEDULED", "CANCELLED", "COMPLETED"]