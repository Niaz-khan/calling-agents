"""Celery tasks for core infrastructure.

Only harmless infrastructure tasks live here for now. Movement of
conversation-critical agent behavior into Celery is intentionally deferred;
these prove the broker/worker wiring works end to end.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="core.ping")
def ping():
    """Lightweight liveness task for broker/worker health checks."""
    return "pong"


@shared_task(name="core.health_check")
def health_check():
    """Return a structured health payload a monitor can consume."""
    return {"status": "ok", "task": "core.health_check"}