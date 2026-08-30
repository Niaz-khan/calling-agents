"""Telephony provider factory."""

from django.conf import settings

from .base import TelephonyProvider
from .telnyx import TelnyxProvider
from .twilio import TwilioProvider


def get_telephony_provider() -> TelephonyProvider:
    if settings.TELEPHONY_PROVIDER == "twilio":
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise ValueError("Twilio credentials are not configured")

        return TwilioProvider(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
        )

    if settings.TELEPHONY_PROVIDER == "telnyx":
        if not settings.TELNYX_API_KEY:
            raise ValueError("Telnyx API key is not configured")

        return TelnyxProvider(
            api_key=settings.TELNYX_API_KEY,
            connection_id=settings.TELNYX_CONNECTION_ID or None,
        )

    raise ValueError(f"Unsupported telephony provider: {settings.TELEPHONY_PROVIDER}")