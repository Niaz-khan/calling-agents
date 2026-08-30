"""Text-to-speech providers.

``edge`` is free and keyless (Microsoft Edge neural voices).
``openai`` targets any OpenAI-compatible TTS endpoint (e.g. gpt-4o-mini-tts).
"""

from django.conf import settings
from openai import AsyncOpenAI

from .base import TTSResult, TextToSpeechProvider


class EdgeTTSProvider:
    def __init__(self, voice: str = "en-US-JennyNeural"):
        self._voice = voice

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        import edge_tts

        communicate = edge_tts.Communicate(
            text,
            voice=voice or self._voice,
            rate=f"{round((speed - 1) * 100):+d}%",
        )

        audio = bytearray()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])

        if not audio:
            raise ValueError("Edge TTS returned no audio")

        return TTSResult(audio=bytes(audio), content_type="audio/mpeg")


class OpenAITTSProvider:
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
        response_format: str = "wav",
    ):
        self._client = client
        self._model = model
        self._voice = voice
        self._response_format = response_format

    async def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> TTSResult:
        response = await self._client.audio.speech.create(
            model=self._model,
            voice=voice or self._voice,
            input=text,
            response_format=self._response_format,
            speed=speed,
        )

        return TTSResult(
            audio=response.content,
            content_type=f"audio/{self._response_format}",
        )


def get_tts_provider() -> TextToSpeechProvider:
    if settings.TTS_PROVIDER == "edge":
        return EdgeTTSProvider(voice=settings.TTS_VOICE)

    if settings.TTS_PROVIDER != "openai":
        raise ValueError(f"Unsupported TTS provider: {settings.TTS_PROVIDER}")

    client_kwargs = {"api_key": settings.TTS_API_KEY or settings.LLM_API_KEY}

    base_url = settings.TTS_BASE_URL or settings.LLM_BASE_URL
    if base_url:
        client_kwargs["base_url"] = base_url

    client = AsyncOpenAI(**client_kwargs)

    return OpenAITTSProvider(
        client=client,
        model=settings.TTS_MODEL,
        voice=settings.TTS_VOICE,
        response_format=settings.TTS_FORMAT,
    )