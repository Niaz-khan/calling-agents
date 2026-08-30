"""Twilio telephony provider.

Provider-specific formats (TwiML, signatures, REST payloads) stay here so the
rest of the application only deals with normalized types.
"""

import base64
import hashlib
import hmac

import httpx
from xml.sax.saxutils import escape

from .base import TelephonyCall, TelephonyProvider


class TwilioProvider:
    """Twilio telephony integration."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        base_url: str = "https://api.twilio.com/2010-04-01",
        http_client: httpx.AsyncClient | None = None,
    ):
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    def _calls_url(self, provider_call_id: str | None = None) -> str:
        url = f"{self._base_url}/Accounts/{self._account_sid}/Calls.json"

        if provider_call_id:
            url = f"{self._base_url}/Accounts/{self._account_sid}/Calls/{provider_call_id}.json"

        return url

    async def create_call(
        self,
        from_number: str,
        to_number: str,
        webhook_url: str | None = None,
        status_callback_url: str | None = None,
    ) -> str:
        data = {
            "From": from_number,
            "To": to_number,
        }

        if webhook_url:
            data["Url"] = webhook_url

        if status_callback_url:
            data["StatusCallback"] = status_callback_url
            data["StatusCallbackEvent"] = "answered completed failed"

        response = await self._client().post(
            self._calls_url(),
            auth=(self._account_sid, self._auth_token),
            data=data,
        )

        response.raise_for_status()

        return response.json()["sid"]

    async def end_call(self, provider_call_id: str) -> None:
        response = await self._client().post(
            self._calls_url(provider_call_id),
            auth=(self._account_sid, self._auth_token),
            data={"Status": "completed"},
        )

        response.raise_for_status()

    async def transfer_call(self, provider_call_id: str, to_number: str) -> None:
        response = await self._client().post(
            self._calls_url(provider_call_id),
            auth=(self._account_sid, self._auth_token),
            data={"Twiml": build_dial_twiml(to_number)},
        )

        response.raise_for_status()

    async def get_call(self, provider_call_id: str) -> TelephonyCall:
        response = await self._client().get(
            self._calls_url(provider_call_id),
            auth=(self._account_sid, self._auth_token),
        )

        response.raise_for_status()

        data = response.json()

        return TelephonyCall(
            provider_call_id=data["sid"],
            from_number=data.get("From", ""),
            to_number=data.get("To", ""),
            status=data.get("Status", ""),
        )

    async def verify_credentials(self) -> bool:
        """Confirm the configured account can be reached."""
        try:
            response = await self._client().get(
                f"{self._base_url}/Accounts/{self._account_sid}.json",
                auth=(self._account_sid, self._auth_token),
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()

        return self._http_client


def validate_twilio_signature(
    url: str,
    params: dict[str, str],
    signature: str | None,
    auth_token: str,
) -> bool:
    if signature is None or not auth_token:
        return False

    sorted_params = "".join(
        f"{key}{params[key]}" for key in sorted(params.keys())
    )

    raw = url + sorted_params

    digest = hmac.new(
        auth_token.encode(),
        raw.encode(),
        hashlib.sha1,
    ).digest()

    expected = base64.b64encode(digest)

    return hmac.compare_digest(expected, signature.encode())


def build_dial_twiml(to_number: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Dial>"
        + escape(to_number)
        + "</Dial></Response>"
    )


def build_hangup_twiml() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def build_say_twiml(message: str, language: str = "en-US") -> str:
    """TwiML that speaks a line of text and then lets the call end."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response><Say voice="alice" language="' + escape(language) + '">'
        + escape(message)
        + "</Say></Response>"
    )


def build_gather_twiml(
    say: str,
    gather_url: str,
    *,
    timeout: int = 5,
    speech_timeout: str = "auto",
    language: str = "en-US",
) -> str:
    """TwiML that speaks a line of text and then gathers the caller's speech.

    ``trim``, ``speechModel``, ``enhanced`` and ``actionOnEmptyResult`` tune
    recognition quality for phone audio and force a POST even when the caller
    says nothing, so the loop can re-prompt instead of silently hanging.
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Response><Say voice="alice" language="' + escape(language) + '">'
        + escape(say)
        + '</Say><Gather input="speech" speechTimeout="' + escape(speech_timeout)
        + '" trim="trim-silence"'
        + ' speechModel="phone_call"'
        + ' enhanced="true"'
        + ' actionOnEmptyResult="true"'
        + '" timeout="' + str(timeout)
        + '" action="' + escape(gather_url)
        + '" method="POST"/></Response>'
    )