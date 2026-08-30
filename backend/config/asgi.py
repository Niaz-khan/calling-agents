"""ASGI config for the AI Call Agent project.

Routes HTTP through Django and WebSockets through the Channels URL router.
The only websocket route is the Twilio Media Streams endpoint used by the
real-time voice channel; every other protocol continues to use WSGI.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.urls import re_path  # noqa: E402

from apps.voice.consumers import TwilioMediaStreamConsumer  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(
            [
                re_path(
                    r"^telephony/twilio/media/?$",
                    TwilioMediaStreamConsumer.as_asgi(),
                ),
            ]
        ),
    }
)