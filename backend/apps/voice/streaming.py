"""Bidirectional audio streaming session for telephony media streams.

Twilio streams the call's audio as 8 kHz mono G.711. ``UtteranceDetector``
segments the incoming PCM16 into spoken utterances (energy threshold + trailing
silence), and ``StreamingVoiceSession`` runs each utterance through the *same*
``VoiceSessionEngine`` the transport-agnostic path uses (STT -> agent turn ->
TTS), transcodes the reply to the wire codec, and paces it back to the caller
in ~100 ms chunks so the caller can barge in at any moment.

The session is transport-neutral: the websocket consumer supplies async
callbacks for outgoing audio, ``clear`` (barge-in), ending, and transferring.
The session owns all call-state logic (barge-in interruption, pending-response
queue, max duration, idle timeout, transfer detection).
"""

import asyncio
import logging
import math
import time
from collections import deque

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils import timezone

from apps.conversations.models import ConversationStatus, PhoneCallStatus

from .codec import PCM_SAMPLE_RATE, transcode_audio_to_codec, wrap_wav

logger = logging.getLogger(__name__)

FRAME_MS = 20
FRAME_SAMPLES = PCM_SAMPLE_RATE * FRAME_MS // 1000  # 160
PRE_ROLL_MS = 200
MIN_SPEECH_MS = 50
PLAYBACK_CHUNK_MS = 100


def _frame_rms(frame: bytes) -> float:
    """Root-mean-square energy of a little-endian PCM16 frame."""
    count = len(frame) // 2
    if count == 0:
        return 0.0
    total = 0
    for index in range(count):
        sample = int.from_bytes(frame[index * 2:index * 2 + 2], "little", signed=True)
        total += sample * sample
    return math.sqrt(total / count)


class UtteranceDetector:
    """Energy-based endpointing for a continuous G.711 audio stream.

    Twilio pushes *continuous* audio (including silence), so instead of
    treating every frame as an utterance we keep a short rolling pre-roll, mark
    speech once frame energy clears ``speech_threshold``, keep collecting until
    the caller has been quiet for ``end_silence_seconds`` (or the utterance
    exceeds ``max_utterance_seconds``), and then emit the finished utterance as
    PCM16.
    """

    def __init__(
        self,
        *,
        speech_threshold: int | None = None,
        end_silence_seconds: float | None = None,
        max_utterance_seconds: int | None = None,
    ):
        self.speech_threshold = (
            speech_threshold
            if speech_threshold is not None
            else settings.VOICE_STREAM_SPEECH_THRESHOLD
        )
        self.end_silence_seconds = (
            end_silence_seconds
            if end_silence_seconds is not None
            else settings.VOICE_STREAM_END_SILENCE_SECONDS
        )
        self.max_utterance_seconds = (
            max_utterance_seconds
            if max_utterance_seconds is not None
            else settings.VOICE_MAX_UTTERANCE_SECONDS
        )

        self._silence_frames_required = max(
            1, int(1000 * self.end_silence_seconds / FRAME_MS)
        )
        self._min_speech_frames = max(1, MIN_SPEECH_MS // FRAME_MS)
        self._max_speech_frames = max(
            self._min_speech_frames,
            int(1000 * self.max_utterance_seconds / FRAME_MS),
        )

        self._pre_roll = deque(maxlen=max(1, PRE_ROLL_MS // FRAME_MS))
        self._speech = bytearray()
        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speaking = False
        self._utterances: deque[bytes] = deque()
        self._residual = bytearray()
        self._utterance_head = b""

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def has_utterances(self) -> bool:
        return bool(self._utterances)

    def feed(self, pcm: bytes) -> None:
        """Consume a chunk of PCM16, splitting it into frames as needed."""
        if not pcm:
            return

        self._residual.extend(pcm)

        while len(self._residual) >= FRAME_SAMPLES * 2:
            frame = bytes(self._residual[: FRAME_SAMPLES * 2])
            del self._residual[: FRAME_SAMPLES * 2]
            self._feed_frame(frame)

    def _feed_frame(self, frame: bytes) -> None:
        speech = _frame_rms(frame) >= self.speech_threshold

        if speech:
            if self._is_speaking:
                self._speech.extend(frame)
                self._speech_frames += 1
                if self._speech_frames >= self._max_speech_frames:
                    self._emit_current()
            else:
                self._utterance_head = b"".join(self._pre_roll)
                self._is_speaking = True
                self._speech.clear()
                self._speech.extend(frame)
                self._speech_frames = 1
                self._silence_frames = 0
        else:
            if self._is_speaking:
                self._silence_frames += 1
                if self._silence_frames >= self._silence_frames_required:
                    self._emit_current()
            else:
                self._pre_roll.append(frame)

    def _emit_current(self) -> None:
        if self._speech_frames < self._min_speech_frames:
            # Sub-threshold blip (cough, keypress); discard to avoid noise.
            self._reset_after_utterance()
            return

        utterance = (self._utterance_head or b"") + bytes(self._speech)
        if utterance:
            self._utterances.append(utterance)
        self._reset_after_utterance()

    def _reset_after_utterance(self) -> None:
        self._speech.clear()
        self._speech_frames = 0
        self._silence_frames = 0
        self._is_speaking = False
        self._utterance_head = b""

    def drain(self) -> list[bytes]:
        utterances = list(self._utterances)
        self._utterances.clear()
        return utterances

    def flush(self) -> bytes | None:
        """Force-emit the in-progress utterance (caller disconnect)."""
        if self._is_speaking:
            self._emit_current()
        if not self._utterances:
            return None
        utterancing = self._utterances[-1]
        self._utterances.clear()
        return utterancing


class StreamingVoiceSession:
    """Drives turns for a single live call over a media websocket.

    A background worker owns the STT/LLM/TTS pipeline so the transport stays
    free to deliver frames while a reply is playing; any speech that starts
    while we are talking (or preparing a reply) marks the current reply stale
    and asks the transport to ``clear`` the playback buffer.
    """

    def __init__(
        self,
        engine,
        *,
        codec: str = "mulaw",
        speech_threshold: int | None = None,
        end_silence_seconds: float | None = None,
        max_utterance_seconds: int | None = None,
        max_duration_seconds: int | None = None,
        idle_timeout_seconds: int | None = None,
        on_audio=None,
        on_clear=None,
        on_end=None,
        on_transfer=None,
    ):
        self._engine = engine
        self._codec = codec
        self._on_audio = on_audio
        self._on_clear = on_clear
        self._on_end = on_end
        self._on_transfer = on_transfer

        self._conversation = engine.conversation
        self._agent = engine.conversation.agent
        self._provider_call_id = engine.conversation.phone_call.provider_call_id

        self._detector = UtteranceDetector(
            speech_threshold=speech_threshold,
            end_silence_seconds=end_silence_seconds,
            max_utterance_seconds=max_utterance_seconds,
        )

        self._pending: deque[tuple[str, bytes | str]] = deque()
        self._wakeup = asyncio.Event()
        self._worker: asyncio.Task | None = None
        self._watchdog: asyncio.Task | None = None
        self._processing = False
        self._playing = False
        self._closed = False

        self._interrupts = 0
        self._last_activity = time.monotonic()

        self._idle_timeout = (
            idle_timeout_seconds
            if idle_timeout_seconds is not None
            else settings.VOICE_IDLE_TIMEOUT_SECONDS
        )
        self._max_duration_seconds = max_duration_seconds
        self._max_until = None
        if self._max_duration_seconds:
            started_at = self._conversation.started_at
            remaining = (
                started_at
                + timezone.timedelta(seconds=self._max_duration_seconds)
                - timezone.now()
            ).total_seconds()
            self._max_until = time.monotonic() + max(0.0, remaining)

        self._transfer_target = (
            self._conversation.organization.transfer_phone_number or ""
        ).strip() or None

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())
        if self._watchdog is None and (self._idle_timeout or self._max_until):
            self._watchdog = asyncio.create_task(self._watch())
        self._note_activity()

    async def stop(self) -> None:
        """Flush remaining speech, cancel background tasks, become inert."""
        if self._closed:
            return

        leftover = self._flush_detector()
        if leftover and not self._processing:
            self._processing = True
            try:
                await self._turn(leftover)
            except Exception:
                logger.exception(
                    "Final utterance processing failed for conversation %s",
                    self._conversation.id,
                )
            finally:
                self._processing = False

        self._closed = True
        self._wakeup.set()
        for task in (self._worker, self._watchdog):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._worker = None
        self._watchdog = None

    # -- inbound (transport calls these) ------------------------------------

    async def handle_media(self, decoded_pcm: bytes) -> None:
        """Consume a decoded PCM16 chunk from the transport (fast path)."""
        was_speaking = self._detector.is_speaking
        self._detector.feed(decoded_pcm)

        for utterance in self._detector.drain():
            if utterance:
                self._pending.append(("audio", utterance))
                self._wakeup.set()

        if (
            self._detector.is_speaking
            and not was_speaking
            and (self._playing or self._processing or self._pending)
        ):
            await self._request_interrupt()

    async def handle_text(self, text: str) -> None:
        """Queue a keypad (DTMF) input as a turn without speech recognition."""
        if not (text or "").strip():
            return
        self._pending.append(("text", (text or "").strip()))
        self._wakeup.set()

    async def greet(self, text: str) -> None:
        """Synthesize and play an opening line (no agent turn)."""
        message = (text or "").strip()
        if not message:
            return
        try:
            result = await self._engine.tts_synthesize(message)
        except Exception:
            logger.exception("Greeting synthesis failed for conversation %s", self._conversation.id)
            return
        if result.audio:
            await self._play(result)
        self._note_activity()

    # -- worker -------------------------------------------------------------

    async def _run(self) -> None:
        while not self._closed:
            await self._wakeup.wait()
            self._wakeup.clear()

            if self._closed:
                return

            while self._pending and not self._closed:
                kind, payload = self._pending.popleft()
                self._processing = True
                try:
                    if kind == "text":
                        await self._turn(payload, from_dtmf=True)
                    else:
                        await self._turn(payload)
                    if self._closed:
                        return
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "Turn failed for conversation %s", self._conversation.id
                    )
                finally:
                    self._processing = False

    async def _watch(self) -> None:
        while not self._closed:
            await asyncio.sleep(1)

            if self._idle_timeout and time.monotonic() - self._last_activity > self._idle_timeout:
                logger.info(
                    "Conversation %s ending: idle for %ss",
                    self._conversation.id,
                    self._idle_timeout,
                )
                await self._end("idle")
                return

            if self._max_until and time.monotonic() > self._max_until:
                logger.info(
                    "Conversation %s ending: max duration reached (agent %s)",
                    self._conversation.id,
                    self._agent.id,
                )
                await self._end("max_duration")
                return

    # -- turn pipeline ------------------------------------------------------

    async def _turn(self, utterance_or_text, *, from_dtmf: bool = False) -> None:
        reactions = self._interrupts
        self._note_activity()

        try:
            if from_dtmf:
                result = await self._engine.process_text(utterance_or_text)
            else:
                result = await self._engine.process_utterance(
                    wrap_wav(utterance_or_text), content_type="audio/wav"
                )
        except Exception:
            logger.exception(
                "Agent turn failed for conversation %s", self._conversation.id
            )
            return

        if not result.audio:
            await self._post_turn()
            return

        # The caller spoke again while we were thinking: drop the stale reply.
        if self._interrupts != reactions:
            await self._post_turn()
            return

        try:
            payload = await transcode_audio_to_codec(
                result.audio, result.content_type, self._codec
            )
        except Exception:
            logger.exception(
                "Audio transcoding failed for conversation %s", self._conversation.id
            )
            return

        await self._play(result, payload)
        await self._post_turn()

    async def _play(self, result, payload: bytes | None = None) -> None:
        start = self._interrupts
        self._playing = True
        try:
            if payload is None:
                payload = await transcode_audio_to_codec(
                    result.audio, result.content_type, self._codec
                )
            chunk_bytes = PCM_SAMPLE_RATE * PLAYBACK_CHUNK_MS // 1000  # bytes per 100 ms
            chunk_size = max(1, chunk_bytes)
            for offset in range(0, len(payload), chunk_size):
                if self._interrupts != start:
                    break
                chunk = payload[offset:offset + chunk_size]
                if self._on_audio is not None:
                    await self._on_audio(chunk)
                await asyncio.sleep(PLAYBACK_CHUNK_MS / 1000)
        finally:
            self._playing = False
            self._note_activity()

    async def _request_interrupt(self) -> None:
        self._interrupts += 1
        if self._on_clear is not None:
            await self._on_clear()

    async def _post_turn(self) -> None:
        # ``database_sync_to_async`` runs on the asgiref thread-sensitive thread
        # with its own connection, so this relies on committed data (the normal
        # production state after the caller's transaction completes).
        transferred, closed = await database_sync_to_async(self._refresh_state)()

        if transferred:
            if self._on_transfer is not None:
                await self._on_transfer(self._transfer_target)
            self._closed = True
            return

        if closed:
            await self._end("closed")
            return

    def _refresh_state(self):
        try:
            self._conversation.refresh_from_db(fields=["status"])
            self._conversation.phone_call.refresh_from_db(fields=["provider_status"])
            transferred = (
                self._conversation.phone_call.provider_status == PhoneCallStatus.TRANSFERRED
            )
            closed = self._conversation.status == ConversationStatus.CLOSED
        except Exception:
            logger.exception("State refresh failed for conversation %s", self._conversation.id)
            transferred = False
            closed = False
        return transferred, closed

    async def _end(self, reason: str) -> None:
        if self._closed:
            return
        self._closed = True
        if self._on_end is not None:
            await self._on_end(reason)

    def _note_activity(self) -> None:
        self._last_activity = time.monotonic()

    def _flush_detector(self) -> bytes | None:
        return self._detector.flush()