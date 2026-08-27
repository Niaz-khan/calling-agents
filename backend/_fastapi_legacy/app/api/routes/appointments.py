from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.appointment import (
    Appointment,
    AppointmentStatus,
)
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
)
from app.services.appointments import create_appointment


router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
)


def _get_user_appointment(
    db: Session,
    appointment_id: int,
    user_id: int,
) -> Appointment | None:
    statement = (
        select(Appointment)
        .join(Agent, Agent.id == Appointment.agent_id)
        .where(
            Appointment.id == appointment_id,
            Agent.owner_id == user_id,
        )
    )

    return db.scalar(statement)


def _get_user_agent(
    db: Session,
    agent_id: int,
    user_id: int,
) -> Agent | None:
    return db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.owner_id == user_id,
        )
    )


@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment_route(
    data: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = _get_user_agent(db, data.agent_id, current_user.id)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    try:
        appointment = create_appointment(
            db=db,
            agent_id=agent.id,
            call_id=None,
            customer_name=data.customer_name,
            customer_phone=data.customer_phone,
            start_time=data.start_time,
            end_time=data.end_time,
            notes=data.notes,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )

    return appointment


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    agent_id: int | None = None,
    status_filter: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(Appointment)
        .join(Agent, Agent.id == Appointment.agent_id)
        .where(Agent.owner_id == current_user.id)
        .order_by(Appointment.start_time.asc())
    )

    if agent_id is not None:
        statement = statement.where(Appointment.agent_id == agent_id)

    if status_filter is not None:
        statement = statement.where(Appointment.status == status_filter)

    if date_from is not None:
        statement = statement.where(Appointment.start_time >= date_from)

    if date_to is not None:
        statement = statement.where(Appointment.start_time <= date_to)

    return db.scalars(statement).all()


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = _get_user_appointment(
        db,
        appointment_id,
        current_user.id,
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return appointment


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    data: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = _get_user_appointment(
        db,
        appointment_id,
        current_user.id,
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    new_start = update_data.get("start_time", appointment.start_time)
    new_end = update_data.get("end_time", appointment.end_time)

    if new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment end time must be after start time",
        )

    if "start_time" in update_data or "end_time" in update_data:
        overlapping = db.scalar(
            select(Appointment).where(
                Appointment.agent_id == appointment.agent_id,
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.id != appointment.id,
                Appointment.start_time < new_end,
                Appointment.end_time > new_start,
            )
        )

        if overlapping is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The requested time is not available",
            )

    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    appointment = _get_user_appointment(
        db,
        appointment_id,
        current_user.id,
    )

    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    db.delete(appointment)
    db.commit()

    return None