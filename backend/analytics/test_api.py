from datetime import timedelta

import pytest
from django.utils import timezone

from agents.models import Agent
from appointments.models import Appointment
from conversations.models import (
    Conversation,
    ConversationOutcome,
    PhoneCall,
    PhoneCallStatus,
)
from crm.models import Customer

pytestmark = pytest.mark.django_db


def _call(org, agent, status=PhoneCallStatus.COMPLETED, outcome=None, days_ago=0):
    conversation = Conversation.objects.create(
        organization=org,
        agent=agent,
        outcome=outcome,
        started_at=timezone.now() - timedelta(days=days_ago),
    )
    PhoneCall.objects.create(
        conversation=conversation,
        caller_number="+15558889999",
        provider_status=status,
    )
    if status == PhoneCallStatus.COMPLETED:
        conversation.ended_at = conversation.started_at + timedelta(seconds=120)
        conversation.save(update_fields=["ended_at"])
    return conversation


def test_analytics_require_auth(api_client):
    assert api_client.get("/analytics/overview").status_code == 401


def test_analytics_overview_shape(tenant):
    _, org, client = tenant
    agent_a = Agent.objects.create(organization=org, name="A", system_prompt="p")
    agent_b = Agent.objects.create(organization=org, name="B", system_prompt="p")
    Customer.objects.create(organization=org, phone_number="+15550001111")
    Appointment.objects.create(
        organization=org,
        agent=agent_a,
        customer_name="C",
        customer_phone="+15551234567",
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        status=Appointment.Status.SCHEDULED,
    )
    Appointment.objects.create(
        organization=org,
        agent=agent_b,
        customer_name="D",
        customer_phone="+15557654321",
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=1),
        status=Appointment.Status.CANCELLED,
    )

    _call(org, agent_a, PhoneCallStatus.COMPLETED, ConversationOutcome.APPOINTMENT_BOOKED, days_ago=1)
    _call(org, agent_a, PhoneCallStatus.COMPLETED, ConversationOutcome.APPOINTMENT_BOOKED, days_ago=2)
    _call(org, agent_b, PhoneCallStatus.RINGING, days_ago=3)
    _call(org, agent_b, PhoneCallStatus.IN_PROGRESS, days_ago=0)
    _call(org, agent_b, PhoneCallStatus.FAILED, days_ago=0)

    overview = client.get("/analytics/overview")
    assert overview.status_code == 200
    data = overview.json()

    assert data["total_calls"] == 5
    assert data["completed_calls"] == 2
    assert data["in_progress_calls"] == 1
    assert data["failed_calls"] == 1
    assert data["transferred_calls"] == 0
    assert data["missed_calls"] == 1
    assert data["average_duration_seconds"] == 120.0
    assert data["total_customers"] == 1
    assert data["total_agents"] == 2
    assert data["appointments_scheduled"] == 1
    assert data["appointments_cancelled"] == 1

    breakdown = {item["outcome"]: item["count"] for item in data["outcome_breakdown"]}
    assert breakdown == {"appointment_booked": 2}

    by_day = {item["day"]: item["count"] for item in data["calls_last_7_days"]}
    assert len(by_day) == 7
    assert sum(by_day.values()) == 5

    recent = data["recent_calls"]
    assert len(recent) == 5
    assert recent[0]["agent_name"] in {"A", "B"}
    assert recent[0]["status"] in {"in_progress", "failed"}
    assert recent[0]["duration_seconds"] is None
    assert "outcome" in recent[0]


def test_analytics_recent_call_statuses(tenant):
    _, org, client = tenant
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    completed = _call(org, agent, PhoneCallStatus.COMPLETED, days_ago=4)
    _call(org, agent, PhoneCallStatus.RINGING, days_ago=5)

    recent = client.get("/analytics/overview").json()["recent_calls"]
    assert [item["id"] for item in recent] == [completed.id, completed.id + 1]
    assert [item["status"] for item in recent] == ["completed", "ringing"]
    assert recent[0]["duration_seconds"] == 120


def test_analytics_scoped_to_organization(tenant, stranger):
    _, org, client = tenant
    _, _, other = stranger
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    _call(org, agent, PhoneCallStatus.COMPLETED)

    own = client.get("/analytics/overview").json()
    assert own["total_calls"] == 1
    assert own["total_agents"] == 1

    foreign = other.get("/analytics/overview").json()
    assert foreign["total_calls"] == 0
    assert foreign["total_agents"] == 0