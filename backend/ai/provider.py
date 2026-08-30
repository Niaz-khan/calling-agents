"""LLM provider abstraction.

The rest of the application only talks to ``generate_response``. Provider-
specific details live here so the orchestrator and tools stay provider-agnostic.
"""

from django.conf import settings


class LLMError(Exception):
    """Raised when the LLM provider is unavailable or a request fails."""


_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("The openai package is not installed") from exc

        if not settings.LLM_API_KEY:
            raise LLMError("LLM_API_KEY is not configured")

        kwargs = {"api_key": settings.LLM_API_KEY}
        if settings.LLM_BASE_URL:
            kwargs["base_url"] = settings.LLM_BASE_URL
        _client = OpenAI(**kwargs)
    return _client


def generate_response(messages, tools=None):
    """Return ``{"content": str, "tool_calls": [...]}`` from the LLM."""
    kwargs = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }

    if tools:
        kwargs["tools"] = tools

    try:
        response = _get_client().chat.completions.create(**kwargs)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc

    message = response.choices[0].message

    return {
        "content": message.content or "",
        "tool_calls": [
            {
                "id": tool_call.id,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in (message.tool_calls or [])
        ],
    }