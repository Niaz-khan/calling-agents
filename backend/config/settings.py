"""Django settings for the AI Call Agent platform."""

import datetime
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env(key, default=None):
    return os.environ.get(key, default)


def env_list(key, default=None):
    value = env(key)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


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


SECRET_KEY = env("DJANGO_SECRET_KEY", env("JWT_SECRET_KEY", "insecure-dev-key"))
DEBUG = env("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"]
)

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
    "accounts",
    "tenancy",
    "agents",
    "crm",
    "conversations",
    "appointments",
    "knowledge",
    "telephony",
    "analytics",
    "ai",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

DATABASES = {
    "default": parse_database_url(
        env(
            "DATABASE_URL",
            "postgresql://callagent:callagent@localhost:5432/callagent",
        )
    ),
}

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

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_CREDENTIALS = True
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

TTS_PROVIDER = env("TTS_PROVIDER", "openai")
TTS_MODEL = env("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = env("TTS_VOICE", "alloy")
TTS_FORMAT = env("TTS_FORMAT", "wav")

VOICE_MAX_UTTERANCE_SECONDS = int(env("VOICE_MAX_UTTERANCE_SECONDS", "30"))
VOICE_HEARTBEAT_SECONDS = int(env("VOICE_HEARTBEAT_SECONDS", "20"))
VOICE_IDLE_TIMEOUT_SECONDS = int(env("VOICE_IDLE_TIMEOUT_SECONDS", "300"))

TELEPHONY_PROVIDER = env("TELEPHONY_PROVIDER", "twilio")
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", "")
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:8000")

EMBEDDING_PROVIDER = env("EMBEDDING_PROVIDER", "openai")
EMBEDDING_MODEL = env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = int(env("EMBEDDING_DIMENSIONS", "512"))
EMBEDDING_API_KEY = env("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = env("EMBEDDING_BASE_URL", "") or None
KNOWLEDGE_SEARCH_LIMIT = int(env("KNOWLEDGE_SEARCH_LIMIT", "5"))
KNOWLEDGE_RELEVANCE_THRESHOLD = float(env("KNOWLEDGE_RELEVANCE_THRESHOLD", "0.30"))