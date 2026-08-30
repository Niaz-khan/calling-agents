"""Structured JSON log formatter for production.

Emits one JSON object per line with stable keys, an ISO timestamp, the
request id (when a request-scoped id exists) and optional extra fields.
"""

import json
import logging
from datetime import datetime, timezone


class StructuredJsonFormatter(logging.Formatter):
    safe_keys = ("request_id", "organization_id", "agent_id", "call_id", "deployment_id")

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key in self.safe_keys:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        extra = getattr(record, "meta", None)
        if isinstance(extra, dict):
            payload["meta"] = extra

        return json.dumps(payload, default=str)