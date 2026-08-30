from datetime import timedelta

import pytest
from django.utils import timezone

from agents.models import Agent
from tenancy.models import Organization

from .models import Appointment
from .services import check_availability, create_appointment

pytestmark = pytest.mark.django_db


@pytest.fixture
def org_agent():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="Scheduler", system_prompt="p")
    return org, agent


def _slot(start, end):
    return timezone.now() + timedelta(hours=start), timezone.now() + timedelta(hours=end)


def test_check_available_when_no_conflict(org_agent):
    org, agent = org_agent
    start, end = _slot(24, 25)
    assert check_availability(org, agent.id, start, end) is True


def test_check_unavailable_when_conflict_exists(org_agent):
    org, agent = org_agent
    Appointment.objects.create(
        organization=org,
        agent=agent,
        customer_name="Existing",
        customer_phone="+15550000000",
        start_time=timezone.now() + timedelta(hours=24),
        end_time=timezone.now() + timedelta(hours=25),
        status=Appointment.Status.SCHEDULED,
    )
    start, end = _slot(24.5, 25.5)
    assert check_availability(org, agent.id, start, end) is False


def test_check_available_for_adjacent_times(org_agent):
    org, agent = org_agent
    Appointment.objects.create(
        organization=org,
        agent=agent,
        customer_name="Existing",
        customer_phone="+15550000000",
        start_time=timezone.now() + timedelta(hours=24),
        end_time=timezone.now() + timedelta(hours=25),
        status=Appointment.Status.SCHEDULED,
    )
    start, end = _slot(25, 25.5)
    assert check_availability(org, agent.id, start, end) is True


def test_check_ignores_cancelled_appointments(org_agent):
    org, agent = org_agent
    Appointment.objects.create(
        organization=org,
        agent=agent,
        customer_name="Existing",
        customer_phone="+15550000000",
        start_time=timezone.now() + timedelta(hours=24),
        end_time=timezone.now() + timedelta(hours=25),
        status=Appointment.Status.CANCELLED,
    )
    start, end = _slot(24, 25)
    assert check_availability(org, agent.id, start, end) is True


def test_create_appointment_success(org_agent):
    org, agent = org_agent
    start, end = _slot(30, 30.5)
    appointment = create_appointment(
        organization=org,
        agent_id=agent.id,
        call_id=None,
        customer_name="John Doe",
        customer_phone="+15551234567",
        start_time=start,
        end_time=end,
        notes="First visit",
    )
    assert appointment.status == Appointment.Status.SCHEDULED
    assert appointment.customer_name == "John Doe"
    assert Appointment.objects.count() == 1


def test_create_appointment_rejects_overlap(org_agent):
    org, agent = org_agent
    start, end = _slot(30, 30.5)
    create_appointment(
        organization=org,
        agent_id=agent.id,
        call_id=None,
        customer_name="First",
        customer_phone="+15551111111",
        start_time=start,
        end_time=end,
    )
    with pytest.raises(ValueError):
        create_appointment(
            organization=org,
            agent_id=agent.id,
            call_id=None,
            customer_name="Second",
            customer_phone="+15552222222",
            start_time=start + timedelta(minutes=15),
            end_time=end + timedelta(minutes=15),
        )


def test_create_appointment_rejects_end_before_start(org_agent):
    org, agent = org_agent
    start, end = _slot(30, 29)
    with pytest.raises(ValueError):
        create_appointment(
            organization=org,
            agent_id=agent.id,
            call_id=None,
            customer_name="Bad",
            customer_phone="+15553333333",
            start_time=start,
            end_time=end,
        )