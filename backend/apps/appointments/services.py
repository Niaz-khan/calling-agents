"""Appointment availability and booking business rules.

These are the authoritative checks used both by the API serializer and by
the AI booking tool. The LLM never decides availability; the backend does.
"""

from datetime import datetime

from apps.services.models import Service

from .models import Appointment


def check_availability(organization, agent_id, start_time, end_time, exclude_id=None):
    """Return True when the requested slot does not overlap a scheduled one."""
    if start_time is None or end_time is None:
        return True
    if end_time <= start_time:
        return False

    overlapping = Appointment.objects.filter(
        organization=organization,
        agent_id=agent_id,
        status=Appointment.Status.SCHEDULED,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude_id is not None:
        overlapping = overlapping.exclude(pk=exclude_id)
    return not overlapping.exists()


def create_appointment(
    organization,
    agent_id,
    call_id,
    customer_name,
    customer_phone,
    start_time,
    end_time,
    notes=None,
    service_id=None,
):
    """Create a scheduled appointment, raising ValueError on invalid/overlap."""
    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        raise ValueError("start_time and end_time must be datetimes")
    if end_time <= start_time:
        raise ValueError("Appointment end time must be after start time")
    if not check_availability(organization, agent_id, start_time, end_time):
        raise ValueError("The requested time is not available")

    service = None
    if service_id is not None:
        service = Service.objects.filter(
            id=service_id, organization=organization, active=True
        ).first()
        if service is None:
            raise ValueError("The requested service does not exist")

    return Appointment.objects.create(
        organization=organization,
        agent_id=agent_id,
        conversation_id=call_id,
        service=service,
        customer_name=customer_name,
        customer_phone=customer_phone,
        start_time=start_time,
        end_time=end_time,
        status=Appointment.Status.SCHEDULED,
        notes=notes,
    )