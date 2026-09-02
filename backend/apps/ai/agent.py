"""AI agent orchestrator.

Responsible for:
* calling the LLM with system prompt + conversation
* detecting tool calls
* executing approved tools through the registry
* feeding tool results back to the LLM
* producing a final response
"""

from dataclasses import dataclass, field

from .prompts import DEFAULT_AGENT_PROMPT
from .prompt_render import render_prompt
from .provider import generate_response
from .tools import TOOL_DEFINITIONS, execute_tool

MAX_TOOL_ROUNDS = 5


def _load_agent(agent_id):
    try:
        from apps.agents.models import Agent

        return Agent.objects.filter(id=agent_id).select_related("organization").first()
    except Exception:
        return None


@dataclass
class AgentResult:
    response: str
    messages: list[dict] = field(default_factory=list)


def run_agent(system_prompt, conversation, organization, agent_id, call_id=None):
    """Run the agent loop and return the final response plus new messages."""
    agent = _load_agent(agent_id)
    prompt = system_prompt or DEFAULT_AGENT_PROMPT
    if agent is not None:
        prompt = render_prompt(prompt, agent, organization)

    messages = [{"role": "system", "content": prompt}, *conversation]
    new_messages: list[dict] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = generate_response(messages, tools=TOOL_DEFINITIONS)

        tool_calls = response.get("tool_calls", [])

        if not tool_calls:
            return AgentResult(
                response=response["content"],
                messages=new_messages,
            )

        assistant_msg = {
            "role": "assistant",
            "content": response.get("content") or None,
            "tool_calls": tool_calls,
        }
        messages.append(assistant_msg)
        new_messages.append(assistant_msg)

        for tool_call in tool_calls:
            result = execute_tool(
                organization=organization,
                agent_id=agent_id,
                call_id=call_id,
                tool_name=tool_call["function"]["name"],
                arguments=tool_call["function"]["arguments"],
            )

            tool_msg = {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": result,
            }
            messages.append(tool_msg)
            new_messages.append(tool_msg)

    return AgentResult(
        response=(
            "I apologize, but I'm having trouble processing your request. "
            "Please try again."
        ),
        messages=new_messages,
    )