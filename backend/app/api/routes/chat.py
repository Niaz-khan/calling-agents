from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agent import run_agent
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.call import Call
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(
    prefix="/agents",
    tags=["chat"],
)


@router.post(
    "/{agent_id}/chat",
    response_model=ChatResponse,
)
async def chat_with_agent(agent_id: int, data: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db),):
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id,
        Agent.is_active.is_(True),
    )

    agent = db.scalar(statement)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    conversation = [
        {
            "role": "user",
            "content": data.message,
        }
    ]

    response = await run_agent(
        system_prompt=agent.system_prompt,
        conversation=conversation,
    )

    return ChatResponse(
        agent_id=agent.id,
        message=response,
    )