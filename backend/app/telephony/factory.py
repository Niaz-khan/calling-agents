from app.config import settings
from app.telephony.base import TelephonyProvider
from app.telephony.twilio import TwilioProvider


def get_telephony_provider() -> TelephonyProvider:
    if settings.telephony_provider == "twilio":
        return TwilioProvider(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
        )

    raise ValueError(f"Unsupported telephony provider: {settings.telephony_provider}")