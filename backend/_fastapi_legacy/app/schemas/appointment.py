from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    agent_id: int

    customer_name: str = Field(
        min_length=1,
        max_length=255,
    )

    customer_phone: str = Field(
        min_length=1,
        max_length=50,
    )

    start_time: datetime

    end_time: datetime

    notes: str | None = None


class AppointmentUpdate(BaseModel):
    status: Literal["scheduled", "cancelled", "completed"] | None = None

    start_time: datetime | None = None

    end_time: datetime | None = None

    notes: str | None = None


class AppointmentResponse(BaseModel):
    id: int
    agent_id: int
    call_id: int | None
    customer_name: str
    customer_phone: str
    start_time: datetime
    end_time: datetime
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}