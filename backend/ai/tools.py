"""AI tool registry.

Tools are the controlled bridge between LLM reasoning and real-world
actions. The LLM never executes code; it only requests a named tool with
JSON arguments, and this registry executes the approved, validated handler.
Unknown tools are rejected.
"""

import json
import logging
from datetime import datetime, timezone

from agents.models import Agent
from appointments.services import check_availability, create_appointment
from conversations.models import Conversation, PhoneCallStatus
from crm.models import Customer
from knowledge.embeddings import EmbeddingError
from knowledge.services import search_knowledge_base as knowledge_search

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_appointment_availability",
            "description": "Check if a time slot is available for booking an appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g. 2026-08-28T15:00:00)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format (e.g. 2026-08-28T15:30:00)",
                    },
                },
                "required": ["start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for a customer at an available time slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Full name of the customer",
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "Phone number of the customer",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g. 2026-08-28T15:00:00)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format (e.g. 2026-08-28T15:30:00)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes for the appointment",
                    },
                },
                "required": ["customer_name", "customer_phone", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_customer",
            "description": "Look up a customer by their phone number to retrieve their information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "Phone number to look up",
                    },
                },
                "required": ["phone_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the business knowledge base for facts such as services, "
                "pricing, opening hours, policies, addresses, FAQs, or any other "
                "business-specific information. Use this tool whenever the customer "
                "asks a question whose answer depends on business information that "
                "you cannot know for certain. Returns the most relevant passages "
                "from business documents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A concise search query summarizing the business information the customer asked for",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Transfer the call to a human agent when the customer requests it or the situation requires it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Reason for the transfer",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]

TOOLS = {
    definition["function"]["name"]: definition
    for definition in TOOL_DEFINITIONS
}


def _owned_agent(organization, agent_id):
    return Agent.objects.filter(id=agent_id, organization=organization).first()


def check_appointment_availability(organization, agent_id, start_time, end_time):
    available = check_availability(organization, agent_id, start_time, end_time)
    return {
        "available": available,
        "requested_start": start_time.isoformat(),
        "requested_end": end_time.isoformat(),
    }


def book_appointment(
    organization,
    agent_id,
    call_id,
    customer_name,
    customer_phone,
    start_time,
    end_time,
    notes=None,
):
    try:
        appointment = create_appointment(
            organization=organization,
            agent_id=agent_id,
            call_id=call_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
        )
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success": True,
        "appointment_id": appointment.id,
        "requested_start": appointment.start_time.isoformat(),
        "requested_end": appointment.end_time.isoformat(),
        "customer_name": appointment.customer_name,
    }


def lookup_customer(organization, phone_number):
    customer = Customer.objects.filter(
        organization=organization, phone_number=phone_number
    ).first()

    if customer is None:
        return {"found": False, "phone_number": phone_number}

    return {
        "found": True,
        "customer_id": customer.id,
        "name": customer.name,
        "phone_number": customer.phone_number,
        "email": customer.email,
        "notes": customer.notes,
    }


def search_knowledge_base(organization, agent_id, query):
    try:
        result = knowledge_search(
            organization=organization, agent_id=agent_id, query=query
        )
    except EmbeddingError as exc:
        return {"found": False, "query": query, "message": str(exc)}

    if result.get("found"):
        return result
    if result.get("message"):
        return result

    return {
        "found": False,
        "query": query,
        "message": (
            "No relevant business information was found in the knowledge base. "
            "Do not guess or invent this information. If the customer needs it, "
            "apologize and offer to help with something else or transfer to a human."
        ),
    }


def transfer_to_human(organization, call_id, reason):
    if call_id is not None:
        conversation = Conversation.objects.filter(
            organization=organization, id=call_id
        ).first()
        if conversation is not None:
            conversation.close()
            conversation.save(update_fields=["status", "ended_at"])
            phone_call = getattr(conversation, "phone_call", None)
            if phone_call is not None:
                phone_call.provider_status = PhoneCallStatus.TRANSFERRED
                phone_call.save(update_fields=["provider_status"])

    return {
        "success": True,
        "message": "Transferring you to a human agent.",
        "reason": reason,
    }


def _parse_time(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def execute_tool(organization, agent_id, call_id, tool_name, arguments):
    """Execute an approved tool and return a JSON-encoded result string."""
    if tool_name not in TOOLS:
        logger.warning("AI requested unknown tool: %s", tool_name)
        return json.dumps({"error": f"Tool not available: {tool_name}"})

    if _owned_agent(organization, agent_id) is None:
        logger.warning("AI tool '%s' rejected: agent %s not in org", tool_name, agent_id)
        return json.dumps({"error": "Agent not found"})

    try:
        args = json.loads(arguments)
    except (TypeError, json.JSONDecodeError):
        logger.warning("AI tool '%s' rejected: invalid JSON arguments", tool_name)
        return json.dumps({"error": "Invalid tool arguments"})

    if not isinstance(args, dict):
        return json.dumps({"error": "Invalid tool arguments"})

    logger.info("AI tool called: %s", tool_name)

    try:
        result = _dispatch(organization, agent_id, call_id, tool_name, args)
    except Exception as exc:
        logger.exception("AI tool '%s' failed", tool_name)
        return json.dumps({"error": f"Tool execution failed: {exc}"})
    return json.dumps(result)


def _dispatch(organization, agent_id, call_id, tool_name, args):
    if tool_name == "check_appointment_availability":
        try:
            start_time = _parse_time(args["start_time"])
            end_time = _parse_time(args["end_time"])
        except (KeyError, ValueError):
            return {"error": "Invalid start_time or end_time"}

        return check_appointment_availability(
            organization, agent_id, start_time, end_time
        )

    if tool_name == "book_appointment":
        try:
            start_time = _parse_time(args["start_time"])
            end_time = _parse_time(args["end_time"])
        except (KeyError, ValueError):
            return {"error": "Invalid start_time or end_time"}

        customer_name = str(args.get("customer_name") or "").strip()
        customer_phone = str(args.get("customer_phone") or "").strip()
        if not customer_name or not customer_phone:
            return {"error": "customer_name and customer_phone are required"}

        return book_appointment(
            organization=organization,
            agent_id=agent_id,
            call_id=call_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            start_time=start_time,
            end_time=end_time,
            notes=args.get("notes"),
        )

    if tool_name == "lookup_customer":
        phone_number = str(args.get("phone_number") or "").strip()
        if not phone_number:
            return {"error": "phone_number is required"}
        return lookup_customer(organization, phone_number)

    if tool_name == "search_knowledge_base":
        query = str(args.get("query") or "").strip()
        if not query:
            return {"error": "Search query is required."}
        return search_knowledge_base(organization, agent_id, query)

    if tool_name == "transfer_to_human":
        reason = str(args.get("reason") or "").strip()
        if not reason:
            return {"error": "reason is required"}
        return transfer_to_human(organization, call_id, reason)

    return {"error": f"Tool not available: {tool_name}"}