"""Celery application configuration.

Broker/result backend come from CELERY_BROKER_URL / CELERY_RESULT_BACKEND
(settings), which in turn live on REDIS_URL. JSON serialization and the
project timezone are forced so producers/consumers agree on wire format.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("ai_call_agent")
app.config_from_object("django.conf:settings", namespace="CELERY")
# Task autodiscovery happens from apps.core.apps.CoreConfig.ready() — at this
# point Django is fully initialized, so <app>.tasks modules import cleanly.