from datetime import datetime

from pydantic import BaseModel, Field


class PhoneNumberCreate(BaseModel):
    agent_id: int
    phone_number: str = Field(
        min_length=1,
        max_length=50,
    )
    provider: str = Field(
        default="twilio",
        min_length=1,
        max_length=50,
    )
    provider_number_id: str | None = Field(
        default=None,
        max_length=100,
    )


class PhoneNumberUpdate(BaseModel):
    is_active: bool | None = None
    agent_id: int | None = None
    provider_number_id: str | None = None


class PhoneNumberResponse(BaseModel):
    id: int
    owner_id: int
    agent_id: int
    phone_number: str
    provider: str
    provider_number_id: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}