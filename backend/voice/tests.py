import asyncio
from types import SimpleNamespace

import pytest
from django.test import override_settings

from .base import STTResult, TTSResult
from .stt import get_stt_provider
from .tts import get_tts_provider

pytestmark = pytest.mark.django_db


def test_utterance_buffer():
    from .session import UtteranceBuffer

    buffer = UtteranceBuffer()
    buffer.append(b"ab")
    buffer.append(b"cd")
    assert buffer.size == 4
    assert buffer.snapshot() == b"abcd"
    buffer.clear()
    assert buffer.size == 0
    buffer.append(b"")
    assert buffer.size == 0


def test_utterance_buffer_max_bytes():
    from .session import UtteranceBuffer

    buffer = UtteranceBuffer(max_bytes=3)
    buffer.append(b"ab")
    with pytest.raises(ValueError):
        buffer.append(b"cd")


class FakeSTT:
    def __init__(self, transcript="I need an appointment."):
        self.transcript = transcript

    async def transcribe(self, audio, *, content_type="audio/wav", language=None):
        return STTResult(transcript=self.transcript)


class FakeTTS:
    async def synthesize(self, text, *, voice=None, speed=1.0):
        return TTSResult(audio=b"<audio>", content_type="audio/mpeg")


def _engine(stt=None, tts=None):
    from .session import VoiceSessionEngine

    return VoiceSessionEngine(
        conversation=SimpleNamespace(id=1),
        agent=SimpleNamespace(id=2),
        stt_provider=stt or FakeSTT(),
        tts_provider=tts or FakeTTS(),
    )


def test_engine_full_turn(monkeypatch):
    calls = []

    def fake_turn(conversation, agent, text):
        calls.append((conversation.id, agent.id, text))
        return SimpleNamespace(response="3 PM is available. Book it?")

    monkeypatch.setattr("voice.session.run_agent_turn", fake_turn)

    result = asyncio.run(_engine().process_utterance(b"audio"))

    assert result.user_text == "I need an appointment."
    assert result.assistant_text == "3 PM is available. Book it?"
    assert result.audio == b"<audio>"
    assert result.content_type == "audio/mpeg"
    assert calls == [(1, 2, "I need an appointment.")]


def test_engine_empty_transcript_skips_agent(monkeypatch):
    called = []
    monkeypatch.setattr(
        "voice.session.run_agent_turn",
        lambda c, a, t: called.append(t),
    )

    result = asyncio.run(_engine(stt=FakeSTT(transcript="   ")).process_utterance(b"audio"))

    assert result.user_text == ""
    assert result.assistant_text == ""
    assert result.audio == b""
    assert called == []


def test_engine_empty_reply_skips_tts(monkeypatch):
    monkeypatch.setattr(
        "voice.session.run_agent_turn",
        lambda c, a, t: SimpleNamespace(response="   "),
    )
    tts_calls = []

    class CountingTTS(FakeTTS):
        async def synthesize(self, text, *, voice=None, speed=1.0):
            tts_calls.append(text)
            return TTSResult(audio=b"<audio>", content_type="audio/mpeg")

    result = asyncio.run(_engine(tts=CountingTTS()).process_utterance(b"audio"))

    assert result.audio == b""
    assert tts_calls == []


def test_engine_processes_language_content_type(monkeypatch):
    class Stt:
        def __init__(self):
            self.seen = None

        async def transcribe(self, audio, *, content_type="audio/wav", language=None):
            self.seen = (content_type, language)
            return STTResult(transcript="hi")

    monkeypatch.setattr(
        "voice.session.run_agent_turn",
        lambda c, a, t: SimpleNamespace(response="ok"),
    )

    stt = Stt()
    asyncio.run(_engine(stt=stt).process_utterance(b"x", content_type="audio/mp3", language="en"))
    assert stt.seen == ("audio/mp3", "en")


def test_get_stt_provider_dispatch():
    with override_settings(
        STT_PROVIDER="openai",
        STT_API_KEY="key",
        STT_BASE_URL="https://api.groq.com/openai/v1",
        STT_MODEL="whisper-large-v3-turbo",
    ):
        provider = get_stt_provider()

    assert provider._model == "whisper-large-v3-turbo"
    assert provider._language is None
    assert str(provider._client.base_url) == "https://api.groq.com/openai/v1/"

    with override_settings(STT_PROVIDER="bogus"):
        with pytest.raises(ValueError):
            get_stt_provider()


def test_get_tts_provider_dispatch():
    with override_settings(TTS_PROVIDER="edge", TTS_VOICE="en-US-AriaNeural"):
        provider = get_tts_provider()

    assert provider._voice == "en-US-AriaNeural"

    with override_settings(TTS_PROVIDER="openai", TTS_API_KEY="x"):
        provider = get_tts_provider()

    assert provider._model == "en-US-JennyNeural"
    assert provider._voice == "en-US-JennyNeural"
    assert provider._response_format == "mp3"

    with override_settings(TTS_PROVIDER="bogus"):
        with pytest.raises(ValueError):
            get_tts_provider()