"""Twilio media-stream websocket consumer.

Twilio connects to ``/telephony/twilio/media?token=...`` when a call's TwiML
uses ``<Connect><Stream>``. The token is secret and per-call, so the consumer
resolves the owning conversation from the database -- never from a client
field -- and verifies the ``start`` event's ``callSid`` before allowing media.
``connect()`` is transport-specific; from there the ``StreamingVoiceSession``
owns the call state (barge-in, max duration, idle, transfer) and this consumer
just relays events in both directions.
"""

import asyncio
import base64
import binascii
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from apps.telephony.providers.factory import get_telephony_provider
from apps.telephony.services import (
    apply_provider_status,
    get_conversation_by_stream_token,
)
from apps.telephony.webhooks import GREETING

from .codec import _normalize_codec, decode_codec
from .session import VoiceSessionEngine
from .stt import get_stt_provider
from .streaming import StreamingVoiceSession
from .tts import get_tts_provider

logger = logging.getLogger(__name__)


def _greeting_for(agent) -> str:
    return (agent.voice_greeting or "").strip() or GREETING


def _max_duration_seconds_for(agent) -> int | None:
    minutes = agent.max_call_duration_minutes
    if minutes is None:
        return None
    return int(minutes) * 60


# One consumer per provider call id so duplicate/rogue connections cannot
# double-process the same call's audio.
_ACTIVE_STREAMS: dict[str, "TwilioMediaStreamConsumer"] = {}


class TwilioMediaStreamConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conversation = None
        self._provider_call_id = None
        self._stream_sid = ""
        self._codec = "mulaw"
        self._session = None
        self._heartbeat_task = None
        self._started = False
        self._finalized = False
        self._skip_completion = False

    # -- connection lifecycle ----------------------------------------------

    async def connect(self):
        self._conversation = None
        self._provider_call_id = None
        token = self._query_token()

        if not token:
            logger.warning("Media stream connect rejected: missing token")
            await self.close(code=4001)
            return

        conversation = await database_sync_to_async(
            get_conversation_by_stream_token
        )(token)

        if conversation is None:
            logger.warning("Media stream connect rejected: unknown token")
            await self.close(code=4403)
            return

        self._conversation = conversation
        self._provider_call_id = conversation.phone_call.provider_call_id

        if self._provider_call_id in _ACTIVE_STREAMS:
            logger.warning(
                "Media stream connect rejected: %s already streaming",
                self._provider_call_id,
            )
            await self.close(code=4401)
            return

        _ACTIVE_STREAMS[self._provider_call_id] = self
        await self.accept()

    async def disconnect(self, code):
        await self._finalize()

    def _query_token(self) -> str:
        query = self.scope.get("query_string", b"")
        for pair in query.split(b"&"):
            if pair.startswith(b"token="):
                return pair.split(b"=", 1)[1].decode("utf-8", "ignore")
        return ""

    # -- framing -----------------------------------------------------------

    async def receive(self, text_data=None, bytes_data=None):
        try:
            message = json.loads(text_data or "")
        except (TypeError, ValueError):
            logger.warning("Media stream dropped malformed frame")
            return

        event = message.get("event")

        if event == "start":
            await self._handle_start(message)
        elif event == "media":
            await self._handle_media(message)
        elif event == "dtmf":
            await self._handle_dtmf(message)
        elif event == "stop":
            await self._finalize_and_close()
        elif event in ("connected", "mark"):
            pass

    async def _handle_start(self, message: dict) -> None:
        if self._started or self._session is not None:
            return

        call_sid = message.get("callSid") or ""
        if call_sid and call_sid != self._provider_call_id:
            logger.warning(
                "Media stream start rejected: stream %s on call %s for call %s",
                message.get("streamSid"),
                call_sid,
                self._provider_call_id,
            )
            await self._abort()
            return

        self._stream_sid = message.get("streamSid") or ""
        media_format = message.get("mediaFormat") or {}
        encoding = media_format.get("encoding") or "audio/x-mulaw"
        normalized = _normalize_codec(encoding)
        self._codec = normalized if normalized in ("mulaw", "alaw", "pcm16") else "mulaw"

        conversation = self._conversation

        if self._provider_call_id:
            await database_sync_to_async(apply_provider_status)(
                self._provider_call_id, "in-progress"
            )

        stt = await asyncio.to_thread(get_stt_provider)
        tts = await asyncio.to_thread(get_tts_provider)
        engine = VoiceSessionEngine(
            conversation=conversation,
            agent=conversation.agent,
            stt_provider=stt,
            tts_provider=tts,
        )

        session = StreamingVoiceSession(
            engine,
            codec=self._codec,
            max_duration_seconds=_max_duration_seconds_for(conversation.agent),
            idle_timeout_seconds=settings.VOICE_IDLE_TIMEOUT_SECONDS,
            on_audio=self._send_media,
            on_clear=self._send_clear,
            on_end=self._handle_end,
            on_transfer=self._handle_transfer,
        )
        self._session = session

        await session.start()
        self._started = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat())

        logger.info(
            "Media stream started for call %s (conversation %s, codec %s)",
            self._provider_call_id,
            conversation.id,
            self._codec,
        )

        await session.greet(_greeting_for(conversation.agent))

    async def _handle_media(self, message: dict) -> None:
        if self._session is None:
            return

        payload = (message.get("media") or {}).get("payload") or ""
        if not payload:
            return

        try:
            wire = base64.b64decode(payload)
        except (ValueError, binascii.Error):
            logger.warning("Media stream dropped undecodable payload")
            return

        await self._session.handle_media(decode_codec(wire, self._codec))

    async def _handle_dtmf(self, message: dict) -> None:
        if self._session is None:
            return

        digit = (message.get("dtmf") or {}).get("digit") or ""
        if digit:
            await self._session.handle_text(digit)

    # -- outbound relays ---------------------------------------------------

    async def _send_media(self, payload: bytes) -> None:
        if not self._stream_sid:
            return
        try:
            await self.send(
                text_data=json.dumps(
                    {
                        "event": "media",
                        "streamSid": self._stream_sid,
                        "media": {
                            "payload": base64.b64encode(payload).decode("ascii")
                        },
                    }
                )
            )
        except Exception:
            # The call may already be over (connection closed); the session
            # keeps streaming a best-effort final reply, so just drop it.
            logger.debug("Outbound media send failed for call %s", self._provider_call_id)

    async def _send_clear(self) -> None:
        if not self._stream_sid:
            return
        try:
            await self.send(
                text_data=json.dumps(
                    {"event": "clear", "streamSid": self._stream_sid}
                )
            )
        except Exception:
            logger.debug("Clear send failed for call %s", self._provider_call_id)

    async def _heartbeat(self) -> None:
        try:
            while not self._finalized:
                await asyncio.sleep(settings.VOICE_HEARTBEAT_SECONDS)
                if not self._stream_sid:
                    continue
                await self.send(
                    text_data=json.dumps(
                        {
                            "event": "mark",
                            "streamSid": self._stream_sid,
                            "mark": {"name": "heartbeat"},
                        }
                    )
                )
        except asyncio.CancelledError:
            pass

    # -- call-level callbacks from the session -----------------------------

    async def _handle_end(self, reason: str) -> None:
        logger.info(
            "Media stream ending call %s: %s", self._provider_call_id, reason
        )
        await self._finalize_and_close()

    async def _handle_transfer(self, target: str | None) -> None:
        self._skip_completion = True
        logger.info(
            "Transferring media-stream call %s to %s",
            self._provider_call_id,
            target or "no destination",
        )
        if target:
            try:
                provider = await asyncio.to_thread(get_telephony_provider)
                await provider.transfer_call(self._provider_call_id, target)
            except Exception:
                logger.exception(
                    "Transfer failed for call %s", self._provider_call_id
                )
        await self._finalize_and_close()

    # -- finalize ----------------------------------------------------------

    async def _abort(self) -> None:
        """Close a stream that was never legitimately started.

        Unlike ``_finalize`` this never touches the conversation/phone call
        lifecycle: an identity mismatch on ``start`` must not mark a real,
        in-progress call as completed.
        """
        self._finalized = True
        _ACTIVE_STREAMS.pop(self._provider_call_id, None)
        await self.close()

    async def _finalize_and_close(self) -> None:
        await self._finalize()
        await self.close()

    async def _finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True

        if self._session is not None:
            try:
                await self._session.stop()
            except Exception:
                logger.exception("Session stop failed for call %s", self._provider_call_id)

        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except (asyncio.CancelledError, Exception):
                pass
            self._heartbeat_task = None

        _ACTIVE_STREAMS.pop(self._provider_call_id, None)

        if self._provider_call_id and not self._skip_completion:
            await database_sync_to_async(apply_provider_status)(
                self._provider_call_id, "completed"
            )