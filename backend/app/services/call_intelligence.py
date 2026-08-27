import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.provider import generate_response
from app.models.appointment import Appointment
from app.models.call import Call, CallOutcome, CallStatus
from app.models.call_message import CallMessage, MessageRole
from app.models.customer import Customer


def build_transcript(db: Session, call: Call) -> str:
    statement = (
        select(CallMessage)
        .where(CallMessage.call_id == call.id)
        .order_by(CallMessage.created_at.asc(), CallMessage.id.asc())
    )

    messages = db.scalars(statement).all()

    lines: list[str] = []

    for message in messages:
        role = message.role.value

        if message.role == MessageRole.TOOL:
            continue

        if message.role == MessageRole.ASSISTANT and message.tool_call_id is None:
            try:
                payload = json.loads(message.content)
            except json.JSONDecodeError:
                payload = None

            if payload and "tool_calls" in payload:
                continue

        label = "Customer" if role == "user" else "Agent"
        lines.append(f"{label}: {message.content}")

    return "\n".join(lines)


async def generate_call_summary(db: Session, call: Call) -> str:
    transcript = build_transcript(db, call)

    messages = [
        {
            "role": "system",
            "content": (
                "You write concise call summaries for a business phone agent. "
                "Summarize what the customer wanted and the outcome of the call "
                "in 2-3 sentences."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this call:\n\n{transcript}",
        },
    ]

    response = await generate_response(messages)

    return response["content"].strip()


async def classify_call_outcome(db: Session, call: Call) -> CallOutcome:
    if call.status == CallStatus.TRANSFERRED:
        return CallOutcome.TRANSFERRED_TO_HUMAN

    appointment_statement = select(Appointment).where(
        Appointment.call_id == call.id
    )
    appointment = db.scalar(appointment_statement)

    if appointment is not None:
        return CallOutcome.APPOINTMENT_BOOKED

    transcript = build_transcript(db, call)

    if not transcript.strip():
        return CallOutcome.UNKNOWN

    options = [
        "appointment_booked",
        "appointment_requested",
        "information_provided",
        "callback_requested",
        "transferred_to_human",
        "no_resolution",
        "customer_hung_up",
        "unknown",
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You classify the outcome of a business phone call. "
                f"Reply with exactly one of these values: {', '.join(options)}. "
                "No other text."
            ),
        },
        {
            "role": "user",
            "content": f"Classify this call:\n\n{transcript}",
        },
    ]

    try:
        response = await generate_response(messages)
        label = response["content"].strip().lower()

        for option in options:
            if option in label:
                return CallOutcome(option)
    except Exception:
        return CallOutcome.UNKNOWN

    return CallOutcome.UNKNOWN


def get_customer_memory(db: Session, call: Call) -> str | None:
    if not call.customer_id:
        return None

    customer = db.get(Customer, call.customer_id)

    if customer is None:
        return None

    return customer.memory


async def finalize_call(db: Session, call: Call) -> Call:
    call.summary = await generate_call_summary(db, call)
    call.outcome = await classify_call_outcome(db, call)

    if call.customer_id:
        customer = db.get(Customer, call.customer_id)
        if customer is not None:
            entry = (
                f"[{datetime.now(timezone.utc).isoformat(timespec='minutes')}] "
                f"{call.summary}"
            )
            customer.memory = "\n".join(filter(None, [customer.memory, entry]))

    db.commit()
    db.refresh(call)

    return call