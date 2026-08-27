from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import Agent
from appointments.models import Appointment
from conversations.models import Conversation, PhoneCallStatus
from crm.models import Customer
from tenancy.access import get_request_organization


def _call_status_counts(calls):
    counts = {item: 0 for item in PhoneCallStatus.values}
    for conversation in calls:
        phone_call = conversation.phone_call
        if phone_call is not None and phone_call.provider_status in counts:
            counts[phone_call.provider_status] += 1
    return counts


def _duration_seconds(conversation):
    if conversation.started_at is None or conversation.ended_at is None:
        return None
    return int((conversation.ended_at - conversation.started_at).total_seconds())


class AnalyticsOverviewView(APIView):
    def get(self, request):
        organization = get_request_organization(request)
        if organization is None:
            raise NotFound("Organization not found")

        calls = list(
            Conversation.objects.filter(
                organization=organization, phone_call__isnull=False
            )
            .select_related("agent", "phone_call")
            .order_by("started_at")
        )

        counts = _call_status_counts(calls)
        status_map = {
            PhoneCallStatus.RINGING: "missed_calls",
            PhoneCallStatus.IN_PROGRESS: "in_progress_calls",
            PhoneCallStatus.COMPLETED: "completed_calls",
            PhoneCallStatus.FAILED: "failed_calls",
            PhoneCallStatus.TRANSFERRED: "transferred_calls",
        }
        totals = {value: counts[key] for key, value in status_map.items()}

        durations = [
            (conversation.ended_at - conversation.started_at).total_seconds()
            for conversation in calls
            if conversation.ended_at is not None and conversation.started_at is not None
        ]
        average_duration_seconds = (
            sum(durations) / len(durations) if durations else None
        )

        outcome_breakdown = {}
        for conversation in calls:
            if conversation.outcome is not None:
                key = conversation.outcome.lower()
                outcome_breakdown[key] = outcome_breakdown.get(key, 0) + 1
        outcome_counts = [
            {"outcome": key, "count": value}
            for key, value in sorted(
                outcome_breakdown.items(), key=lambda item: item[1], reverse=True
            )
        ]

        today = timezone.now().date()
        days = [today - timedelta(days=delta) for delta in range(6, -1, -1)]
        counts_by_day = {day: 0 for day in days}
        for conversation in calls:
            day = conversation.started_at.date()
            if day in counts_by_day:
                counts_by_day[day] += 1
        calls_last_7_days = [
            {"day": day.isoformat(), "count": count}
            for day, count in counts_by_day.items()
        ]

        recent_calls = [
            {
                "id": conversation.id,
                "agent_id": conversation.agent_id,
                "agent_name": conversation.agent.name,
                "caller_number": conversation.phone_call.caller_number,
                "direction": conversation.phone_call.direction.lower(),
                "status": conversation.phone_call.provider_status.lower(),
                "outcome": conversation.outcome.lower() if conversation.outcome else None,
                "started_at": conversation.started_at,
                "ended_at": conversation.ended_at,
                "duration_seconds": _duration_seconds(conversation),
            }
            for conversation in sorted(
                calls, key=lambda item: item.started_at, reverse=True
            )[:5]
        ]

        appointments = Appointment.objects.filter(organization=organization)
        overview = {
            "total_calls": len(calls),
            **totals,
            "average_duration_seconds": average_duration_seconds,
            "total_customers": Customer.objects.filter(
                organization=organization
            ).count(),
            "total_agents": Agent.objects.filter(organization=organization).count(),
            "appointments_scheduled": appointments.filter(
                status=Appointment.Status.SCHEDULED
            ).count(),
            "appointments_cancelled": appointments.filter(
                status=Appointment.Status.CANCELLED
            ).count(),
            "outcome_breakdown": outcome_counts,
            "calls_last_7_days": calls_last_7_days,
            "recent_calls": recent_calls,
        }
        return Response(overview)