"""Twilio webhook endpoints.

These endpoints are intentionally unauthenticated because Twilio signs its
requests with ``X-Twilio-Signature`` (verified with a fixed auth token).
CSRF is skipped because Twilio posts cross-site form data.

The conversation loop is TwiML/Gather based: Twilio collects the caller's
speech, posts it here, and we answer with TwiML that speaks the agent reply
and gathers the next utterance.
"""

import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ai.provider import LLMError
from conversations.models import ConversationStatus
from conversations.services import run_agent_turn

from .providers.twilio import (
    build_gather_twiml,
    build_hangup_twiml,
    validate_twilio_signature,
)
from .services import (
    apply_provider_status,
    create_inbound_call,
    get_conversation_by_provider_call_id,
    get_gather_webhook_url,
    resolve_phone_number,
)

logger = logging.getLogger(__name__)

GREETING = "Hello! Welcome to our business. How can I help you?"
REPEAT_PROMPT = "I didn't catch that. Could you say that again?"
ERROR_PROMPT = "I'm sorry, we're experiencing a technical problem. Please call again later."


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

            conversation = create_inbound_call(
                phone_number, from_number, provider_call_id
            )

        return _twiml_response(
            build_gather_twiml(GREETING, get_gather_webhook_url())
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

        if not reply:
            reply = REPEAT_PROMPT

        return _twiml_response(
            build_gather_twiml(reply, get_gather_webhook_url())
        )