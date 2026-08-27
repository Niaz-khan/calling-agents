from .prompts import DEFAULT_AGENT_PROMPT
from .provider import generate_response


async def run_agent(system_prompt: str | None, conversation: list[dict]) -> str:
    prompt = system_prompt or DEFAULT_AGENT_PROMPT

    messages = {
        "role": "system",
        "content": prompt
    }

    conversation.extend(messages)

    return await generate_response(messages)