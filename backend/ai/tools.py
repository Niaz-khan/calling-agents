"""AI tool registry.

Tools are the controlled bridge between LLM reasoning and real-world
actions. The LLM never executes code; it only requests a named tool with
JSON arguments, and this registry executes the approved, validated handler.
Unknown tools are rejected.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from agents.models import Agent
from appointments.services import check_availability, create_appointment
from conversations.models import Conversation, PhoneCallStatus
from crm.models import Customer
from knowledge.embeddings import EmbeddingError
from knowledge.services import search_knowledge_base as knowledge_search
from services.models import Service

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_services",
            "description": (
                "List the services the business currently offers, including name, "
                "description, duration in minutes, price and currency. Call this "
                "whenever the customer asks what services exist, how much a service "
                "costs, or how long an appointment lasts. The returned service id is "
                "required when checking availability or booking for a specific service. "
                "Never invent services, prices or durations yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_appointment_availability",
            "description": (
                "Check if a time slot is available for booking an appointment. When "
                "the customer has selected a service, pass its service_id and the "
                "tool derives the correct end time from the service duration; an "
                "LLM-supplied end time is ignored in that case."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g. 2026-08-28T15:00:00)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": (
                            "End time in ISO 8601 format. Optional when service_id is "
                            "provided (the service duration is used)."
                        ),
                    },
                    "service_id": {
                        "type": "integer",
                        "description": "Id of the selected service from list_services.",
                    },
                },
                "required": ["start_time"],
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
                        "description": (
                            "End time in ISO 8601 format. Optional when service_id is "
                            "provided (the service duration is used)."
                        ),
                    },
                    "service_id": {
                        "type": "integer",
                        "description": "Id of the selected service from list_services.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes for the appointment",
                    },
                },
                "required": ["customer_name", "customer_phone", "start_time"],
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


def _owned_service(organization, service_id):
    return Service.objects.filter(
        id=service_id, organization=organization, active=True
    ).first()


def list_services(organization):
    services = Service.objects.filter(organization=organization, active=True).order_by(
        "name"
    )
    return {
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "description": service.description or "",
                "duration_minutes": service.duration_minutes,
                "price": str(service.price) if service.price is not None else None,
                "currency": service.currency,
            }
            for service in services
        ]
    }


def check_appointment_availability(
    organization, agent_id, start_time, end_time=None, service_id=None
):
    if start_time is None:
        return {"error": "start_time is required"}

    if service_id is not None:
        service = _owned_service(organization, service_id)
        if service is None:
            return {"error": "The requested service does not exist"}
        end_time = start_time + timedelta(minutes=service.duration_minutes)
    elif end_time is None:
        return {"error": "end_time is required when no service is selected"}

    available = check_availability(organization, agent_id, start_time, end_time)
    return {
        "available": available,
        "requested_start": start_time.isoformat(),
        "requested_end": end_time.isoformat(),
        "service_id": service_id,
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
    service_id=None,
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
            service_id=service_id,
        )
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    return {
        "success": True,
        "appointment_id": appointment.id,
        "service_id": service_id,
        "service_name": appointment.service.name if appointment.service else None,
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
            if conversation.agent is not None and not conversation.agent.can_transfer:
                return {
                    "success": False,
                    "error": "Transfers are disabled for this agent",
                }
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
    if tool_name == "list_services":
        return list_services(organization)

    if tool_name == "check_appointment_availability":
        try:
            start_time = _parse_time(args["start_time"])
        except (KeyError, ValueError):
            return {"error": "Invalid start_time"}

        end_time = None
        raw_end = args.get("end_time")
        if raw_end:
            try:
                end_time = _parse_time(raw_end)
            except ValueError:
                return {"error": "Invalid end_time"}

        service_id = args.get("service_id")
        return check_appointment_availability(
            organization, agent_id, start_time, end_time, service_id
        )

    if tool_name == "book_appointment":
        try:
            start_time = _parse_time(args["start_time"])
        except (KeyError, ValueError):
            return {"error": "Invalid start_time"}

        service_id = args.get("service_id")
        service = None
        if service_id is not None:
            service = _owned_service(organization, service_id)
            if service is None:
                return {"error": "The requested service does not exist"}

        if service is not None:
            end_time = start_time + timedelta(minutes=service.duration_minutes)
        else:
            try:
                end_time = _parse_time(args["end_time"])
            except (KeyError, ValueError):
                return {"error": "Invalid end_time"}

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
            service_id=service_id,
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