"""Transport-neutral streaming tests: UtteranceDetector + StreamingVoiceSession."""

import asyncio
import struct
from types import SimpleNamespace

import pytest
from channels.db import database_sync_to_async
from django.utils import timezone

from apps.agents.models import Agent
from apps.conversations.models import (
    Conversation,
    PhoneCall,
    PhoneCallStatus,
)

from .base import STTResult, TTSResult
from .codec import PCM_SAMPLE_RATE, wrap_wav
from .session import VoiceSessionEngine
from .streaming import StreamingVoiceSession, UtteranceDetector


# Utterance-detector tests are pure CPU (no DB). Session tests exercise the
# streaming worker, which touches PostgreSQL on the asgiref thread-sensitive
# connection; they therefore need real commits (transaction=True) so each
# background thread sees the rows the test created.
DB_SESSION = pytest.mark.django_db(transaction=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _pcm(amplitude: int, seconds: float) -> bytes:
    count = int(PCM_SAMPLE_RATE * seconds)
    samples = [amplitude if index % 2 == 0 else -amplitude for index in range(count)]
    return struct.pack(f"<{count}h", *samples)


def _speech(seconds: float = 0.3) -> bytes:
    return _pcm(9000, seconds)


def _silence(seconds: float = 0.3) -> bytes:
    return _pcm(0, seconds)


def _wav(amplitude: int = 6000, seconds: float = 0.3) -> tuple[bytes, bytes]:
    pcm = _pcm(amplitude, seconds)
    return wrap_wav(pcm), pcm


class FakeSTT:
    def __init__(self, transcript="book my appointment"):
        self.transcript = transcript
        self.calls = []

    async def transcribe(self, audio, *, content_type="audio/wav", language=None):
        self.calls.append(audio)
        return STTResult(transcript=self.transcript)


class FakeTTS:
    def __init__(self, long=False):
        self.long = long
        self.texts = []

    async def synthesize(self, text, *, voice=None, speed=1.0):
        self.texts.append(text)
        wav, _ = _wav(seconds=2.0 if self.long else 0.1)
        return TTSResult(audio=wav, content_type="audio/wav")


def _make_agent(org, name="StreamAgent"):
    return Agent.objects.create(organization=org, name=name, system_prompt="p")


def _make_conversation(org, agent, call_sid="CA-STREAM"):
    conversation = Conversation.objects.create(organization=org, agent=agent)
    PhoneCall.objects.create(
        conversation=conversation,
        phone_number=None,
        provider_call_id=call_sid,
        provider_status=PhoneCallStatus.IN_PROGRESS,
    )
    return conversation


def _build_session(
    conversation,
    agent,
    *,
    stt=None,
    tts=None,
    max_duration_seconds=None,
    idle_timeout_seconds=None,
    speech_threshold=1000,
    end_silence_seconds=0.05,
    audio_collector=None,
    clear_collector=None,
):
    engine = VoiceSessionEngine(
        conversation=conversation,
        agent=agent,
        stt_provider=stt or FakeSTT(),
        tts_provider=tts or FakeTTS(),
    )
    return StreamingVoiceSession(
        engine,
        speech_threshold=speech_threshold,
        end_silence_seconds=end_silence_seconds,
        max_duration_seconds=max_duration_seconds,
        idle_timeout_seconds=idle_timeout_seconds,
        on_audio=audio_collector,
        on_clear=clear_collector,
    )


async def _collector(bucket):
    async def collect(payload):
        bucket.append(payload)

    return collect


# ---------------------------------------------------------------------------
# UtteranceDetector
# ---------------------------------------------------------------------------


def make_detector(end_silence=0.05, max_utterance=1.0, threshold=1000):
    return UtteranceDetector(
        speech_threshold=threshold,
        end_silence_seconds=end_silence,
        max_utterance_seconds=max_utterance,
    )


def test_detector_endpoints_single_utterance():
    detector = make_detector(end_silence=0.05)
    detector.feed(_speech(0.2) + _silence(0.3))
    utterances = detector.drain()

    assert len(utterances) == 1
    # pre-roll lead-in + speech, roughly the speech window
    assert len(utterances[0]) / 2 >= int(PCM_SAMPLE_RATE * 0.2)
    assert detector.drain() == []


def test_detector_ignores_quiet_and_suppresses_blips():
    detector = make_detector()
    detector.feed(_silence(1.0))
    assert detector.drain() == []

    detector.feed(_speech(0.02) + _silence(0.5))
    assert detector.drain() == []


def test_detector_forces_utterance_at_max_length():
    detector = make_detector(max_utterance=0.1)
    detector.feed(_speech(1.0))
    utterances = detector.drain()

    assert len(utterances) >= 5
    for utterance in utterances:
        assert len(utterance) / 2 <= int(PCM_SAMPLE_RATE * 0.2)


def test_detector_handles_unaligned_chunks():
    detector = make_detector(end_silence=0.05)
    speech = _speech(0.3)
    silence = _silence(0.3)
    chunk = speech[:600]  # not frame-aligned
    detector.feed(chunk)
    detector.feed(speech[600:] + silence)
    assert len(detector.drain()) == 1


def test_detector_flush_emits_in_progress_speech():
    detector = make_detector()
    detector.feed(_speech(0.5))
    assert detector.is_speaking
    assert detector.flush() is not None


# ---------------------------------------------------------------------------
# StreamingVoiceSession
# ---------------------------------------------------------------------------


@DB_SESSION
def test_session_greets_and_plays(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    out = []

    async def scenario():
        session = _build_session(
            conversation,
            agent,
            tts=FakeTTS(),
            audio_collector=await _collector(out),
        )
        await session.start()
        await session.greet("Welcome!")
        await session.stop()

    asyncio.run(scenario())
    assert out, "expected at least one outbound audio chunk"
    assert len(out[0]) > 0


@DB_SESSION
def test_session_handles_voice_utterance(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    turns = []
    out = []

    monkeypatch.setattr(
        "apps.voice.session.run_agent_turn",
        lambda c, a, t: turns.append(t) or SimpleNamespace(response="Done."),
    )

    async def scenario():
        session = _build_session(
            conversation,
            agent,
            stt=FakeSTT(transcript="book it"),
            audio_collector=await _collector(out),
            end_silence_seconds=0.05,
        )
        await session.start()
        await session.handle_media(_speech(0.2) + _silence(0.3))
        for _ in range(60):
            if turns and out:
                break
            await asyncio.sleep(0.05)
        await session.stop()

    asyncio.run(scenario())
    assert turns == ["book it"]
    assert out, "expected a spoken reply chunk"


@DB_SESSION
def test_session_barge_in_clears_and_skips_stale(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    turns = []
    out = []
    clears = []

    def fake_turn(conversation, agent, text):
        turns.append(text)
        return SimpleNamespace(response="LONG REPLY")

    monkeypatch.setattr("apps.voice.session.run_agent_turn", fake_turn)

    async def on_clear():
        clears.append("clear")

    async def scenario():
        session = _build_session(
            conversation,
            agent,
            stt=FakeSTT(),
            tts=FakeTTS(long=True),
            audio_collector=await _collector(out),
            clear_collector=on_clear,
            end_silence_seconds=0.05,
        )
        await session.start()

        # First long utterance -> long reply starts playing.
        await session.handle_media(_speech(0.2) + _silence(0.3))
        for _ in range(100):
            if turns and out:
                break
            await asyncio.sleep(0.05)
        assert turns and out, "first reply should have started"

        # Caller barges in mid-playback.
        await session.handle_media(_speech(0.2))
        for _ in range(50):
            if clears:
                break
            await asyncio.sleep(0.05)
        assert clears, "expected a clear (barge-in) request"

        # Finish the barge-in utterance; it should be processed after the
        # interrupted reply.
        await session.handle_media(_silence(0.3))
        before = len(turns)
        for _ in range(120):
            if len(turns) > before and len(out) > 2:
                break
            await asyncio.sleep(0.05)
        await session.stop()

    asyncio.run(scenario())
    assert len(turns) >= 2
    assert clears


@DB_SESSION
def test_session_max_duration_ends(tenant):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    conversation.started_at = timezone.now().replace(minute=0) - timezone.timedelta(hours=2)
    conversation.save(update_fields=["started_at"])
    ended = []

    async def scenario():
        session = _build_session(conversation, agent, max_duration_seconds=60)

        async def end(reason):
            ended.append(reason)

        session._on_end = end
        await session.start()
        for _ in range(40):
            if ended:
                break
            await asyncio.sleep(0.1)
        await session.stop()

    asyncio.run(scenario())
    assert ended == ["max_duration"]


@DB_SESSION
def test_session_idle_timeout_ends(tenant):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    ended = []

    async def scenario():
        session = _build_session(conversation, agent, idle_timeout_seconds=1)

        async def end(reason):
            ended.append(reason)

        session._on_end = end
        await session.start()
        for _ in range(30):
            if ended:
                break
            await asyncio.sleep(0.1)
        await session.stop()

    asyncio.run(scenario())
    assert ended == ["idle"]


@DB_SESSION
def test_session_transfer_passthrough(tenant):
    _, org, _ = tenant
    org.transfer_phone_number = "+15550009999"
    org.save(update_fields=["transfer_phone_number"])
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    transfers = []

    def mark_transferred():
        conversation.phone_call.provider_status = PhoneCallStatus.TRANSFERRED
        conversation.phone_call.save(update_fields=["provider_status"])

    async def scenario():
        session = _build_session(
            conversation, agent, end_silence_seconds=0.05
        )

        async def on_transfer(target):
            transfers.append(target)

        session._on_transfer = on_transfer
        await session.start()
        await database_sync_to_async(mark_transferred)()
        await session._post_turn()
        await session.stop()

    asyncio.run(scenario())
    assert transfers == ["+15550009999"]