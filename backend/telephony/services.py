"""Voice call service: phone number resolution and provider status handling.

Ported from the legacy FastAPI ``services/telephony.py``. Provider status is
normalized onto ``PhoneCall.provider_status``; ``Conversation`` mirrors the
lifecycle with an OPEN/CLOSED status so voice and text calls share one path.
"""

from django.conf import settings
from django.db import transaction

from ai.provider import LLMError
from conversations.call_intelligence import finalize_call
from conversations.models import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
    PhoneCall,
    PhoneCallDirection,
    PhoneCallStatus,
)
from crm.models import Customer

from .models import PhoneNumber

PROVIDER_STATUS_TO_CALL_STATUS = {
    "queued": PhoneCallStatus.RINGING,
    "ringing": PhoneCallStatus.RINGING,
    "in-progress": PhoneCallStatus.IN_PROGRESS,
    "in_progress": PhoneCallStatus.IN_PROGRESS,
    "completed": PhoneCallStatus.COMPLETED,
    "busy": PhoneCallStatus.FAILED,
    "no-answer": PhoneCallStatus.FAILED,
    "failed": PhoneCallStatus.FAILED,
    "canceled": PhoneCallStatus.FAILED,
    "missed": PhoneCallStatus.FAILED,
}


def resolve_phone_number(phone_number: str) -> PhoneNumber | None:
    """Find the active registered number that was dialed."""
    return (
        PhoneNumber.objects.filter(phone_number=phone_number, is_active=True)
        .select_related("agent", "organization")
        .first()
    )


def create_inbound_call(
    phone_number: PhoneNumber,
    from_number: str,
    provider_call_id: str | None = None,
) -> Conversation:
    """Create a phone Conversation + PhoneCall for an inbound call."""
    if phone_number.agent is None:
        raise ValueError("Phone number has no agent")

    with transaction.atomic():
        customer, _ = Customer.objects.get_or_create(
            organization=phone_number.organization,
            phone_number=from_number,
        )

        conversation = Conversation.objects.create(
            organization=phone_number.organization,
            agent=phone_number.agent,
            customer=customer,
            channel=ConversationChannel.PHONE,
            status=ConversationStatus.OPEN,
        )
        PhoneCall.objects.create(
            conversation=conversation,
            phone_number=phone_number,
            direction=PhoneCallDirection.INBOUND,
            caller_number=from_number,
            provider_call_id=provider_call_id,
            provider_status=PhoneCallStatus.RINGING,
        )

    return conversation


def get_conversation_by_provider_call_id(
    provider_call_id: str,
) -> Conversation | None:
    if not provider_call_id:
        return None

    phone_call = (
        PhoneCall.objects.filter(provider_call_id=provider_call_id)
        .select_related("conversation")
        .first()
    )

    if phone_call is None:
        return None

    return phone_call.conversation


def _webhook_url(path: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}{path}"


def get_inbound_webhook_url() -> str:
    return _webhook_url("/telephony/webhook/inbound")


def get_status_webhook_url() -> str:
    return _webhook_url("/telephony/webhook/status")


def get_gather_webhook_url() -> str:
    return _webhook_url("/telephony/webhook/gather")


def apply_provider_status(
    provider_call_id: str,
    provider_status: str,
) -> Conversation | None:
    """Normalize a provider status callback onto the conversation lifecycle."""
    if not provider_call_id:
        return None

    phone_call = (
        PhoneCall.objects.filter(provider_call_id=provider_call_id)
        .select_related("conversation")
        .first()
    )

    if phone_call is None:
        return None

    status = PROVIDER_STATUS_TO_CALL_STATUS.get(provider_status.lower().strip())

    if status is None:
        return phone_call.conversation

    if status == PhoneCallStatus.IN_PROGRESS:
        if phone_call.provider_status != status:
            phone_call.provider_status = status
            phone_call.save(update_fields=["provider_status"])
        return phone_call.conversation

    if status == PhoneCallStatus.COMPLETED:
        conversation = phone_call.conversation

        if (
            phone_call.provider_status == PhoneCallStatus.COMPLETED
            and conversation.summary
        ):
            return conversation

        phone_call.provider_status = status
        phone_call.save(update_fields=["provider_status"])

        if conversation.status != ConversationStatus.CLOSED:
            conversation.close()
            conversation.save(update_fields=["status", "ended_at"])

            try:
                finalize_call(conversation)
            except LLMError:
                conversation.refresh_from_db(fields=["summary", "outcome"])

        return conversation

    if status == PhoneCallStatus.FAILED:
        if phone_call.provider_status == PhoneCallStatus.COMPLETED:
            return phone_call.conversation

        phone_call.provider_status = status
        phone_call.save(update_fields=["provider_status"])

        conversation = phone_call.conversation
        if conversation.status != ConversationStatus.CLOSED:
            conversation.close()
            conversation.save(update_fields=["status", "ended_at"])

        return conversation

    return phone_call.conversation