"""Deployment-scoped website/API analytics.

Derived from the existing Conversation / ConversationMessage / Appointment
rows — no duplicated counters. Every function is scoped to one deployment
(which is already an organizational resource), so org isolation is preserved
by construction.
"""

import json
from datetime import datetime, time, timezone as dt_timezone

from django.utils import timezone

from appointments.models import Appointment
from conversations.models import Conversation, ConversationMessage
from tenancy.services import is_business_open, open_ranges, organization_zone

TRANSFER_TOOL = "transfer_to_human"


def _day_bounds(org, days):
    zone = organization_zone(org)
    today = timezone.now().astimezone(zone).date()
    for offset in range(days - 1, -1, -1):
        day = today - dt_timezone.timedelta(days=offset)
        start = datetime.combine(day, time.min, tzinfo=zone)
        end = datetime.combine(day + dt_timezone.timedelta(days=1), time.min, tzinfo=zone)
        yield day, start, end


def _count_transfers(conversations):
    """Count transfer_to_human tool events across a deployments conversations.

    The tool name lives in the assistant message's ``tool_calls`` JSON because
    the tool result payload does not echo the tool name.
    """
    events = 0
    messages = (
        ConversationMessage.objects.filter(conversation__in=conversations)
        .filter(role=ConversationMessage.Role.ASSISTANT)
        .values_list("content", flat=True)
        .iterator()
    )
    for raw in messages:
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        tool_calls = payload.get("tool_calls") if isinstance(payload, dict) else None
        if not tool_calls:
            continue
        for call in tool_calls:
            func = call.get("function") or {}
            if func.get("name") == TRANSFER_TOOL:
                events += 1
    return events


def deployment_analytics(deployment, days=7):
    """Aggregate analytics for a single website/API deployment.

    ``online`` is the real business presence (enabled + configured business
    hours in the organization timezone) — never "the AI server is alive".
    """
    organization = deployment.organization

    conversations = Conversation.objects.filter(deployment=deployment)
    total_conversations = conversations.count()

    unique_visitors = (
        conversations.exclude(visitor_id__isnull=True)
        .exclude(visitor_id="")
        .values("visitor_id")
        .distinct()
        .count()
    )

    total_messages = ConversationMessage.objects.filter(
        conversation__in=conversations
    ).count()

    average_messages_per_conversation = (
        round(total_messages / total_conversations, 2) if total_conversations else 0
    )

    appointments = Appointment.objects.filter(
        conversation__deployment=deployment
    ).exclude(status=Appointment.Status.CANCELLED)
    appointments_booked = appointments.count()

    tool_calls = ConversationMessage.objects.filter(
        conversation__in=conversations, role=ConversationMessage.Role.TOOL
    ).count()

    transfers = _count_transfers(conversations)

    zone = organization_zone(organization)
    now = timezone.now().astimezone(zone)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_day - dt_timezone.timedelta(days=now.weekday())
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    started = {}
    for label, start in (
        ("today", start_of_day),
        ("this_week", start_of_week),
        ("this_month", start_of_month),
    ):
        started[label] = conversations.filter(started_at__gte=start).count()

    by_day = []
    for day, start, end in _day_bounds(organization, days):
        by_day.append(
            {
                "day": day.isoformat(),
                "count": conversations.filter(
                    started_at__gte=start, started_at__lt=end
                ).count(),
            }
        )

    return {
        "deployment_id": deployment.id,
        "agent_name": deployment.agent.name,
        "deployment_name": deployment.name or deployment.widget_title or deployment.agent.name,
        "channel": deployment.channel,
        "online": bool(
            deployment.enabled
            and deployment.agent.is_active
            and is_business_open(organization)
        ),
        "business_name": organization.display_name,
        "timezone": organization.timezone or "UTC",
        "business_hours": open_ranges(organization),
        "total_conversations": total_conversations,
        "unique_visitors": unique_visitors,
        "total_messages": total_messages,
        "average_messages_per_conversation": average_messages_per_conversation,
        "conversations_started": started,
        "appointments_booked": appointments_booked,
        "tool_calls": tool_calls,
        "transfers": transfers,
        "days": days,
        "conversations_by_day": by_day,
    }