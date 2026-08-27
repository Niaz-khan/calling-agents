from openai import AsyncOpenAI

from app.config import settings

client_kwargs = {
    "api_key": settings.llm_api_key
}

if settings.llm_base_url:
    client_kwargs["base_url"] = settings.llm_base_url


client = AsyncOpenAI(**client_kwargs)

async def generate_response(message: list[dict]) -> str:
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=message,
        temperature=0.2
    )

    message = response.choices[0].message

    return message.content or ""

