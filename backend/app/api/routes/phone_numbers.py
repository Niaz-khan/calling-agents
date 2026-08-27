from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.phone_number import PhoneNumber
from app.models.user import User
from app.schemas.phone_number import (
    PhoneNumberCreate,
    PhoneNumberResponse,
    PhoneNumberUpdate,
)


router = APIRouter(
    prefix="/phone-numbers",
    tags=["phone-numbers"],
)


def _get_user_phone_number(
    db: Session,
    phone_number_id: int,
    user_id: int,
) -> PhoneNumber | None:
    return db.scalar(
        select(PhoneNumber).where(
            PhoneNumber.id == phone_number_id,
            PhoneNumber.owner_id == user_id,
        )
    )


@router.post("", response_model=PhoneNumberResponse, status_code=status.HTTP_201_CREATED)
def create_phone_number(
    data: PhoneNumberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.scalar(
        select(Agent).where(
            Agent.id == data.agent_id,
            Agent.owner_id == current_user.id,
        )
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    existing = db.scalar(
        select(PhoneNumber).where(
            PhoneNumber.phone_number == data.phone_number,
            PhoneNumber.owner_id == current_user.id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered",
        )

    phone_number = PhoneNumber(
        owner_id=current_user.id,
        agent_id=agent.id,
        phone_number=data.phone_number,
        provider=data.provider,
        provider_number_id=data.provider_number_id,
    )

    db.add(phone_number)
    db.commit()
    db.refresh(phone_number)

    return phone_number


@router.get("", response_model=list[PhoneNumberResponse])
def list_phone_numbers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(PhoneNumber)
        .where(PhoneNumber.owner_id == current_user.id)
        .order_by(PhoneNumber.created_at.desc())
    ).all()


@router.get("/{phone_number_id}", response_model=PhoneNumberResponse)
def get_phone_number(
    phone_number_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone_number = _get_user_phone_number(db, phone_number_id, current_user.id)

    if phone_number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found",
        )

    return phone_number


@router.patch("/{phone_number_id}", response_model=PhoneNumberResponse)
def update_phone_number(
    phone_number_id: int,
    data: PhoneNumberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone_number = _get_user_phone_number(db, phone_number_id, current_user.id)

    if phone_number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found",
        )

    if data.agent_id is not None:
        agent = db.scalar(
            select(Agent).where(
                Agent.id == data.agent_id,
                Agent.owner_id == current_user.id,
            )
        )

        if agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        phone_number.agent_id = agent.id

    if data.is_active is not None:
        phone_number.is_active = data.is_active

    if data.provider_number_id is not None:
        phone_number.provider_number_id = data.provider_number_id

    db.commit()
    db.refresh(phone_number)

    return phone_number


@router.delete("/{phone_number_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_phone_number(
    phone_number_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone_number = _get_user_phone_number(db, phone_number_id, current_user.id)

    if phone_number is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phone number not found",
        )

    db.delete(phone_number)
    db.commit()