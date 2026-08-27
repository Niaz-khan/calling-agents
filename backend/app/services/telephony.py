from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.call import Call, CallDirection, CallStatus
from app.models.phone_number import PhoneNumber
from app.services.call_intelligence import finalize_call
from app.services.customers import create_customer

PROVIDER_STATUS_TO_CALL_STATUS = {
    "queued": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "in_progress": CallStatus.IN_PROGRESS,
    "completed": CallStatus.COMPLETED,
    "busy": CallStatus.FAILED,
    "no-answer": CallStatus.FAILED,
    "failed": CallStatus.FAILED,
    "canceled": CallStatus.FAILED,
    "missed": CallStatus.FAILED,
}


def resolve_phone_number(
    db: Session,
    phone_number: str,
) -> PhoneNumber | None:
    return db.scalar(
        select(PhoneNumber).where(
            PhoneNumber.phone_number == phone_number,
            PhoneNumber.is_active.is_(True),
        )
    )


def create_inbound_call(
    db: Session,
    phone_number: PhoneNumber,
    from_number: str,
    provider_call_id: str | None,
) -> Call:
    agent = db.get(Agent, phone_number.agent_id)

    if agent is None:
        raise ValueError("Phone number has no agent")

    customer = create_customer(
        db=db,
        owner_id=phone_number.owner_id,
        phone_number=from_number,
    )

    call = Call(
        agent_id=agent.id,
        customer_id=customer.id,
        caller_number=from_number,
        direction=CallDirection.INBOUND,
        status=CallStatus.RINGING,
        provider_call_id=provider_call_id,
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    return call


def apply_provider_status(
    db: Session,
    provider_call_id: str,
    provider_status: str,
) -> Call | None:
    if not provider_call_id:
        return None

    call = db.scalar(
        select(Call).where(Call.provider_call_id == provider_call_id)
    )

    if call is None:
        return None

    status = PROVIDER_STATUS_TO_CALL_STATUS.get(
        provider_status.lower().strip()
    )

    if status is None:
        return call

    if status == CallStatus.FAILED:
        if call.status == CallStatus.COMPLETED:
            return call
        call.status = CallStatus.FAILED
        db.commit()
        db.refresh(call)
        return call

    if status == CallStatus.IN_PROGRESS:
        if call.status != CallStatus.IN_PROGRESS:
            call.status = CallStatus.IN_PROGRESS
            db.commit()
            db.refresh(call)
        return call

    if status == CallStatus.COMPLETED:
        if call.status == CallStatus.COMPLETED and call.summary:
            return call

        call.status = CallStatus.COMPLETED
        db.commit()
        db.refresh(call)

        try:
            call = finalize_call(db, call)
        except Exception:
            db.rollback()
            db.refresh(call)

        return call

    return call