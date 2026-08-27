from openai import AsyncOpenAI

from app.config import settings

client_kwargs = {
    "api_key": settings.llm_api_key
}

if settings.llm_base_url:
    client_kwargs["base_url"] = settings.llm_base_url


client = AsyncOpenAI(**client_kwargs)


async def generate_response(
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    kwargs = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.2,
    }

    if tools:
        kwargs["tools"] = tools

    response = await client.chat.completions.create(**kwargs)

    message = response.choices[0].message

    return {
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in (message.tool_calls or [])
        ],
    }
