"""Post-call intelligence: transcripts, summaries, and outcome classification.

Ported from the legacy FastAPI ``call_intelligence`` service. Deterministic
signals (appointment booked, call transferred) are authoritative; the LLM is
used only as a fallback summarizer and classifier.
"""

import json

from django.utils import timezone

from ai.provider import generate_response, LLMError
from appointments.models import Appointment

from .models import ConversationMessage, ConversationOutcome, PhoneCallStatus

_OUTCOME_OPTIONS = [
    ("appointment_booked", ConversationOutcome.APPOINTMENT_BOOKED),
    ("appointment_requested", ConversationOutcome.APPOINTMENT_REQUESTED),
    ("information_provided", ConversationOutcome.INFORMATION_PROVIDED),
    ("callback_requested", ConversationOutcome.CALLBACK_REQUESTED),
    ("transferred_to_human", ConversationOutcome.TRANSFERRED_TO_HUMAN),
    ("no_resolution", ConversationOutcome.NO_RESOLUTION),
    ("customer_hung_up", ConversationOutcome.CUSTOMER_HUNG_UP),
    ("unknown", ConversationOutcome.UNKNOWN),
]


def build_transcript(conversation):
    """Render the call as a readable Customer/Agent transcript.

    Tool interactions and system messages are excluded.
    """
    lines = []

    for message in conversation.messages.all().order_by("created_at", "id"):
        if message.role == ConversationMessage.Role.TOOL:
            continue

        if message.role == ConversationMessage.Role.ASSISTANT:
            try:
                payload = json.loads(message.content)
            except (TypeError, json.JSONDecodeError):
                payload = None

            if payload and "tool_calls" in payload:
                continue

        if message.role == ConversationMessage.Role.SYSTEM:
            continue

        label = (
            "Customer"
            if message.role == ConversationMessage.Role.USER
            else "Agent"
        )
        lines.append(f"{label}: {message.content}")

    return "\n".join(lines)


def generate_call_summary(conversation):
    transcript = build_transcript(conversation)

    messages = [
        {
            "role": "system",
            "content": (
                "You write concise call summaries for a business phone agent. "
                "Summarize what the customer wanted and the outcome of the call "
                "in 2-3 sentences."
            ),
        },
        {"role": "user", "content": f"Summarize this call:\n\n{transcript}"},
    ]

    return generate_response(messages)["content"].strip()


def classify_call_outcome(conversation):
    """Classify the outcome of a call.

    Transferred calls and booked appointments are decided deterministically.
    Everything else is delegated to the LLM, falling back to ``UNKNOWN``.
    """
    phone_call = getattr(conversation, "phone_call", None)
    if (
        phone_call is not None
        and phone_call.provider_status == PhoneCallStatus.TRANSFERRED
    ):
        return ConversationOutcome.TRANSFERRED_TO_HUMAN

    if Appointment.objects.filter(conversation=conversation).exists():
        return ConversationOutcome.APPOINTMENT_BOOKED

    transcript = build_transcript(conversation)

    if not transcript.strip():
        return ConversationOutcome.UNKNOWN

    options = ", ".join(label for label, _ in _OUTCOME_OPTIONS)

    messages = [
        {
            "role": "system",
            "content": (
                "You classify the outcome of a business phone call. "
                f"Reply with exactly one of these values: {options}. "
                "No other text."
            ),
        },
        {"role": "user", "content": f"Classify this call:\n\n{transcript}"},
    ]

    try:
        response = generate_response(messages)
        label = response["content"].strip().lower()

        for option, outcome in _OUTCOME_OPTIONS:
            if option in label:
                return outcome
    except LLMError:
        return ConversationOutcome.UNKNOWN

    return ConversationOutcome.UNKNOWN


def get_customer_memory(conversation):
    if conversation.customer is None:
        return None

    memory = conversation.customer.memory or ""
    if not memory.strip():
        return None

    return memory


def finalize_call(conversation):
    """Write the summary, outcome, and customer memory for a finished call."""
    conversation.summary = generate_call_summary(conversation)
    conversation.outcome = classify_call_outcome(conversation)

    if conversation.customer is not None:
        entry = (
            f"[{timezone.now().isoformat(timespec='minutes')}] "
            f"{conversation.summary}"
        )
        customer = conversation.customer
        customer.memory = "\n".join(filter(None, [customer.memory, entry]))
        customer.save(update_fields=["memory"])

    conversation.save(update_fields=["summary", "outcome"])
    return conversation