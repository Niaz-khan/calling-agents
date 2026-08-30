"""Conversation turn orchestration for the text AI agent."""

import json

from apps.ai.agent import run_agent

from .call_intelligence import get_customer_memory
from .models import ConversationMessage


def build_conversation_history(conversation):
    """Rebuild the LLM message list from persisted conversation messages."""
    history = conversation.messages.all().order_by("created_at", "id")

    conversation_messages = []

    memory = get_customer_memory(conversation)
    if memory:
        conversation_messages.append(
            {
                "role": "system",
                "content": (
                    "Information about the customer, learned from previous calls:\n"
                    f"{memory}"
                ),
            }
        )

    for message in history:
        if message.role == ConversationMessage.Role.USER:
            conversation_messages.append(
                {"role": "user", "content": message.content}
            )

        elif message.role == ConversationMessage.Role.ASSISTANT:
            try:
                payload = json.loads(message.content)
            except (TypeError, json.JSONDecodeError):
                payload = None

            tool_calls = payload.get("tool_calls") if payload else None

            if tool_calls:
                conversation_messages.append(
                    {
                        "role": "assistant",
                        "content": (payload.get("content") or None)
                        if payload
                        else None,
                        "tool_calls": [
                            {**tc, "type": tc.get("type") or "function"}
                            for tc in tool_calls
                        ],
                    }
                )
            else:
                conversation_messages.append(
                    {"role": "assistant", "content": message.content}
                )

        elif message.role == ConversationMessage.Role.TOOL:
            conversation_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                }
            )

    return conversation_messages


def run_agent_turn(conversation, agent, user_text):
    """Persist a user message, run the AI agent, and persist its output."""
    ConversationMessage.objects.create(
        conversation=conversation,
        role=ConversationMessage.Role.USER,
        content=user_text,
    )

    history = build_conversation_history(conversation)
    result = run_agent(
        system_prompt=agent.system_prompt,
        conversation=history,
        organization=conversation.organization,
        agent_id=agent.id,
        call_id=conversation.id,
    )

    for message in result.messages:
        if message["role"] == "assistant":
            tool_info = {"tool_calls": message.get("tool_calls", [])}
            if message.get("content"):
                tool_info["content"] = message["content"]
            ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.Role.ASSISTANT,
                content=json.dumps(tool_info),
            )

        elif message["role"] == "tool":
            ConversationMessage.objects.create(
                conversation=conversation,
                role=ConversationMessage.Role.TOOL,
                content=message["content"],
                tool_call_id=message.get("tool_call_id"),
            )

    ConversationMessage.objects.create(
        conversation=conversation,
        role=ConversationMessage.Role.ASSISTANT,
        content=result.response,
    )

    return result