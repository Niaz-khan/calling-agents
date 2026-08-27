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
from app.schemas.call import (
    CallCreate,
    CallResponse,
    MessageCreate,
    MessageResponse,
)


router = APIRouter(
    prefix="/calls",
    tags=["calls"],
)


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

    call = Call(
        agent_id=agent.id,
        caller_number=data.caller_number,
        direction=direction,
        status=CallStatus.IN_PROGRESS,
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    return call

@router.post("/{call_id}/messages", response_model=MessageResponse,)
async def send_message(call_id: int, data: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),):
    # 1. Find the call through the user's agent
    statement = (
        select(Call)
        .join(Agent, Agent.id == Call.agent_id)
        .where(
            Call.id == call_id,
            Agent.owner_id == current_user.id,
        )
    )

    call = db.scalar(statement)

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

    # 2. Load the agent
    agent = db.get(Agent, call.agent_id)

    if agent is None or not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # 3. Save user message
    user_message = CallMessage(
        call_id=call.id,
        role=MessageRole.USER,
        content=data.message,
    )

    db.add(user_message)
    db.commit()

    # 4. Load conversation history
    history_statement = (
        select(CallMessage)
        .where(CallMessage.call_id == call.id)
        .order_by(CallMessage.created_at.asc(), CallMessage.id.asc())
    )

    history = db.scalars(history_statement).all()

    conversation = []

    for message in history:
        if message.role == MessageRole.USER:
            conversation.append(
                {
                    "role": "user",
                    "content": message.content,
                }
            )

        elif message.role == MessageRole.ASSISTANT:
            conversation.append(
                {
                    "role": "assistant",
                    "content": message.content,
                }
            )

    # 5. Run the AI agent
    ai_response = await run_agent(
        system_prompt=agent.system_prompt,
        conversation=conversation,
    )

    # 6. Save AI response
    assistant_message = CallMessage(
        call_id=call.id,
        role=MessageRole.ASSISTANT,
        content=ai_response,
    )

    db.add(assistant_message)
    db.commit()

    return MessageResponse(
        call_id=call.id,
        role="assistant",
        message=ai_response,
    )