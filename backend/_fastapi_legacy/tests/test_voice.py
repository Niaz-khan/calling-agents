from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.voice.stt import OpenAISTTProvider, _content_type_to_filename
from app.voice.tts import OpenAITTSProvider


class TestOpenAISTTProvider:
    def _provider(self, **overrides) -> OpenAISTTProvider:
        client_kwargs = {
            "audio": SimpleNamespace(transcriptions=SimpleNamespace(create=AsyncMock())),
        }
        client = SimpleNamespace(**client_kwargs, **overrides)
        return OpenAISTTProvider(client=client, model="whisper-1")

    @pytest.mark.asyncio
    async def test_transcribe_returns_text(self):
        provider = self._provider()
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text=" Book my appointment for Friday "
        )

        result = await provider.transcribe(b"\x00\x01audio", content_type="audio/wav")

        assert result.transcript == "Book my appointment for Friday"
        assert result.is_final is True

        provider._client.audio.transcriptions.create.assert_awaited_once_with(
            model="whisper-1",
            file=("audio.wav", b"\x00\x01audio", "audio/wav"),
            language=None,
        )

    @pytest.mark.asyncio
    async def test_transcribe_uses_provider_language(self):
        provider = OpenAISTTProvider(
            client=SimpleNamespace(
                audio=SimpleNamespace(
                    transcriptions=SimpleNamespace(create=AsyncMock())
                )
            ),
            model="whisper-1",
            language="en",
        )
        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="Hello"
        )

        await provider.transcribe(b"audio", content_type="audio/webm")

        args = provider._client.audio.transcriptions.create.await_args.kwargs
        assert args["language"] == "en"
        assert args["file"][0] == "audio.webm"

    @pytest.mark.asyncio
    async def test_transcribe_stream_yields_final_result(self):
        provider = self._provider()

        async def _chunks():
            yield b"part1"
            yield b"part2"

        provider._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="Hello I am calling"
        )

        results = [r async for r in provider.transcribe_stream(_chunks())]

        assert len(results) >= 1
        assert results[-1].transcript == "Hello I am calling"
        assert results[-1].is_final is True

    def test_content_type_to_filename(self):
        assert _content_type_to_filename("audio/wav") == "audio.wav"
        assert _content_type_to_filename("audio/webm") == "audio.webm"
        assert _content_type_to_filename("audio/mpeg") == "audio.mp3"


class TestOpenAITTSProvider:
    def _provider(self, **overrides) -> OpenAITTSProvider:
        client = SimpleNamespace(
            audio=SimpleNamespace(speech=SimpleNamespace(create=AsyncMock())),
            **overrides,
        )
        return OpenAITTSProvider(client=client)

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_bytes(self):
        provider = self._provider()
        provider._client.audio.speech.create.return_value = SimpleNamespace(
            content=b"RIFF........WAVE"
        )

        result = await provider.synthesize("Hello, how can I help you?")

        assert result.audio == b"RIFF........WAVE"
        assert result.content_type == "audio/wav"
        provider._client.audio.speech.create.assert_awaited_once_with(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input="Hello, how can I help you?",
            response_format="wav",
            speed=1.0,
        )

    @pytest.mark.asyncio
    async def test_synthesize_honors_voice_and_speed(self):
        provider = self._provider()
        provider._client.audio.speech.create.return_value = SimpleNamespace(
            content=b"audiodata"
        )

        await provider.synthesize("Hi", voice="nova", speed=1.25)

        args = provider._client.audio.speech.create.await_args.kwargs
        assert args["voice"] == "nova"
        assert args["speed"] == 1.25