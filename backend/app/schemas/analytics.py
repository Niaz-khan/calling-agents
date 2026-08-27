from datetime import datetime

from pydantic import BaseModel


class CallCountByDay(BaseModel):
    day: str
    count: int


class RecentCall(BaseModel):
    id: int
    agent_id: int
    agent_name: str | None
    caller_number: str
    direction: str
    status: str
    outcome: str | None
    started_at: datetime
    ended_at: datetime | None


class AnalyticsOverview(BaseModel):
    total_calls: int
    in_progress_calls: int
    completed_calls: int
    failed_calls: int
    transferred_calls: int
    missed_calls: int
    average_duration_seconds: float | None
    total_customers: int
    total_agents: int
    appointments_scheduled: int
    appointments_cancelled: int
    outcome_breakdown: dict[str, int]
    calls_last_7_days: list[CallCountByDay]
    recent_calls: list[RecentCall]