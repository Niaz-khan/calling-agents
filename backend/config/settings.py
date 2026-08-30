"""Django settings for the AI Call Agent platform."""

import datetime
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# Declare the Celery app so `celery worker/app` and task autodiscovery resolve
# even before Django fully initializes the app registry.
from .celery import app as celery_app  # noqa: E402

__all__ = ["celery_app"]


def env(key, default=None):
    return os.environ.get(key, default)


def env_list(key, default=None):
    value = env(key)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def env_int(key, default=0):
    try:
        return int(env(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(key, default=False):
    return env(key, "1" if default else "0") == "1"


def django_cache_config(redis_url):
    """Resolve the default Django cache backend from an optional Redis URL.

    Redis (production) uses Django's built-in RedisCache; otherwise a local
    in-memory cache keeps development and tests dependency-free.
    """
    if redis_url:
        return {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": redis_url,
            "KEY_PREFIX": "ai_call_agent",
        }
    return {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ai_call_agent",
    }


def channel_layers_config(redis_url):
    """Resolve Channels layer: Redis when configured, in-memory otherwise."""
    if redis_url:
        return {
            "default": {
                "BACKEND": "channels_redis.core.RedisChannelLayer",
                "CONFIG": {"hosts": [redis_url]},
            }
        }
    return {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


def parse_database_url(url):
    """Parse a SQLAlchemy-style DATABASE_URL into Django DATABASES options."""
    url = url.replace("postgresql+psycopg://", "postgres://", 1).replace(
        "postgresql://", "postgres://", 1
    )
    if not url.startswith("postgres://"):
        raise RuntimeError("Only PostgreSQL URLs are supported")
    rest = url[len("postgres://"):]
    userinfo, _, hostport = rest.partition("@")
    user, _, password = userinfo.partition(":")
    host, _, port = hostport.partition(":")
    dbname = port.split("/", 1)[-1]
    port = port.split("/", 1)[0]
    host = host or "localhost"
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": dbname,
        "USER": user or "",
        "PASSWORD": password or "",
        "HOST": host,
        "PORT": port or "",
    }


ENVIRONMENT = env("DJANGO_ENV", "development")

SECRET_KEY = env("DJANGO_SECRET_KEY", env("JWT_SECRET_KEY", "insecure-dev-key"))
DEBUG = env("DJANGO_DEBUG", "0" if ENVIRONMENT == "production" else "1") == "1"
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]
)
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])
INTERNAL_IPS = env_list("DJANGO_INTERNAL_IPS", ["127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.accounts",
    "apps.tenancy",
    "apps.agents",
    "apps.crm",
    "apps.conversations",
    "apps.appointments",
    "apps.services",
    "apps.knowledge",
    "apps.telephony",
    "apps.voice",
    "apps.analytics",
    "apps.ai",
    "apps.core",
    "apps.cms",
    "apps.platform",
]

MIDDLEWARE = [
    "apps.core.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.JsonExceptionMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Redis + Channels
# ---------------------------------------------------------------------------
# Redis is optional in development (no external dependency for normal HTTP).
# When REDIS_URL is set (production) it powers the Channels layer and the
# default Django cache, which DRF throttling uses. Keep in-process layers
# otherwise so local development works without Redis running.
REDIS_URL = (env("REDIS_URL", "") or "").rstrip("/") or None

CHANNEL_LAYERS = channel_layers_config(REDIS_URL)

CACHES = {"default": django_cache_config(REDIS_URL)}

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
_database_default = "postgresql://callagent:callagent@localhost:5432/callagent"
DATABASES = {"default": parse_database_url(env("DATABASE_URL", _database_default))}
DATABASES["default"].update(
    {
        # Reuse connections in production; health-checks clear stale sockets.
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60 if ENVIRONMENT == "production" else 0),
        "CONN_HEALTH_CHECKS": env_bool("DB_CONN_HEALTH_CHECKS", True),
        "OPTIONS": {"connect_timeout": env_int("DB_CONNECT_TIMEOUT", 10)},
    }
)

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = env("DJANGO_STATIC_URL", "static/")
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = env("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / "media"

# Upload limits (knowledge documents, logos) — reasonable, not unbounded.
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Production security
# ---------------------------------------------------------------------------
# Nginx terminates TLS and forwards X-Forwarded-Proto in production; honour it
# only when the proxy header is actually present.
SECURE_PROXY_SSL_HEADER = None
if env_bool("DJANGO_BEHIND_PROXY", ENVIRONMENT == "production"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", ENVIRONMENT == "production")
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", ENVIRONMENT == "production")
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", ENVIRONMENT == "production")
SECURE_HSTS_SECONDS = env_int(
    "DJANGO_SECURE_HSTS_SECONDS", 31536000 if ENVIRONMENT == "production" else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", ENVIRONMENT == "production"
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = env("DJANGO_X_FRAME_OPTIONS", "DENY")

# Production environment guard: fail fast instead of running insecure.
if ENVIRONMENT == "production":
    problems = []
    if DEBUG:
        problems.append("DJANGO_DEBUG must be 0 in production")
    if not env("DJANGO_SECRET_KEY") or SECRET_KEY == "insecure-dev-key":
        problems.append("DJANGO_SECRET_KEY must be set to a unique strong value")
    if not env("DATABASE_URL"):
        problems.append("DATABASE_URL must be set in production")
    if problems:
        raise ImproperlyConfigured("; ".join(problems))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.core.logging_filters.RequestIDFilter"},
        "redact": {"()": "apps.core.logging_filters.RedactSecretsFilter"},
    },
    "formatters": {
        "json": {"()": "apps.core.logging_formatters.StructuredJsonFormatter"},
        "console": {
            "format": "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_id", "redact"],
            "formatter": "json" if ENVIRONMENT == "production" else "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.security": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "apps": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
# Infrastructure pre-requisite for background jobs (summaries, analytics,
# document processing, notifications, usage metering). HTTP functionality does
# not depend on a running worker.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL or "")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL or "")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", 300)
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 600)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_CREDENTIALS = True
# The public widget endpoints manage their own per-deployment CORS and
# preflight handling; leave only private/organization routes to the middleware.
CORS_URLS_REGEX = r"^/(?!public/).*$"
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ORIGINS",
    [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
)

# ---------------------------------------------------------------------------
# Django REST Framework + JWT
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "public_cms": env("PUBLIC_CMS_RATE", "300/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(
        minutes=int(env("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    ),
    "ALGORITHM": env("JWT_ALGORITHM", "HS256"),
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Application-level configuration
# ---------------------------------------------------------------------------

APP_NAME = env("APP_NAME", "AI Call Agent")
APP_VERSION = env("APP_VERSION", "1.0.0")

LLM_API_KEY = env("LLM_API_KEY", "")
LLM_MODEL = env("LLM_MODEL", "gpt-4o-mini")
LLM_BASE_URL = env("LLM_BASE_URL", "") or None

STT_PROVIDER = env("STT_PROVIDER", "openai")
STT_MODEL = env("STT_MODEL", "whisper-1")
STT_LANGUAGE = env("STT_LANGUAGE", "") or None
STT_API_KEY = env("STT_API_KEY", "") or None
STT_BASE_URL = env("STT_BASE_URL", "") or None

TTS_PROVIDER = env("TTS_PROVIDER", "edge")
TTS_MODEL = env("TTS_MODEL", "en-US-JennyNeural")
TTS_VOICE = env("TTS_VOICE", "en-US-JennyNeural")
TTS_FORMAT = env("TTS_FORMAT", "mp3")
TTS_API_KEY = env("TTS_API_KEY", "") or None
TTS_BASE_URL = env("TTS_BASE_URL", "") or None

VOICE_MAX_UTTERANCE_SECONDS = int(env("VOICE_MAX_UTTERANCE_SECONDS", "30"))
VOICE_HEARTBEAT_SECONDS = int(env("VOICE_HEARTBEAT_SECONDS", "20"))
VOICE_IDLE_TIMEOUT_SECONDS = int(env("VOICE_IDLE_TIMEOUT_SECONDS", "300"))

# Real-time media streaming (Twilio Media Streams). When disabled (default),
# the TwiML/Gather loop remains the live voice path.
VOICE_STREAMING_ENABLED = env("VOICE_STREAMING_ENABLED", "0") == "1"
# RMS energy (0..32767) above which a 20ms frame counts as speech.
VOICE_STREAM_SPEECH_THRESHOLD = int(env("VOICE_STREAM_SPEECH_THRESHOLD", "1000"))
# Trailing silence (seconds) before an utterance is committed to STT.
VOICE_STREAM_END_SILENCE_SECONDS = float(env("VOICE_STREAM_END_SILENCE_SECONDS", "0.6"))

TELEPHONY_PROVIDER = env("TELEPHONY_PROVIDER", "twilio")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", "")
TELNYX_API_KEY = env("TELNYX_API_KEY", "")
TELNYX_PUBLIC_KEY = env("TELNYX_PUBLIC_KEY", "")
TELNYX_CONNECTION_ID = env("TELNYX_CONNECTION_ID", "")
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:8000")

EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", "openai")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(env("EMBEDDING_DIMENSIONS", "512"))
EMBEDDING_API_KEY = env("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = env("EMBEDDING_BASE_URL", "") or None
KNOWLEDGE_SEARCH_LIMIT = int(env("KNOWLEDGE_SEARCH_LIMIT", "5"))
KNOWLEDGE_RELEVANCE_THRESHOLD = float(env("KNOWLEDGE_RELEVANCE_THRESHOLD", "0.30"))

# Late production sanity checks (values above are defined by this point).
if ENVIRONMENT == "production" and not PUBLIC_BASE_URL.startswith("https://"):
    raise ImproperlyConfigured("PUBLIC_BASE_URL must be HTTPS in production")