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
    outcome: str | None
    summary: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class CallListResponse(BaseModel):
    id: int
    agent_id: int
    agent_name: str
    customer_id: int | None
    caller_number: str
    direction: str
    status: str
    outcome: str | None
    summary: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None


class CallDetailResponse(BaseModel):
    id: int
    agent_id: int
    customer_id: int | None
    caller_number: str
    direction: str
    status: str
    outcome: str | None
    summary: str | None
    started_at: datetime
    ended_at: datetime | None
    messages: list["MessageDetailResponse"]

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000,
    )


class MessageResponse(BaseModel):
    call_id: int
    role: str
    message: str


class MessageDetailResponse(BaseModel):
    id: int
    role: str
    content: str
    tool_call_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
