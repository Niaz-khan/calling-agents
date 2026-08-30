"""Public, unauthenticated endpoints for web/API agent deployments.

Visitors never hold an organization JWT. Identity is a client-generated
``X-Visitor-ID`` header; conversation state is keyed by (deployment,
visitor_id) so a returning visitor continues the same open conversation.

Domain policy:
* ``allowed_domains == []``  -> any Origin/Referer accepted.
* ``allowed_domains`` set   -> only those exact hosts are accepted, but only
  for browser (Origin-carrying) requests. API and non-browser callers bypass
  the check so curl/testing still work.
"""

import json
import time

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from ai.provider import LLMError
from conversations.models import (
    Conversation,
    ConversationChannel,
    ConversationStatus,
)
from conversations.services import run_agent_turn

from .models import AgentDeployment
from .widget_assets import WIDGET_HTML, WIDGET_JS

_PUBLIC_CHANNELS = {ConversationChannel.WEBSITE, ConversationChannel.API}

DEFAULT_WIDGET_COLOR = "#4f46e5"
MAX_MESSAGE_CHARS = 2000
THROTTLE_WINDOW_SECONDS = 60
THROTTLE_LIMIT_PER_WINDOW = 60


def _origin_host(request):
    """Exact Origin/Referer host without scheme/path, or ``None``."""
    for header in ("Origin", "Referer"):
        value = request.headers.get(header)
        if value:
            host = value.split("://", 1)[-1].split("/", 1)[0].lower()
            if host:
                return host
    return None


def _domain_allowed(allowed_domains, host) -> bool:
    if not allowed_domains:
        return True
    return host in [domain.lower() for domain in allowed_domains]


def _display_content(role, content):
    """Extract the user-visible text from a persisted agent message."""
    if role != "assistant":
        return content
    try:
        payload = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return content
    if isinstance(payload, dict) and payload.get("content"):
        return payload["content"]
    return None


def _throttle_status(request, visitor_id) -> int:
    """Return how many seconds until the visitor is allowed again (0 = allowed).

    In-process fixed-window counter keyed by (remote IP, visitor id). Intended
    as a lightweight abuse brake; Redis can replace it later without touching
    views. ``X-Forwarded-For`` is intentionally ignored — it is client-supplied
    and would make the scheme trivial to spoof.
    """
    ip = request.META.get("REMOTE_ADDR") or "unknown"
    fingerprint = f"{ip}|{visitor_id or ''}"
    now = int(time.time())
    bucket = now // THROTTLE_WINDOW_SECONDS
    cache_key = f"pubchat:{fingerprint}:{bucket}"
    count = cache.get(cache_key, 0)
    if count >= THROTTLE_LIMIT_PER_WINDOW:
        retry = (bucket + 1) * THROTTLE_WINDOW_SECONDS - now
        return max(retry, 1)
    cache.set(cache_key, count + 1, timeout=THROTTLE_WINDOW_SECONDS * 2)
    return 0


class PublicChatView(APIView):
    """No-JWT chat for a public deployment; visitor keyed by X-Visitor-ID."""

    permission_classes = [AllowAny]

    def _cors_headers(self, request, deployment):
        origin = request.headers.get("Origin")
        host = _origin_host(request)
        headers = {}
        if not origin or host is None or deployment is None:
            return headers
        if deployment.channel != ConversationChannel.WEBSITE:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
            return headers
        if _domain_allowed(deployment.allowed_domains, host):
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
        return headers

    def _resolve(self, identifier):
        return AgentDeployment.objects.resolve_public(identifier)

    def _config_error(self, request, deployment, payload, status_code):
        return JsonResponse(
            payload, status=status_code, headers=self._cors_headers(request, deployment)
        )

    def _visitor_id(self, request):
        visitor_id = request.headers.get("X-Visitor-ID")
        if visitor_id and len(visitor_id) <= 128:
            return visitor_id
        return None

    def options(self, request, identifier):
        deployment = self._resolve(identifier)
        if deployment is None or deployment.channel not in _PUBLIC_CHANNELS:
            return self._config_error(
                request, deployment, {"detail": "Deployment not found"}, 404
            )
        headers = self._cors_headers(request, deployment)
        if request.headers.get("Origin") and "Access-Control-Allow-Origin" not in headers:
            return JsonResponse(
                {"detail": "Origin not allowed"}, status=403, headers=headers
            )
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type, X-Visitor-ID"
        return HttpResponse(status=200, headers=headers)

    def get(self, request, identifier):
        """Return the open conversation's transcript for a visitor."""
        deployment = self._resolve(identifier)
        if deployment is None or deployment.channel not in _PUBLIC_CHANNELS:
            return self._config_error(
                request, deployment, {"detail": "Deployment not found"}, 404
            )
        headers = self._cors_headers(request, deployment)
        if request.headers.get("Origin") and "Access-Control-Allow-Origin" not in headers:
            return JsonResponse(
                {"detail": "Origin not allowed"}, status=403, headers=headers
            )

        visitor_id = self._visitor_id(request)
        if visitor_id is None:
            return JsonResponse(
                {"detail": "X-Visitor-ID header is required"}, status=400, headers=headers
            )

        retry_after = _throttle_status(request, visitor_id)
        if retry_after:
            return JsonResponse(
                {"detail": "Too many requests", "retry_after": retry_after},
                status=http_status.HTTP_429_TOO_MANY_REQUESTS,
                headers={**headers, "Retry-After": str(retry_after)},
            )

        conversation = (
            Conversation.objects.filter(
                deployment=deployment,
                visitor_id=visitor_id,
                status=ConversationStatus.OPEN,
            )
            .order_by("-started_at")
            .first()
        )
        if conversation is None:
            return JsonResponse({"conversation_id": None, "messages": []}, headers=headers)

        messages = []
        for message in conversation.messages.all().order_by("created_at", "id"):
            text = _display_content(message.role, message.content)
            if text is None:
                continue
            messages.append({"role": message.role.lower(), "content": text})

        return JsonResponse(
            {"conversation_id": conversation.id, "messages": messages}, headers=headers
        )

    def post(self, request, identifier):
        deployment = self._resolve(identifier)
        if deployment is None or deployment.channel not in _PUBLIC_CHANNELS:
            return self._config_error(
                request, deployment, {"detail": "Deployment not found"}, 404
            )
        headers = self._cors_headers(request, deployment)
        if request.headers.get("Origin") and "Access-Control-Allow-Origin" not in headers:
            return JsonResponse(
                {"detail": "Origin not allowed"}, status=403, headers=headers
            )

        visitor_id = self._visitor_id(request)
        if visitor_id is None:
            return JsonResponse(
                {"detail": "X-Visitor-ID header is required"}, status=400, headers=headers
            )

        message = ""
        try:
            payload = request.data
            if isinstance(payload, dict):
                message = payload.get("message", "")
        except Exception:
            message = ""
        if not isinstance(message, str) or not message.strip():
            return JsonResponse(
                {"detail": "message is required"}, status=400, headers=headers
            )
        if len(message.strip()) > MAX_MESSAGE_CHARS:
            return JsonResponse(
                {"detail": "message is too long"}, status=400, headers=headers
            )

        retry_after = _throttle_status(request, visitor_id)
        if retry_after:
            return JsonResponse(
                {"detail": "Too many requests", "retry_after": retry_after},
                status=http_status.HTTP_429_TOO_MANY_REQUESTS,
                headers={**headers, "Retry-After": str(retry_after)},
            )

        conversation = (
            Conversation.objects.filter(
                deployment=deployment,
                visitor_id=visitor_id,
                status=ConversationStatus.OPEN,
            )
            .order_by("-started_at")
            .first()
        )
        if conversation is None:
            conversation = Conversation.objects.create(
                organization=deployment.organization,
                agent=deployment.agent,
                deployment=deployment,
                channel=deployment.channel,
                visitor_id=visitor_id,
            )

        try:
            result = run_agent_turn(conversation, deployment.agent, message.strip())
        except LLMError:
            return JsonResponse(
                {"detail": "AI service is currently unavailable"},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                headers=headers,
            )

        return JsonResponse(
            {
                "conversation_id": conversation.id,
                "visitor_id": visitor_id,
                "message": result.response,
            },
            headers=headers,
        )


def widget_js(request):
    return HttpResponse(WIDGET_JS, content_type="application/javascript; charset=utf-8")


def widget_config(request, identifier):
    """Public branding/preflight for a website deployment's widget.

    Returns widget display config (title, primary color, welcome message) and
    the resolved agent name. Unresolvable or non-website identifiers 404 so the
    endpoint cannot be used to probe for deployments.
    """
    deployment = (
        AgentDeployment.objects.filter(public_identifier=identifier)
        .select_related("organization", "agent")
        .first()
    )
    if (
        deployment is None
        or not deployment.enabled
        or not deployment.organization.is_active
        or not deployment.agent.is_active
        or deployment.channel != ConversationChannel.WEBSITE
    ):
        return JsonResponse({"detail": "Deployment not found"}, status=404)

    origin = request.headers.get("Origin")
    host = _origin_host(request)
    headers = {}
    if origin and host is not None:
        if _domain_allowed(deployment.allowed_domains, host):
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"

    if request.method == "OPTIONS":
        if origin and "Access-Control-Allow-Origin" not in headers:
            return JsonResponse({"detail": "Origin not allowed"}, status=403, headers=headers)
        headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type, X-Visitor-ID"
        return HttpResponse(status=200, headers=headers)

    if origin and "Access-Control-Allow-Origin" not in headers:
        return JsonResponse({"detail": "Origin not allowed"}, status=403, headers=headers)

    return JsonResponse(
        {
            "identifier": deployment.public_identifier,
            "agent": {"name": deployment.agent.name},
            "title": deployment.widget_title or deployment.agent.name or "Chat with us",
            "primary_color": deployment.widget_primary_color or DEFAULT_WIDGET_COLOR,
            "welcome_message": deployment.welcome_message or "",
            "online": True,
        },
        headers=headers,
    )


def widget_demo(request):
    return HttpResponse(WIDGET_HTML, content_type="text/html; charset=utf-8")