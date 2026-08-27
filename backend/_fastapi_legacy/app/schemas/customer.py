from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CustomerCreate(BaseModel):
    phone_number: str = Field(
        min_length=1,
        max_length=50,
    )

    name: str | None = Field(
        default=None,
        max_length=255,
    )

    email: EmailStr | None = None

    notes: str | None = None


class CustomerUpdate(BaseModel):
    phone_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    name: str | None = Field(
        default=None,
        max_length=255,
    )

    email: EmailStr | None = None

    notes: str | None = None


class CustomerResponse(BaseModel):
    id: int
    owner_id: int
    name: str | None
    phone_number: str
    email: str | None
    notes: str | None
    memory: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}