"""Logging filters that add request context and scrub secrets.

The redact filter is structural defence-in-depth: never rely on it alone.
Call paths that must not log secrets should not pass them to ``logger.*`` in
the first place.
"""

import logging

from django.conf import settings

from .context import request_id_var


class RequestIDFilter(logging.Filter):
    """Attach the active request id to every record."""

    def filter(self, record):
        record.request_id = request_id_var.get()
        return True


def _collect_secrets():
    """Gather configured secret values that must never appear in logs."""
    keys = [
        "SECRET_KEY",
        "TWILIO_AUTH_TOKEN",
        "TELNYX_API_KEY",
        "TELNYX_PUBLIC_KEY",
        "LLM_API_KEY",
        "STT_API_KEY",
        "TTS_API_KEY",
        "EMBEDDING_API_KEY",
    ]
    secrets = set()
    for key in keys:
        value = getattr(settings, key, None)
        if value and len(str(value)) >= 8:
            secrets.add(str(value))
    return secrets


class RedactSecretsFilter(logging.Filter):
    """Replace configured secret values in log messages with a placeholder."""

    def __init__(self, secrets=None, name=""):
        super().__init__(name=name)
        self.secrets = secrets if secrets is not None else _collect_secrets()

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            if secret and secret in message:
                message = message.replace(secret, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True