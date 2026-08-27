from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
)


router = APIRouter(
    prefix="/agents",
    tags=["agents"],
)


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = Agent(
        owner_id=current_user.id,
        name=agent_data.name,
        description=agent_data.description,
        system_prompt=agent_data.system_prompt,
    )

    db.add(agent)
    db.commit()
    db.refresh(agent)

    return agent


@router.get(
    "",
    response_model=list[AgentResponse],
)
def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(Agent)
        .where(Agent.owner_id == current_user.id)
        .order_by(Agent.id.desc())
    )

    return db.scalars(statement).all()


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
)
def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id,
    )

    agent = db.scalar(statement)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return agent


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
)
def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id,
    )

    agent = db.scalar(statement)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    update_data = agent_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)

    return agent


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.owner_id == current_user.id,
    )

    agent = db.scalar(statement)

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    db.delete(agent)
    db.commit()

    return None