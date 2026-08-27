import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.appointments import check_availability, create_appointment


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


def check_appointment_availability(
    db: Session,
    agent_id: int,
    start_time: datetime,
    end_time: datetime,
) -> dict:
    available = check_availability(
        db=db,
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "available": available,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }


def book_appointment(
    db: Session,
    agent_id: int,
    call_id: int | None,
    customer_name: str,
    customer_phone: str,
    start_time: datetime,
    end_time: datetime,
    notes: str | None = None,
) -> dict:
    try:
        appointment = create_appointment(
            db=db,
            agent_id=agent_id,
            call_id=call_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            start_time=start_time,
            end_time=end_time,
            notes=notes,
        )

        return {
            "success": True,
            "appointment_id": appointment.id,
            "start_time": appointment.start_time.isoformat(),
            "end_time": appointment.end_time.isoformat(),
            "customer_name": appointment.customer_name,
        }
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
        }


def execute_tool(
    db: Session,
    agent_id: int,
    call_id: int | None,
    tool_name: str,
    arguments: str,
) -> str:
    try:
        args = json.loads(arguments)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid tool arguments"})

    if tool_name == "check_appointment_availability":
        start_time = datetime.fromisoformat(args["start_time"])
        end_time = datetime.fromisoformat(args["end_time"])

        result = check_appointment_availability(
            db=db,
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
        )
        return json.dumps(result)

    elif tool_name == "book_appointment":
        start_time = datetime.fromisoformat(args["start_time"])
        end_time = datetime.fromisoformat(args["end_time"])

        result = book_appointment(
            db=db,
            agent_id=agent_id,
            call_id=call_id,
            customer_name=args["customer_name"],
            customer_phone=args["customer_phone"],
            start_time=start_time,
            end_time=end_time,
            notes=args.get("notes"),
        )
        return json.dumps(result)

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
