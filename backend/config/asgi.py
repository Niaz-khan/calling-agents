"""ASGI config for the AI Call Agent project.

Routes HTTP through Django and WebSockets through the Channels URL router so
Django + Daphne serve both on one port (HTTP, Chunked transfers, and the
Twilio Media Streams websocket URL).

Production: ``daphne -b 0.0.0.0 -p 8000 config.asgi:application`` behind nginx
which terminates TLS and forwards ``X-Forwarded-Proto: https``.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import re_path  # noqa: E402

from apps.voice.consumers import TwilioMediaStreamConsumer  # noqa: E402

websocket_urlpatterns = [
    re_path(
        r"^telephony/twilio/media/?$",
        TwilioMediaStreamConsumer.as_asgi(),
    ),
]

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(websocket_urlpatterns),
    }
)