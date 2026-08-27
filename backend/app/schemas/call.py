from datetime import datetime

from pydantic import BaseModel, Field


class CallCreate(BaseModel):
    caller_number: str = Field(
        min_length=1,
        max_length=50,
    )

    direction: str = "inbound"


class CallResponse(BaseModel):
    id: int
    agent_id: int
    customer_id: int | None
    caller_number: str
    direction: str
    status: str
    started_at: datetime
    ended_at: datetime | None


class MessageCreate(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000,
    )


class MessageResponse(BaseModel):
    call_id: int
    role: str
    message: str