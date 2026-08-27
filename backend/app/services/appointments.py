from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import (
    Appointment,
    AppointmentStatus,
)


def check_availability(db: Session, agent_id: int, start_time: datetime, end_time: datetime,) -> bool:
    statement = select(Appointment).where(
        Appointment.agent_id == agent_id,
        Appointment.status == AppointmentStatus.SCHEDULED,
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )

    existing = db.scalar(statement)

    return existing is None

def create_appointment(db: Session, agent_id: int, call_id: int | None, customer_name: str, customer_phone: str, start_time: datetime, end_time: datetime, notes: str | None = None,) -> Appointment:

    if end_time <= start_time:
        raise ValueError(
            "Appointment end time must be after start time"
        )

    if not check_availability(
        db=db,
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
    ):
        raise ValueError(
            "The requested time is not available"
        )

    appointment = Appointment(
        agent_id=agent_id,
        call_id=call_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        start_time=start_time,
        end_time=end_time,
        status=AppointmentStatus.SCHEDULED,
        notes=notes,
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return appointment