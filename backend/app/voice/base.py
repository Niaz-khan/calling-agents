from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class STTResult:
    transcript: str
    is_final: bool = True
    confidence: float | None = None
    language: str | None = None
    duration_ms: int | None = None


@dataclass
class TTSResult:
    audio: bytes
    content_type: str = "audio/wav"
    duration_ms: int | None = None


class SpeechToTextProvider(Protocol):
    async def transcribe(
        self,
        audio: bytes,
        *,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> STTResult:
        """Transcribe a single full audio utterance to text."""
        ...

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[bytes],
        *,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> AsyncIterator[STTResult]:
        """Transcribe a stream of audio chunks, yielding results per utterance."""
        ...


class TextToSpeechProvider(Protocol):
    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Synthesize text into audio bytes."""
        ...