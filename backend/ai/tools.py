"""AI tool registry.

Tools are the controlled bridge between LLM reasoning and real-world
actions. The LLM never executes code; it only requests a named tool with
JSON arguments, and this registry executes the approved, validated handler.
Unknown tools are rejected.
"""

import json
from datetime import datetime, timezone

from agents.models import Agent
from appointments.services import check_availability, create_appointment

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


def _parse_time(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def execute_tool(organization, agent_id, call_id, tool_name, arguments):
    """Execute an approved tool and return a JSON-encoded result string."""
    if tool_name not in TOOLS:
        return json.dumps({"error": f"Tool not available: {tool_name}"})

    if _owned_agent(organization, agent_id) is None:
        return json.dumps({"error": "Agent not found"})

    try:
        args = json.loads(arguments)
    except (TypeError, json.JSONDecodeError):
        return json.dumps({"error": "Invalid tool arguments"})

    if not isinstance(args, dict):
        return json.dumps({"error": "Invalid tool arguments"})

    if tool_name == "check_appointment_availability":
        try:
            start_time = _parse_time(args["start_time"])
            end_time = _parse_time(args["end_time"])
        except (KeyError, ValueError):
            return json.dumps({"error": "Invalid start_time or end_time"})

        result = check_appointment_availability(
            organization, agent_id, start_time, end_time
        )
        return json.dumps(result)

    if tool_name == "book_appointment":
        try:
            start_time = _parse_time(args["start_time"])
            end_time = _parse_time(args["end_time"])
        except (KeyError, ValueError):
            return json.dumps({"error": "Invalid start_time or end_time"})

        customer_name = str(args.get("customer_name") or "").strip()
        customer_phone = str(args.get("customer_phone") or "").strip()
        if not customer_name or not customer_phone:
            return json.dumps(
                {"error": "customer_name and customer_phone are required"}
            )

        result = book_appointment(
            organization=organization,
            agent_id=agent_id,
            call_id=call_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            start_time=start_time,
            end_time=end_time,
            notes=args.get("notes"),
        )
        return json.dumps(result)

    return json.dumps({"error": f"Tool not available: {tool_name}"})