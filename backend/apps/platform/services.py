"""Cross-organization metrics used by the platform dashboard/analytics.

These queries intentionally ignore tenant scoping -- they are the platform
admin's view across every organization. Gate every call site with the
``IsPlatformAdmin`` permission.
"""

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.agents.models import Agent, AgentDeployment
from apps.appointments.models import Appointment
from apps.conversations.models import Conversation, PhoneCallStatus
from apps.crm.models import Customer
from apps.tenancy.models import Organization, OrganizationMember


def organization_summary(org):
    return {
        "members_count": OrganizationMember.objects.filter(organization=org).count(),
        "agents_count": Agent.objects.filter(organization=org).count(),
        "active_agents_count": Agent.objects.filter(organization=org, is_active=True).count(),
        "deployments_count": AgentDeployment.objects.filter(organization=org).count(),
        "phone_numbers_count": org.phone_numbers.count(),
        "calls_count": Conversation.objects.filter(organization=org, phone_call__isnull=False).count(),
        "conversations_count": Conversation.objects.filter(organization=org).count(),
        "customers_count": Customer.objects.filter(organization=org).count(),
        "appointments_count": Appointment.objects.filter(organization=org).count(),
        "knowledge_bases_count": org.knowledge_bases.count(),
    }


def growth_series(days=14):
    today = timezone.now().date()
    start = today - timedelta(days=days - 1)

    def series(queryset):
        rows = (
            queryset.filter(created_at__date__gte=start)
            .extra(select={"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        by_day = {row["day"].isoformat(): row["count"] for row in rows}
        out = []
        running = 0
        for i in range(days):
            day = (start + timedelta(days=i)).isoformat()
            running += by_day.get(day, 0)
            out.append({"day": day, "count": running})
        return out

    calls = (
        Conversation.objects.filter(phone_call__isnull=False, started_at__date__gte=start)
        .extra(select={"day": "date(started_at)"})
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    calls_by_day = {row["day"].isoformat(): row["count"] for row in calls}
    call_series = [
        {"day": (start + timedelta(days=i)).isoformat(), "count": calls_by_day.get((start + timedelta(days=i)).isoformat(), 0)}
        for i in range(days)
    ]

    return {
        "organizations_growth": series(Organization.objects.all()),
        "agents_created": series(Agent.objects.all()),
        "deployments_created": series(AgentDeployment.objects.all()),
        "calls_by_day": call_series,
    }


def dashboard_metrics():
    now = timezone.now()
    today = now.date()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    orgs = Organization.objects.all()
    calls = Conversation.objects.filter(phone_call__isnull=False)

    conversations = Conversation.objects.all()
    outcome_rows = (
        conversations.exclude(outcome__isnull=True)
        .values("outcome")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    channel_rows = conversations.values("channel").annotate(count=Count("id")).order_by("-count")

    return {
        "total_organizations": orgs.count(),
        "active_organizations": orgs.filter(is_active=True).count(),
        "inactive_organizations": orgs.filter(is_active=False).count(),
        "total_users": User_count_total(),
        "total_memberships": OrganizationMember.objects.count(),
        "active_agents": Agent.objects.filter(is_active=True).count(),
        "total_agents": Agent.objects.count(),
        "calls_today": calls.filter(started_at__date=today).count(),
        "calls_this_month": calls.filter(started_at__gte=month_start).count(),
        "total_calls": calls.count(),
        "total_conversations": conversations.count(),
        "appointments_scheduled": Appointment.objects.filter(
            status=Appointment.Status.SCHEDULED
        ).count(),
        "total_appointments": Appointment.objects.count(),
        "total_customers": Customer.objects.count(),
        "website_deployments": AgentDeployment.objects.filter(
            channel=AgentDeployment.Channel.WEBSITE
        ).count(),
        "phone_deployments": AgentDeployment.objects.filter(
            channel=AgentDeployment.Channel.PHONE
        ).count(),
        "total_deployments": AgentDeployment.objects.count(),
        "growth": growth_series(14),
        "outcome_breakdown": list(outcome_rows),
        "channel_breakdown": list(channel_rows),
    }


def User_count_total():
    from apps.accounts.models import User

    return User.objects.count()


def recent_activity(limit=12):
    """Most recent creations across the major platform resources."""
    events = []

    def push(kind, label, org_name, timestamp):
        if timestamp is None:
            return
        events.append(
            {
                "type": kind,
                "label": label,
                "organization": org_name or "",
                "action": {"organization": "created", "agent": "created", "deployment": "created", "user": "registered", "call": "received", "appointment": "booked"}.get(
                    kind, kind
                ),
                "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else timestamp,
            }
        )

    for org in Organization.objects.order_by("-created_at")[:limit]:
        push("organization", org.name, org.name, org.created_at)
    for member in OrganizationMember.objects.select_related("organization", "user").order_by("-created_at")[:limit]:
        push("user", member.user.email, member.organization.name, member.created_at)
    for agent in Agent.objects.select_related("organization").order_by("-created_at")[:limit]:
        push("agent", agent.name, agent.organization.name, agent.created_at)
    for dep in AgentDeployment.objects.select_related("organization", "agent").order_by("-created_at")[:limit]:
        push("deployment", f"{dep.channel} · {dep.agent.name}", dep.organization.name, dep.created_at)
    for call in (
        Conversation.objects.filter(phone_call__isnull=False)
        .select_related("organization", "agent", "phone_call")
        .order_by("-started_at")[:limit]
    ):
        push(
            "call",
            f"{call.phone_call.direction.lower()} · {call.phone_call.caller_number}",
            call.organization.name,
            call.started_at,
        )
    for apt in Appointment.objects.select_related("organization").order_by("-created_at")[:limit]:
        push("appointment", apt.customer_name, apt.organization.name, apt.created_at)

    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]


def platform_analytics(days=30):
    growth = growth_series(days)
    calls = Conversation.objects.filter(phone_call__isnull=False)
    conversations = Conversation.objects.all()

    status_counts = {
        status.value: conversations.filter(phone_call__provider_status=status).count()
        for status in PhoneCallStatus
    }

    return {
        "days": days,
        "growth": growth,
        "totals": {
            "organizations": Organization.objects.count(),
            "users": User_count_total(),
            "agents": Agent.objects.count(),
            "deployments": AgentDeployment.objects.count(),
            "conversations": conversations.count(),
            "phone_calls": calls.count(),
            "customers": Customer.objects.count(),
            "appointments": Appointment.objects.count(),
        },
        "call_status": status_counts,
        "channel_breakdown": list(
            conversations.values("channel").annotate(count=Count("id")).order_by("-count")
        ),
        "outcome_breakdown": list(
            conversations.exclude(outcome__isnull=True)
            .values("outcome")
            .annotate(count=Count("id"))
            .order_by("-count")
        ),
    }