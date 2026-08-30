"""Telnyx telephony provider.

Telnyx Programmable Voice is event/command driven rather than TwiML driven:

* outbound calls are placed with ``POST /v2/calls`` (Bearer API key);
* call events are delivered as JSON webhooks whose URL is configured on the
  Voice API Application ("connection");
* call legs are controlled with ``POST /v2/calls/{call_control_id}/actions/*``.

Webhooks are signed with Ed25519 over ``{timestamp}|{raw_body}`` and verified
with the account public key (Mission Control > Account Settings > Keys &
Credentials > Public Key). Provider-specific details stay in this module.
"""

import base64
import time

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .base import TelephonyCall, TelephonyProvider

WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300

TELNYX_EVENT_TO_STATUS = {
    "call.initiated": "ringing",
    "call.answered": "in-progress",
    "call.hangup": "completed",
}

_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def validate_telnyx_signature(
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    public_key: str,
    *,
    tolerance_seconds: int = WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS,
) -> bool:
    """Verify an Ed25519-signed Telnyx webhook delivery.

    The signed message is the exact byte string ``{timestamp}|{raw_body}``.
    Stale timestamps are rejected to blunt replay attacks.
    """
    if not signature or not timestamp or not public_key:
        return False

    try:
        received = int(timestamp)
    except (TypeError, ValueError):
        return False

    if abs(time.time() - received) > tolerance_seconds:
        return False

    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            base64.b64decode(public_key)
        )
        raw_signature = base64.b64decode(signature)

        public_key.verify(
            raw_signature,
            f"{received}|".encode() + raw_body,
        )
    except (InvalidSignature, ValueError, TypeError):
        return False

    return True


def telnyx_event_to_status(event_type: str) -> str | None:
    """Map a Telnyx call event to a normalized provider status."""
    return TELNYX_EVENT_TO_STATUS.get((event_type or "").strip())


class TelnyxProvider:
    """Telnyx telephony integration."""

    def __init__(
        self,
        api_key: str,
        connection_id: str | None = None,
        base_url: str = "https://api.telnyx.com/v2",
        http_client: httpx.AsyncClient | None = None,
    ):
        self._api_key = api_key
        self._connection_id = connection_id
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    def _calls_url(self, provider_call_id: str | None = None) -> str:
        url = f"{self._base_url}/calls"

        if provider_call_id:
            url = f"{self._base_url}/calls/{provider_call_id}"

        return url

    async def create_call(
        self,
        from_number: str,
        to_number: str,
        webhook_url: str | None = None,
        status_callback_url: str | None = None,
    ) -> str:
        """Place an outbound call, returning the call control id.

        Telnyx routes call events through the Voice API Application's webhook
        configuration, so ``webhook_url``/``status_callback_url`` are accepted
        for protocol compatibility but intentionally not part of the request
        payload.
        """
        if not self._connection_id:
            raise ValueError("Telnyx connection_id is not configured")

        data = {
            "from": from_number,
            "to": to_number,
            "connection_id": self._connection_id,
        }

        response = await self._client().post(
            self._calls_url(),
            headers={"Authorization": f"Bearer {self._api_key}", **_HEADERS},
            json=data,
        )

        response.raise_for_status()

        return response.json()["data"]["call_control_id"]

    async def end_call(self, provider_call_id: str) -> None:
        response = await self._client().post(
            f"{self._calls_url(provider_call_id)}/actions/hangup",
            headers={"Authorization": f"Bearer {self._api_key}", **_HEADERS},
            json={},
        )

        response.raise_for_status()

    async def answer_call(self, provider_call_id: str) -> None:
        """Answer an inbound call leg so the caller is connected."""
        response = await self._client().post(
            f"{self._calls_url(provider_call_id)}/actions/answer",
            headers={"Authorization": f"Bearer {self._api_key}", **_HEADERS},
            json={},
        )

        response.raise_for_status()

    async def transfer_call(self, provider_call_id: str, to_number: str) -> None:
        response = await self._client().post(
            f"{self._calls_url(provider_call_id)}/actions/transfer",
            headers={"Authorization": f"Bearer {self._api_key}", **_HEADERS},
            json={"to": to_number},
        )

        response.raise_for_status()

    async def get_call(self, provider_call_id: str) -> TelephonyCall:
        response = await self._client().get(
            self._calls_url(provider_call_id),
            headers={"Authorization": f"Bearer {self._api_key}", **_HEADERS},
        )

        response.raise_for_status()

        data = response.json()["data"]

        return TelephonyCall(
            provider_call_id=provider_call_id,
            from_number=data.get("from", ""),
            to_number=data.get("to", ""),
            status=data.get("state") or data.get("call_status", ""),
            started_at=data.get("start_time"),
            metadata=data,
        )

    async def verify_credentials(self) -> bool:
        """Confirm the configured API key can reach the Telnyx API."""
        try:
            response = await self._client().get(
                f"{self._base_url}/balance",
                headers={"Authorization": f"Bearer {self._api_key}", **_HEADERS},
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()

        return self._http_client