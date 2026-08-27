from openai import AsyncOpenAI

from app.config import settings
from app.voice.base import TTSResult, TextToSpeechProvider


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
    if settings.tts_provider != "openai":
        raise ValueError(f"Unsupported TTS provider: {settings.tts_provider}")

    client_kwargs = {"api_key": settings.llm_api_key}

    if settings.llm_base_url:
        client_kwargs["base_url"] = settings.llm_base_url

    client = AsyncOpenAI(**client_kwargs)

    return OpenAITTSProvider(
        client=client,
        model=settings.tts_model,
        voice=settings.tts_voice,
        response_format=settings.tts_format,
    )