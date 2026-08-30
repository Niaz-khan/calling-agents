"""Request-scoped context propagated into logging records via contextvars."""

import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)