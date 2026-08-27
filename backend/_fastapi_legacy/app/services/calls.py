import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.agent import AgentResult, run_agent
from app.models.agent import Agent
from app.models.call import Call
from app.models.call_message import CallMessage, MessageRole
from app.services.call_intelligence import get_customer_memory


def build_conversation_history(db: Session, call: Call) -> list[dict]:
    statement = (
        select(CallMessage)
        .where(CallMessage.call_id == call.id)
        .order_by(CallMessage.created_at.asc(), CallMessage.id.asc())
    )

    history = db.scalars(statement).all()

    conversation: list[dict] = []

    memory = get_customer_memory(db, call)

    if memory:
        conversation.append(
            {
                "role": "system",
                "content": (
                    "These are notes about this customer from previous calls. "
                    "Use them to provide personalized service.\n\n"
                    f"{memory}"
                ),
            }
        )

    for message in history:
        if message.role == MessageRole.USER:
            conversation.append(
                {
                    "role": "user",
                    "content": message.content,
                }
            )

        elif message.role == MessageRole.ASSISTANT:
            if message.tool_call_id is not None:
                continue

            try:
                payload = json.loads(message.content)
            except json.JSONDecodeError:
                payload = None

            tool_calls = payload.get("tool_calls") if payload else None

            if tool_calls:
                conversation.append(
                    {
                        "role": "assistant",
                        "content": payload.get("content"),
                        "tool_calls": tool_calls,
                    }
                )
            else:
                conversation.append(
                    {
                        "role": "assistant",
                        "content": message.content,
                    }
                )

        elif message.role == MessageRole.TOOL:
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                }
            )

    return conversation


async def run_agent_turn(
    db: Session,
    call: Call,
    agent: Agent,
    user_text: str,
) -> AgentResult:
    user_message = CallMessage(
        call_id=call.id,
        role=MessageRole.USER,
        content=user_text,
    )

    db.add(user_message)
    db.commit()

    conversation = build_conversation_history(db, call)

    result = await run_agent(
        system_prompt=agent.system_prompt,
        conversation=conversation,
        db=db,
        agent_id=agent.id,
        call_id=call.id,
    )

    for msg in result.messages:
        if msg["role"] == "assistant":
            tool_info = {
                "tool_calls": msg.get("tool_calls", []),
            }
            if msg.get("content"):
                tool_info["content"] = msg["content"]

            assistant_message = CallMessage(
                call_id=call.id,
                role=MessageRole.ASSISTANT,
                content=json.dumps(tool_info),
            )
            db.add(assistant_message)

        elif msg["role"] == "tool":
            tool_message = CallMessage(
                call_id=call.id,
                role=MessageRole.TOOL,
                content=msg["content"],
                tool_call_id=msg.get("tool_call_id"),
            )
            db.add(tool_message)

    assistant_message = CallMessage(
        call_id=call.id,
        role=MessageRole.ASSISTANT,
        content=result.response,
    )

    db.add(assistant_message)
    db.commit()

    return result