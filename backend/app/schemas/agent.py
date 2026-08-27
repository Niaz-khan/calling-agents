from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    system_prompt: str = Field(
        min_length=1,
    )


class AgentUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    description: str | None = None

    system_prompt: str | None = Field(
        default=None,
        min_length=1,
    )

    is_active: bool | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str | None
    system_prompt: str
    is_active: bool
    created_at: datetime
    updated_at: datetime