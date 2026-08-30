"""Operations/infrastructure tests: readiness, logging, settings helpers,
deployment check, ASGI routing and production posture."""

import asyncio
import json
import logging
import os
import subprocess
import sys
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import OperationalError
from django.test import override_settings

import config.asgi  # noqa: F401  (module import exercises routing wiring)
from apps.core import views as core_views
from apps.core.context import request_id_var
from apps.core.logging_filters import RedactSecretsFilter, RequestIDFilter
from apps.core.logging_formatters import StructuredJsonFormatter
from config import settings as settings_module


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def test_cache_config_switches_on_redis_url():
    with_redis = settings_module.django_cache_config("redis://127.0.0.1:6379/0")
    assert with_redis["BACKEND"].endswith("RedisCache")
    assert with_redis["LOCATION"].startswith("redis://")
    assert with_redis["KEY_PREFIX"] == "ai_call_agent"

    local = settings_module.django_cache_config(None)
    assert local["BACKEND"].endswith("LocMemCache")


def test_channel_layers_switch_on_redis_url():
    with_redis = settings_module.channel_layers_config("redis://127.0.0.1:6379/0")
    assert with_redis["default"]["BACKEND"] == "channels_redis.core.RedisChannelLayer"
    assert with_redis["default"]["CONFIG"]["hosts"] == ["redis://127.0.0.1:6379/0"]

    local = settings_module.channel_layers_config(None)
    assert local["default"]["BACKEND"] == "channels.layers.InMemoryChannelLayer"


def test_default_database_is_postgres():
    engine = settings.DATABASES["default"]["ENGINE"]
    assert engine == "django.db.backends.postgresql"


def test_parse_database_url_rejects_non_postgres():
    with pytest.raises(RuntimeError, match="Only PostgreSQL"):
        settings_module.parse_database_url("sqlite:///test.db")


def test_production_security_defaults():
    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.X_FRAME_OPTIONS == "DENY"


def test_production_guard_rejects_insecure_env(tmp_path):
    """A DJANGO_ENV=production process fails startup without valid values."""
    env = dict(os.environ)
    env["DJANGO_ENV"] = "production"
    env["DJANGO_DEBUG"] = "0"
    backend_dir = str(settings_module.BASE_DIR)
    proc = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    output = (proc.stdout + proc.stderr).lower()
    assert proc.returncode != 0
    assert "improperlyconfigured" in output


# ---------------------------------------------------------------------------
# Readiness / health
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_readiness_ok(api_client):
    response = api_client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] == "not_configured"


@pytest.mark.django_db
def test_readiness_reports_database_failure(api_client, monkeypatch):
    def _boom():
        raise OperationalError("database is down")

    monkeypatch.setattr(core_views, "_database_healthy", _boom)
    response = api_client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "error"
    assert body["database"] == "error"


@pytest.mark.django_db
def test_readiness_checks_redis_when_configured(api_client, monkeypatch):
    monkeypatch.setattr(core_views, "_redis_healthy", lambda: True)
    with override_settings(REDIS_URL="redis://127.0.0.1:6379/0"):
        response = api_client.get("/ready")
    assert response.status_code == 200
    assert response.json()["redis"] == "ok"

    def _boom():
        raise OSError("redis unreachable")

    monkeypatch.setattr(core_views, "_redis_healthy", _boom)
    with override_settings(REDIS_URL="redis://127.0.0.1:6379/0"):
        response = api_client.get("/ready")
    assert response.status_code == 503
    assert response.json()["redis"] == "error"


@pytest.mark.django_db
def test_health_and_db_health_still_work(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}
    assert api_client.get("/db-health").json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Request ids + structured logging
# ---------------------------------------------------------------------------

def test_request_id_middleware_generates_and_echoes(api_client):
    response = api_client.get("/health")
    assert "X-Request-ID" in response
    assert len(response["X-Request-ID"]) > 0


def test_request_id_middleware_honours_caller_header(api_client):
    response = api_client.get("/health", HTTP_X_REQUEST_ID="trace-abc-123")
    assert response["X-Request-ID"] == "trace-abc-123"


def test_request_id_filter_uses_contextvar():
    record = logging.LogRecord("t", logging.INFO, "", 0, "hello", (), None)
    assert RequestIDFilter().filter(record)
    assert record.request_id == "-"

    token = request_id_var.set("req-42")
    try:
        assert RequestIDFilter().filter(record)
        assert record.request_id == "req-42"
    finally:
        request_id_var.reset(token)


def test_redact_filter_scrubs_configured_secrets():
    record = logging.LogRecord(
        "t", logging.INFO, "", 0, "token=supersecretvalue123", (), None
    )
    RedactSecretsFilter(secrets={"supersecretvalue123"}).filter(record)
    assert "supersecretvalue123" not in record.getMessage()
    assert "REDACTED" in record.getMessage()


def test_structured_json_formatter_is_parseable():
    record = logging.LogRecord(
        "apps.test", logging.INFO, "", 0, "booted", (), None
    )
    record.request_id = "req-7"
    payload = json.loads(StructuredJsonFormatter().format(record))
    assert payload["message"] == "booted"
    assert payload["request_id"] == "req-7"
    assert payload["level"] == "INFO"
    assert "time" in payload


# ---------------------------------------------------------------------------
# ASGI / Channels routing
# ---------------------------------------------------------------------------

def test_asgi_application_serves_http_and_websockets():
    application = config.asgi.application
    mapping = application.application_mapping
    assert "http" in mapping
    assert "websocket" in mapping


@pytest.mark.django_db
def test_asgi_routes_twilio_media_websocket():
    """Connecting to the media path reaches the consumer (rejected on a bogus
    token), proving the Channels URLRouter wiring works end to end."""
    from channels.db import database_sync_to_async
    from channels.testing import WebsocketCommunicator

    def _close_all():
        from django.db import connections

        connections.close_all()

    async def scenario():
        communicator = WebsocketCommunicator(
            config.asgi.application,
            "/telephony/twilio/media?token=bogus",
        )
        connected, code = await communicator.connect()
        # Release the asgiref worker-thread connection so pytest can drop the
        # test database (same pattern as apps/voice/test_consumer.py).
        await database_sync_to_async(_close_all)()
        return connected

    assert asyncio.run(scenario()) is False


# ---------------------------------------------------------------------------
# Deployment check command
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_deployment_check_passes_in_test_env():
    call_command("deployment_check")


@pytest.mark.django_db
def test_deployment_check_never_prints_secrets():
    out = StringIO()
    with override_settings(SECRET_KEY="SUPER-SECRET-VALUE"):
        call_command("deployment_check", stdout=out)
    assert "SUPER-SECRET-VALUE" not in out.getvalue()


@pytest.mark.django_db
def test_deployment_check_strict_fails_on_insecure_config():
    with override_settings(DEBUG=True):
        with pytest.raises(SystemExit):
            call_command("deployment_check", "--strict")