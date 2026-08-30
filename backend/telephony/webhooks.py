"""Telephony webhook endpoints.

These endpoints are intentionally unauthenticated because Twilio signs its
requests with ``X-Twilio-Signature`` (verified with a fixed auth token) and
Telnyx signs its deliveries with an Ed25519 ``{timestamp}|{raw_body}``
signature. CSRF is skipped because providers post cross-site form data.

The Twilio conversation loop is TwiML/Gather based: Twilio collects the
caller's speech, posts it here, and we answer with TwiML that speaks the
agent reply and gathers the next utterance. Ownership is never taken from
request fields -- the dialed number is resolved against registered phone
numbers in the database.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from agents.models import Agent
from ai.provider import LLMError
from conversations.models import ConversationStatus, PhoneCallStatus
from conversations.services import run_agent_turn
from tenancy.services import is_business_open

from .providers.telnyx import (
    validate_telnyx_signature,
    telnyx_event_to_status,
)
from .providers.twilio import (
    build_dial_twiml,
    build_gather_twiml,
    build_hangup_twiml,
    build_say_twiml,
    validate_twilio_signature,
)
from .services import (
    apply_provider_status,
    create_inbound_call,
    get_conversation_by_provider_call_id,
    get_gather_webhook_url,
    persist_recording_url,
    resolve_phone_number,
)

logger = logging.getLogger(__name__)

GREETING = "Hello! Welcome to our business. How can I help you?"
REPEAT_PROMPT = "I didn't catch that. Could you say that again?"
ERROR_PROMPT = "I'm sorry, we're experiencing a technical problem. Please call again later."
AFTER_HOURS_NOTICE = (
    "We're currently closed. Please call back during our business hours."
)


def _verified(request, params) -> bool:
    signature = request.headers.get("X-Twilio-Signature", "")
    return validate_twilio_signature(
        request.build_absolute_uri(),
        params,
        signature or None,
        settings.TWILIO_AUTH_TOKEN,
    )


def _twiml_response(xml: str) -> HttpResponse:
    return HttpResponse(xml, content_type="application/xml")


def _greeting_for(agent: Agent) -> str:
    return (agent.voice_greeting or "").strip() or GREETING


def _after_hours_message_for(agent: Agent) -> str:
    greeting = (agent.voice_greeting or "").strip() or ""
    prefix = f"{greeting} " if greeting else ""
    return f"{prefix}{AFTER_HOURS_NOTICE}"


def _business_accepts(phone_number) -> bool:
    """Whether an inbound call should engage the agent right now.

    The agent's ``after_hours_behavior`` decides: ``continue`` always answers,
    ``message`` (the default) plays a courtesy message and ends the call when
    the business is closed.
    """
    agent = phone_number.agent
    if agent is None:
        return True
    if agent.after_hours_behavior == Agent.AfterHoursBehavior.CONTINUE:
        return True
    return is_business_open(phone_number.organization)


def _max_duration_exceeded(conversation, agent: Agent) -> bool:
    minutes = agent.max_call_duration_minutes
    if minutes is None:
        return False
    return timezone.now() - conversation.started_at > timedelta(minutes=minutes)


@method_decorator(csrf_exempt, name="dispatch")
class TwilioInboundWebhookView(View):
    """Twilio voice webhook: called when one of our numbers gets a call."""

    def post(self, request, *args, **kwargs):
        params = {k: v for k, v in request.POST.items()}

        if not _verified(request, params):
            return HttpResponse(status=403)

        provider_call_id = params.get("CallSid", "")
        to_number = params.get("To", "")
        from_number = params.get("From", "")

        conversation = get_conversation_by_provider_call_id(provider_call_id)

        if conversation is None:
            phone_number = resolve_phone_number(to_number)

            if phone_number is None:
                logger.warning("Inbound call to unregistered number: %s", to_number)
                return _twiml_response(build_hangup_twiml())

            if not _business_accepts(phone_number):
                conversation = create_inbound_call(
                    phone_number, from_number, provider_call_id
                )
                logger.info(
                    "Inbound call %s declined: business closed (conversation %s)",
                    provider_call_id,
                    conversation.id,
                )
                return _twiml_response(
                    build_say_twiml(_after_hours_message_for(phone_number.agent))
                )

            conversation = create_inbound_call(
                phone_number, from_number, provider_call_id
            )

        logger.info(
            "Inbound call %s from %s to %s (conversation %s)",
            provider_call_id,
            from_number,
            to_number,
            conversation.id,
        )

        return _twiml_response(
            build_gather_twiml(
                _greeting_for(conversation.agent), get_gather_webhook_url()
            )
        )


@method_decorator(csrf_exempt, name="dispatch")
class TwilioStatusWebhookView(View):
    """Twilio status callback: normalizes call lifecycle events."""

    def post(self, request, *args, **kwargs):
        params = {k: v for k, v in request.POST.items()}

        if not _verified(request, params):
            return HttpResponse(status=403)

        provider_call_id = params.get("CallSid", "")
        provider_status = params.get("CallStatus", "")

        recording_url = params.get("RecordingUrl") or ""
        if recording_url:
            persist_recording_url(provider_call_id, recording_url)

        conversation = apply_provider_status(provider_call_id, provider_status)
        if conversation is not None and provider_status.lower() in (
            "completed",
            "busy",
            "no-answer",
            "failed",
            "canceled",
            "missed",
        ):
            logger.info(
                "Call %s ended for conversation %s (%s)",
                provider_call_id,
                conversation.id,
                provider_status,
            )

        return JsonResponse({"ok": True})


@method_decorator(csrf_exempt, name="dispatch")
class TwilioGatherWebhookView(View):
    """Twilio speech gather callback: one caller utterance per POST."""

    def post(self, request, *args, **kwargs):
        params = {k: v for k, v in request.POST.items()}

        if not _verified(request, params):
            return HttpResponse(status=403)

        provider_call_id = params.get("CallSid", "")
        conversation = get_conversation_by_provider_call_id(provider_call_id)

        if conversation is None:
            return _twiml_response(build_hangup_twiml())

        if conversation.status != ConversationStatus.OPEN:
            return _twiml_response(build_hangup_twiml())

        if _max_duration_exceeded(conversation, conversation.agent):
            conversation.close()
            conversation.save(update_fields=["status", "ended_at"])
            logger.info("Call %s ended: max duration reached", provider_call_id)
            return _twiml_response(build_hangup_twiml())

        speech_result = (params.get("SpeechResult") or params.get("Digits") or "").strip()

        if not speech_result:
            return _twiml_response(
                build_gather_twiml(REPEAT_PROMPT, get_gather_webhook_url())
            )

        try:
            result = run_agent_turn(conversation, conversation.agent, speech_result)
            reply = (result.response or "").strip()
        except LLMError:
            logger.exception("Agent turn failed for conversation %s", conversation.id)
            reply = ERROR_PROMPT
        except Exception:
            logger.exception("Unexpected agent turn failure for conversation %s", conversation.id)
            reply = ERROR_PROMPT

        if not reply:
            reply = REPEAT_PROMPT

        conversation.refresh_from_db(fields=["status"])

        if conversation.phone_call.provider_status == PhoneCallStatus.TRANSFERRED:
            target = (conversation.organization.transfer_phone_number or "").strip()
            if target:
                logger.info(
                    "Transferring conversation %s to %s", conversation.id, target
                )
                return _twiml_response(build_dial_twiml(target))
            logger.info(
                "Conversation %s transferred with no destination; ending call",
                conversation.id,
            )
            return _twiml_response(build_hangup_twiml())

        return _twiml_response(
            build_gather_twiml(reply, get_gather_webhook_url())
        )


@method_decorator(csrf_exempt, name="dispatch")
class TwilioOutboundWebhookView(View):
    """Twilio webhook that answers our own outbound call leg.

    Unlike the inbound webhook this never creates a call -- the conversation is
    registered before the provider dials, so we resolve purely by CallSid.
    """

    def post(self, request, *args, **kwargs):
        params = {k: v for k, v in request.POST.items()}

        if not _verified(request, params):
            return HttpResponse(status=403)

        provider_call_id = params.get("CallSid", "")
        conversation = get_conversation_by_provider_call_id(provider_call_id)

        if conversation is None or conversation.status != ConversationStatus.OPEN:
            return _twiml_response(build_hangup_twiml())

        logger.info("Outbound call %s answered (conversation %s)", provider_call_id, conversation.id)

        return _twiml_response(
            build_gather_twiml(
                _greeting_for(conversation.agent), get_gather_webhook_url()
            )
        )


@method_decorator(csrf_exempt, name="dispatch")
class TelnyxInboundWebhookView(View):
    """Telnyx connection webhook: normalized call lifecycle events.

    Telnyx delivers JSON events to the webhook URL configured on its Voice API
    Application. Each delivery is Ed25519-signed over its exact raw body plus a
    timestamp header (with replay tolerance), and identity is resolved from the
    dialed number in the database -- never from request fields.
    """

    def post(self, request, *args, **kwargs):
        raw_body = request.body

        if not validate_telnyx_signature(
            raw_body,
            _header(request, "TELNYX-SIGNATURE"),
            _header(request, "TELNYX-TIMESTAMP"),
            settings.TELNYX_PUBLIC_KEY,
        ):
            logger.warning("Telnyx webhook rejected: invalid signature")
            return HttpResponse(status=403)

        event = _telnyx_event(request, raw_body)

        if event is None:
            return JsonResponse({"ok": True})

        event_type, payload, control_id = event

        if not control_id:
            return JsonResponse({"ok": True})

        status = telnyx_event_to_status(event_type)

        if status:
            apply_provider_status(control_id, status)

        if event_type == "call.initiated" and _is_inbound(payload):
            phone_number = resolve_phone_number(payload.get("to") or "")

            if phone_number is None:
                logger.warning("Telnyx inbound call to unregistered number: %s", payload.get("to"))
                return JsonResponse({"ok": True})

            conversation = (
                get_conversation_by_provider_call_id(control_id)
                or create_inbound_call(phone_number, payload.get("from") or "", control_id)
            )

            if _business_accepts(phone_number) is False:
                logger.info(
                    "Telnyx inbound call %s declined: business closed",
                    control_id,
                )

            try:
                _answer_telnyx(control_id)
            except Exception:
                logger.exception("Telnyx answer command failed for %s", control_id)

            logger.info(
                "Telnyx inbound call %s from %s (conversation %s)",
                control_id,
                payload.get("from"),
                conversation.id,
            )

        return JsonResponse({"ok": True})


def _header(request, name: str) -> str | None:
    value = request.headers.get(name)
    if value:
        return value
    return request.headers.get(name.lower())


def _telnyx_event(request, raw_body):
    import json

    try:
        data = json.loads(raw_body or b"{}")
    except (ValueError, TypeError):
        return None

    event_data = (data or {}).get("data") or {}
    event_type = event_data.get("event_type")
    payload = event_data.get("payload") or {}
    control_id = payload.get("call_control_id") or event_data.get("id")

    if not event_type:
        return None

    return event_type, payload, control_id


def _is_inbound(payload: dict) -> bool:
    return (payload.get("direction") or "").lower() == "inbound"


def _answer_telnyx(control_id: str):
    from .providers.factory import get_telephony_provider

    provider = get_telephony_provider()
    try:
        import asyncio

        asyncio.run(provider.answer_call(control_id))
    except AttributeError:
        logger.debug("Current provider does not support answering; skipping")