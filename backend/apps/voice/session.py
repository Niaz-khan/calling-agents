"""Transport-agnostic voice session engine.

Pipeline:

    audio -> STT -> agent turn -> TTS -> audio

The engine is not tied to Twilio or any websocket transport. It drives the
existing text AI agent (``conversations.services.run_agent_turn``) so phone
calls persist the exact same message/transcript/tool history as chat.
"""

import asyncio
from dataclasses import dataclass

from apps.conversations.services import run_agent_turn

from .base import SpeechToTextProvider, TextToSpeechProvider


@dataclass
class VoiceTurnResult:
    user_text: str
    assistant_text: str
    audio: bytes
    content_type: str


class UtteranceBuffer:
    """Accumulates raw audio payloads until end-of-speech is signalled."""

    def __init__(self, max_bytes: int | None = None):
        self._buffer = bytearray()
        self._max_bytes = max_bytes

    def append(self, chunk: bytes) -> None:
        if not chunk:
            return

        if self._max_bytes is not None and len(self._buffer) + len(chunk) > self._max_bytes:
            raise ValueError("Utterance exceeds maximum buffer size")

        self._buffer.extend(chunk)

    @property
    def size(self) -> int:
        return len(self._buffer)

    def snapshot(self) -> bytes:
        return bytes(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


class VoiceSessionEngine:
    def __init__(
        self,
        conversation,
        agent,
        stt_provider: SpeechToTextProvider,
        tts_provider: TextToSpeechProvider,
    ):
        self._conversation = conversation
        self._agent = agent
        self._stt = stt_provider
        self._tts = tts_provider

    @property
    def conversation(self):
        return self._conversation

    @property
    def agent(self):
        return self._agent

    async def tts_synthesize(self, text: str) -> TTSResult:
        """Synthesize text directly (opening greeting, no agent turn)."""
        return await self._tts.synthesize(text)

    async def process_text(self, text: str) -> VoiceTurnResult:
        """Run a full agent turn from text (used for DTMF keypad input)."""
        transcript = (text or "").strip()

        if not transcript:
            return VoiceTurnResult(
                user_text="", assistant_text="", audio=b"", content_type=""
            )

        return await self._turn_from_text(transcript)

    async def process_utterance(
        self,
        audio: bytes,
        *,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> VoiceTurnResult:
        stt_result = await self._stt.transcribe(
            audio, content_type=content_type, language=language
        )

        transcript = stt_result.transcript.strip()

        if not transcript:
            return VoiceTurnResult(
                user_text="",
                assistant_text="",
                audio=b"",
                content_type="",
            )

        return await self._turn_from_text(transcript)

    async def _turn_from_text(self, transcript: str) -> VoiceTurnResult:
        # The agent turn uses sync Django DB access, so it must run in a
        # worker thread when called from an async transport.
        result = await asyncio.to_thread(
            run_agent_turn, self._conversation, self._agent, transcript
        )

        assistant_text = (result.response or "").strip()

        if not assistant_text:
            return VoiceTurnResult(
                user_text=transcript,
                assistant_text="",
                audio=b"",
                content_type="",
            )

        tts_result = await self._tts.synthesize(assistant_text)

        return VoiceTurnResult(
            user_text=transcript,
            assistant_text=assistant_text,
            audio=tts_result.audio,
            content_type=tts_result.content_type,
        )