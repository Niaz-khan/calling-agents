from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.call import Call
from app.services.calls import run_agent_turn
from app.voice.base import STTResult, TTSResult, SpeechToTextProvider, TextToSpeechProvider


@dataclass
class VoiceTurnResult:
    user_text: str
    assistant_text: str
    audio: bytes
    content_type: str


class UtteranceBuffer:
    """Accumulates incoming audio chunks into a single utterance."""

    def __init__(self, max_bytes: int = 5 * 1024 * 1024):
        self._buffer = bytearray()
        self._max_bytes = max_bytes

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    def append(self, chunk: bytes) -> None:
        if len(self._buffer) + len(chunk) > self._max_bytes:
            raise ValueError("Utterance exceeds maximum audio size")

        self._buffer.extend(chunk)

    def clear(self) -> None:
        self._buffer.clear()

    def snapshot(self) -> bytes:
        return bytes(self._buffer)


class VoiceSessionEngine:
    """Runs the voice loop: audio -> STT -> agent -> text -> TTS -> audio.

    Kept transport-agnostic so it can be driven by a WebSocket now and
    a telephony gateway later.
    """

    def __init__(
        self,
        db: Session,
        call: Call,
        agent: Agent,
        stt_provider: SpeechToTextProvider,
        tts_provider: TextToSpeechProvider,
    ):
        self._db = db
        self._call = call
        self._agent = agent
        self._stt = stt_provider
        self._tts = tts_provider

    async def process_utterance(
        self,
        audio: bytes,
        *,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> VoiceTurnResult:
        stt_result = await self._stt.transcribe(
            audio,
            content_type=content_type,
            language=language,
        )

        user_text = stt_result.transcript

        if not user_text:
            raise EmptyUtteranceError("No speech detected")

        agent_result = await run_agent_turn(
            db=self._db,
            call=self._call,
            agent=self._agent,
            user_text=user_text,
        )

        tts_result = await self._tts.synthesize(agent_result.response)

        return VoiceTurnResult(
            user_text=user_text,
            assistant_text=agent_result.response,
            audio=tts_result.audio,
            content_type=tts_result.content_type,
        )

    async def synthesize(self, text: str) -> TTSResult:
        return await self._tts.synthesize(text)

    @property
    def call(self) -> Call:
        return self._call


class EmptyUtteranceError(Exception):
    """Raised when STT produces no recognized speech."""