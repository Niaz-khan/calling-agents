import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, enum.Enum):
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TRANSFERRED = "transferred"


class CallOutcome(str, enum.Enum):
    APPOINTMENT_BOOKED = "appointment_booked"
    APPOINTMENT_REQUESTED = "appointment_requested"
    INFORMATION_PROVIDED = "information_provided"
    CALLBACK_REQUESTED = "callback_requested"
    TRANSFERRED_TO_HUMAN = "transferred_to_human"
    NO_RESOLUTION = "no_resolution"
    CUSTOMER_HUNG_UP = "customer_hung_up"
    UNKNOWN = "unknown"


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True)

    agent_id: Mapped[int] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    phone_number_id: Mapped[int | None] = mapped_column(
        ForeignKey("phone_numbers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider_call_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )

    direction: Mapped[CallDirection] = mapped_column(
        Enum(CallDirection),
        nullable=False,
    )

    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus),
        default=CallStatus.RINGING,
        nullable=False,
    )

    caller_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    recording_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    transcript: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    outcome: Mapped[CallOutcome | None] = mapped_column(
        Enum(CallOutcome),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )