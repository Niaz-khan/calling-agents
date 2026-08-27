import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent
from app.models.call import Call, CallDirection, CallStatus
from app.models.user import User
from app.ai.agent import run_agent
from app.auth.dependencies import get_current_user
from app.models.call_message import CallMessage, MessageRole
from app.services.calls import run_agent_turn
from app.services.customers import create_customer
from app.services.call_intelligence import finalize_call
from app.schemas.call import (
    CallCreate,
    CallDetailResponse,
    CallResponse,
    MessageCreate,
    MessageDetailResponse,
    MessageResponse,
)


router = APIRouter(
    prefix="/calls",
    tags=["calls"],
)


def _get_user_call(
    db: Session,
    call_id: int,
    user_id: int,
) -> Call | None:
    statement = (
        select(Call)
        .join(Agent, Agent.id == Call.agent_id)
        .where(
            Call.id == call_id,
            Agent.owner_id == user_id,
        )
    )

    return db.scalar(statement)


@router.post(
    "",
    response_model=CallResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_call(data: CallCreate, agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),):
    agent = db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.owner_id == current_user.id,
            Agent.is_active.is_(True),
        )
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    try:
        direction = CallDirection(data.direction)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid call direction",
        )

    customer = create_customer(
        db=db,
        owner_id=current_user.id,
        phone_number=data.caller_number,
    )

    call = Call(
        agent_id=agent.id,
        customer_id=customer.id,
        caller_number=data.caller_number,
        direction=direction,
        status=CallStatus.IN_PROGRESS,
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    return call


@router.get("", response_model=list[CallResponse])
def list_calls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    agent_id: int | None = None,
):
    statement = (
        select(Call)
        .join(Agent, Agent.id == Call.agent_id)
        .where(Agent.owner_id == current_user.id)
        .order_by(Call.started_at.desc())
    )

    if agent_id:
        statement = statement.where(Call.agent_id == agent_id)

    calls = db.scalars(statement).all()
    return calls


@router.get("/{call_id}", response_model=CallDetailResponse)
def get_call(
    call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call = _get_user_call(db, call_id, current_user.id)

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    messages_statement = (
        select(CallMessage)
        .where(CallMessage.call_id == call.id)
        .order_by(CallMessage.created_at.asc(), CallMessage.id.asc())
    )

    messages = db.scalars(messages_statement).all()

    return CallDetailResponse(
        id=call.id,
        agent_id=call.agent_id,
        customer_id=call.customer_id,
        caller_number=call.caller_number,
        direction=call.direction.value,
        status=call.status.value,
        outcome=call.outcome.value if call.outcome else None,
        summary=call.summary,
        started_at=call.started_at,
        ended_at=call.ended_at,
        messages=[
            MessageDetailResponse(
                id=m.id,
                role=m.role.value,
                content=m.content,
                tool_call_id=m.tool_call_id,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.get("/{call_id}/messages", response_model=list[MessageDetailResponse])
def get_call_messages(
    call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call = _get_user_call(db, call_id, current_user.id)

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    messages_statement = (
        select(CallMessage)
        .where(CallMessage.call_id == call.id)
        .order_by(CallMessage.created_at.asc(), CallMessage.id.asc())
    )

    messages = db.scalars(messages_statement).all()

    return [
        MessageDetailResponse(
            id=m.id,
            role=m.role.value,
            content=m.content,
            tool_call_id=m.tool_call_id,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/{call_id}/end", response_model=CallResponse)
async def end_call(
    call_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    call = _get_user_call(db, call_id, current_user.id)

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    if call.status != CallStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call is not active",
        )

    call.status = CallStatus.COMPLETED
    call.ended_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(call)

    try:
        call = await finalize_call(db, call)
    except Exception:
        db.rollback()
        db.refresh(call)

    return call


@router.post("/{call_id}/messages", response_model=MessageResponse,)
async def send_message(call_id: int, data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),):
    call = _get_user_call(db, call_id, current_user.id)

    if call is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found",
        )

    if call.status != CallStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call is not active",
        )

    agent = db.get(Agent, call.agent_id)

    if agent is None or not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    result = await run_agent_turn(db, call, agent, data.message)

    return MessageResponse(
        call_id=call.id,
        role="assistant",
        message=result.response,
    )
