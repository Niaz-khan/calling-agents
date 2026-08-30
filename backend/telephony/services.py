"""Voice call service: phone number resolution and provider status handling.

Ported from the legacy FastAPI ``services/telephony.py``. Provider status is
normalized onto ``PhoneCall.provider_status``; ``Conversation`` mirrors the
lifecycle with an OPEN/CLOSED status so voice and text calls share one path.
"""

import asyncio
import logging

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

logger = logging.getLogger(__name__)

PROVIDER_STATUS_TO_CALL_STATUS = {
    "queued": PhoneCallStatus.RINGING,
    "ringing": PhoneCallStatus.RINGING,
    "in-progress": PhoneCallStatus.IN_PROGRESS,
    "in_progress": PhoneCallStatus.IN_PROGRESS,
    "answered": PhoneCallStatus.IN_PROGRESS,
    "completed": PhoneCallStatus.COMPLETED,
    "busy": PhoneCallStatus.FAILED,
    "no-answer": PhoneCallStatus.FAILED,
    "failed": PhoneCallStatus.FAILED,
    "canceled": PhoneCallStatus.FAILED,
    "missed": PhoneCallStatus.FAILED,
}


class ProviderCallError(Exception):
    """Raised when a telephony provider cannot place or control a call."""


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


def get_outbound_webhook_url() -> str:
    """Twilio TwiML endpoint that answers our own outbound call leg."""
    return _webhook_url("/telephony/webhook/outbound")


def get_status_webhook_url() -> str:
    return _webhook_url("/telephony/webhook/status")


def get_gather_webhook_url() -> str:
    return _webhook_url("/telephony/webhook/gather")


def place_outbound_call(
    organization,
    agent,
    phone_number: PhoneNumber,
    to_number: str,
    provider=None,
) -> Conversation:
    """Register an outbound call in the database and place it with the provider.

    The internal call is created first so a provider failure still leaves a
    traceable FAILED record; on success the provider call id is backfilled.
    """
    from .providers.factory import get_telephony_provider

    if not phone_number.outbound_enabled:
        raise ProviderCallError("Phone number does not allow outbound calls")

    if provider is None:
        try:
            provider = get_telephony_provider()
        except ValueError as exc:
            raise ProviderCallError(str(exc))

    with transaction.atomic():
        customer, _ = Customer.objects.get_or_create(
            organization=organization, phone_number=to_number
        )

        conversation = Conversation.objects.create(
            organization=organization,
            agent=agent,
            customer=customer,
            channel=ConversationChannel.PHONE,
            status=ConversationStatus.OPEN,
        )
        phone_call = PhoneCall.objects.create(
            conversation=conversation,
            phone_number=phone_number,
            direction=PhoneCallDirection.OUTBOUND,
            caller_number=to_number,
            provider_status=PhoneCallStatus.RINGING,
        )

    try:
        provider_call_id = asyncio.run(
            provider.create_call(
                from_number=phone_number.phone_number,
                to_number=to_number,
                webhook_url=get_outbound_webhook_url(),
                status_callback_url=get_status_webhook_url(),
            )
        )
    except Exception as exc:
        logger.exception("Outbound call to %s could not be placed", to_number)
        phone_call.provider_status = PhoneCallStatus.FAILED
        phone_call.save(update_fields=["provider_status"])
        conversation.close()
        conversation.save(update_fields=["status", "ended_at"])
        raise ProviderCallError("Provider could not place the outbound call") from exc

    phone_call.provider_call_id = provider_call_id
    phone_call.save(update_fields=["provider_call_id"])

    logger.info(
        "Outbound call placed: conversation %s from %s to %s (provider id %s)",
        conversation.id,
        phone_number.phone_number,
        to_number,
        provider_call_id,
    )

    return conversation


def telephony_connection_status() -> dict:
    """Report whether the configured provider's credentials are usable.

    ``configured`` reflects environment configuration; ``connected`` is only
    true when the provider API actually accepted the credentials. Never returns
    credential material.
    """
    from .providers.factory import get_telephony_provider

    state = {
        "provider": settings.TELEPHONY_PROVIDER,
        "configured": False,
        "connected": False,
        "error": None,
    }

    configured = {
        "twilio": bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN),
        "telnyx": bool(settings.TELNYX_API_KEY),
        "other": False,
    }.get(state["provider"], False)

    state["configured"] = configured

    if not configured:
        state["error"] = "Provider credentials are not configured"
        return state

    try:
        provider = get_telephony_provider()
        state["connected"] = asyncio.run(provider.verify_credentials())
        if not state["connected"]:
            state["error"] = "Provider rejected the credentials"
    except Exception as exc:
        logger.warning("Telephony connection check failed: %s", exc)
        state["error"] = str(exc)

    return state


def persist_recording_url(provider_call_id: str, recording_url: str) -> PhoneCall | None:
    """Persist a provider recording URL only when the agent opted into recording."""
    if not provider_call_id or not recording_url:
        return None

    phone_call = (
        PhoneCall.objects.filter(provider_call_id=provider_call_id)
        .select_related("conversation__agent")
        .first()
    )
    if phone_call is None:
        return None

    agent = phone_call.conversation.agent
    if agent is not None and not agent.recording_enabled:
        return phone_call

    phone_call.recording_url = recording_url
    phone_call.save(update_fields=["recording_url"])
    return phone_call


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
            logger.info(
                "Call %s answered (conversation %s)",
                provider_call_id,
                phone_call.conversation_id,
            )
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
        logger.info(
            "Call %s completed (conversation %s)",
            provider_call_id,
            conversation.id,
        )

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
        logger.info(
            "Call %s failed (conversation %s)",
            provider_call_id,
            phone_call.conversation_id,
        )

        conversation = phone_call.conversation
        if conversation.status != ConversationStatus.CLOSED:
            conversation.close()
            conversation.save(update_fields=["status", "ended_at"])

        return conversation

    return phone_call.conversation