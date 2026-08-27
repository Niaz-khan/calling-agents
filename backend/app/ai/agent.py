from sqlalchemy.orm import Session

from app.ai.prompts import DEFAULT_AGENT_PROMPT
from app.ai.provider import generate_response
from app.ai.tools import TOOL_DEFINITIONS, execute_tool


MAX_TOOL_ROUNDS = 5


async def run_agent(
    system_prompt: str | None,
    conversation: list[dict],
    db: Session,
    agent_id: int,
    call_id: int | None = None,
) -> str:
    prompt = system_prompt or DEFAULT_AGENT_PROMPT

    messages = [
        {"role": "system", "content": prompt},
        *conversation,
    ]

    for _ in range(MAX_TOOL_ROUNDS):
        response = await generate_response(messages, tools=TOOL_DEFINITIONS)

        tool_calls = response.get("tool_calls", [])

        if not tool_calls:
            return response["content"]

        messages.append({
            "role": "assistant",
            "content": response.get("content") or None,
            "tool_calls": tool_calls,
        })

        for tool_call in tool_calls:
            result = execute_tool(
                db=db,
                agent_id=agent_id,
                call_id=call_id,
                tool_name=tool_call["function"]["name"],
                arguments=tool_call["function"]["arguments"],
            )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            })

    return "I apologize, but I'm having trouble processing your request. Please try again."
