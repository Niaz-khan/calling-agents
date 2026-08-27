from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.appointment import Appointment, AppointmentStatus
from app.models.call import Call, CallStatus
from app.models.customer import Customer
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsOverview,
    CallCountByDay,
    OutcomeCount,
    RecentCall,
)


router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get("/overview", response_model=AnalyticsOverview)
def analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent_ids = select(Agent.id).where(Agent.owner_id == current_user.id)

    calls = db.scalars(
        select(Call).where(Call.agent_id.in_(agent_ids))
    ).all()

    total_calls = len(calls)
    in_progress_calls = sum(1 for c in calls if c.status == CallStatus.IN_PROGRESS)
    completed_calls = sum(1 for c in calls if c.status == CallStatus.COMPLETED)
    failed_calls = sum(1 for c in calls if c.status == CallStatus.FAILED)
    transferred_calls = sum(1 for c in calls if c.status == CallStatus.TRANSFERRED)
    missed_calls = sum(1 for c in calls if c.status == CallStatus.RINGING)

    durations = [
        (c.ended_at - c.started_at).total_seconds()
        for c in calls
        if c.ended_at is not None
    ]

    average_duration_seconds = (
        sum(durations) / len(durations)
        if durations
        else None
    )

    outcome_breakdown: dict[str, int] = {}

    for call in calls:
        if call.outcome is not None:
            key = call.outcome.value
            outcome_breakdown[key] = outcome_breakdown.get(key, 0) + 1

    outcome_counts = [
        OutcomeCount(outcome=key, count=value)
        for key, value in sorted(
            outcome_breakdown.items(),
            key=lambda pair: pair[1],
            reverse=True,
        )
    ]

    today = datetime.now(timezone.utc).date()

    days = [today - timedelta(days=delta) for delta in range(6, -1, -1)]

    counts_by_day = {day: 0 for day in days}

    for call in calls:
        started = call.started_at

        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        day = started.date()

        if day in counts_by_day:
            counts_by_day[day] += 1

    calls_last_7_days = [
        CallCountByDay(day=day.isoformat(), count=count)
        for day, count in counts_by_day.items()
    ]

    agent_names = {
        agent.id: agent.name
        for agent in db.scalars(
            select(Agent).where(Agent.id.in_(agent_ids))
        ).all()
    }

    recent_calls = [
        RecentCall(
            id=call.id,
            agent_id=call.agent_id,
            agent_name=agent_names.get(call.agent_id),
            caller_number=call.caller_number,
            direction=call.direction.value,
            status=call.status.value,
            outcome=call.outcome.value if call.outcome else None,
            started_at=call.started_at,
            ended_at=call.ended_at,
            duration_seconds=(
                int((call.ended_at - call.started_at).total_seconds())
                if call.ended_at and call.started_at
                else None
            ),
        )
        for call in sorted(
            calls,
            key=lambda call: call.started_at,
            reverse=True,
        )[:5]
    ]

    appointments_scheduled = db.scalar(
        select(func.count(Appointment.id)).join(
            Agent, Agent.id == Appointment.agent_id
        ).where(
            Agent.owner_id == current_user.id,
            Appointment.status == AppointmentStatus.SCHEDULED,
        )
    ) or 0

    appointments_cancelled = db.scalar(
        select(func.count(Appointment.id)).join(
            Agent, Agent.id == Appointment.agent_id
        ).where(
            Agent.owner_id == current_user.id,
            Appointment.status == AppointmentStatus.CANCELLED,
        )
    ) or 0

    total_customers = db.scalar(
        select(func.count(Customer.id)).where(
            Customer.owner_id == current_user.id,
        )
    ) or 0

    total_agents = db.scalar(
        select(func.count(Agent.id)).where(
            Agent.owner_id == current_user.id,
        )
    ) or 0

    return AnalyticsOverview(
        total_calls=total_calls,
        in_progress_calls=in_progress_calls,
        completed_calls=completed_calls,
        failed_calls=failed_calls,
        transferred_calls=transferred_calls,
        missed_calls=missed_calls,
        average_duration_seconds=average_duration_seconds,
        total_customers=total_customers,
        total_agents=total_agents,
        appointments_scheduled=appointments_scheduled,
        appointments_cancelled=appointments_cancelled,
        outcome_breakdown=outcome_counts,
        calls_last_7_days=calls_last_7_days,
        recent_calls=recent_calls,
    )
