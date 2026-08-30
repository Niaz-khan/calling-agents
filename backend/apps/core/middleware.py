"""Request-scoped middleware: request ids, structured extra logging and safe
JSON error responses in production.
"""

import logging
import uuid

from django.conf import settings
from django.http import JsonResponse

from .context import request_id_var

logger = logging.getLogger("apps.core.middleware")


class RequestIDMiddleware:
    """Attach a request id to each request/response and expose it to logs.

    A caller-supplied ``X-Request-ID`` is honoured (useful for tracing a
    platform-initiated interaction); otherwise a short id is generated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_var.set(request.request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response["X-Request-ID"] = request.request_id
        return response


class JsonExceptionMiddleware:
    """Return a safe JSON 500 instead of a raw stack trace.

    DRF views already own APIException handling; this catches anything that
    escapes (programming errors, unexpected errors in non-DRF views). In
    development the exception propagates so the traceback remains visible.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if settings.DEBUG:
            return None
        logger.exception("Unhandled exception: %s", request.path)
        return JsonResponse({"detail": "Internal server error."}, status=500)