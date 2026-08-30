"""Speech-to-text provider (OpenAI-compatible, works with Groq whisper)."""

from typing import AsyncIterator

from django.conf import settings
from openai import AsyncOpenAI

from .base import STTResult, SpeechToTextProvider


def _content_type_to_filename(content_type: str) -> str:
    extension = content_type.split("/")[-1] or "wav"

    if extension == "mpeg":
        extension = "mp3"

    return f"audio.{extension}"


class OpenAISTTProvider:
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = "whisper-1",
        language: str | None = None,
    ):
        self._client = client
        self._model = model
        self._language = language

    async def _transcribe_buffer(
        self,
        audio: bytes,
        content_type: str,
        language: str | None,
    ) -> str:
        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=(
                _content_type_to_filename(content_type),
                audio,
                content_type,
            ),
            language=language or self._language,
        )

        return (response.text or "").strip()

    async def transcribe(
        self,
        audio: bytes,
        *,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> STTResult:
        transcript = await self._transcribe_buffer(audio, content_type, language)

        return STTResult(transcript=transcript)

    async def transcribe_stream(
        self,
        chunks: AsyncIterator[bytes],
        *,
        content_type: str = "audio/wav",
        language: str | None = None,
    ) -> AsyncIterator[STTResult]:
        buffer = bytearray()
        transcribed = False

        async for chunk in chunks:
            if not chunk:
                continue

            buffer.extend(chunk)
            transcript = await self._transcribe_buffer(
                bytes(buffer), content_type, language
            )

            if transcript:
                transcribed = True
                yield STTResult(transcript=transcript)

        if buffer and not transcribed:
            transcript = await self._transcribe_buffer(
                bytes(buffer), content_type, language
            )

            if transcript:
                yield STTResult(transcript=transcript, is_final=True)


def get_stt_provider() -> SpeechToTextProvider:
    if settings.STT_PROVIDER != "openai":
        raise ValueError(f"Unsupported STT provider: {settings.STT_PROVIDER}")

    client_kwargs = {"api_key": settings.STT_API_KEY or settings.LLM_API_KEY}

    base_url = settings.STT_BASE_URL or settings.LLM_BASE_URL
    if base_url:
        client_kwargs["base_url"] = base_url

    client = AsyncOpenAI(**client_kwargs)

    return OpenAISTTProvider(
        client=client,
        model=settings.STT_MODEL,
        language=settings.STT_LANGUAGE,
    )