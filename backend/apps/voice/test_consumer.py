"""WebSocket integration tests for the Twilio media-stream consumer."""

import asyncio
import base64
import json
import struct
from types import SimpleNamespace

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import override_settings

from apps.agents.models import Agent
from apps.conversations.models import (
    Conversation,
    ConversationMessage,
    PhoneCall,
    PhoneCallStatus,
)

from .base import STTResult, TTSResult
from .codec import (
    PCM_SAMPLE_RATE,
    decode_alaw,
    encode_alaw,
    encode_mulaw,
    wrap_wav,
)
from .consumers import _ACTIVE_STREAMS, TwilioMediaStreamConsumer

pytestmark = pytest.mark.django_db(transaction=True)

APPLICATION = TwilioMediaStreamConsumer.as_asgi()


def _pcm(amplitude: int, seconds: float) -> bytes:
    count = int(PCM_SAMPLE_RATE * seconds)
    samples = [amplitude if index % 2 == 0 else -amplitude for index in range(count)]
    return struct.pack(f"<{count}h", *samples)


def _wav() -> bytes:
    return wrap_wav(_pcm(6000, 0.1))


def _make_agent(org, name="StreamAgent"):
    return Agent.objects.create(organization=org, name=name, system_prompt="p")


def _stream_conversation(org, agent, call_sid, token):
    conversation = Conversation.objects.create(organization=org, agent=agent)
    PhoneCall.objects.create(
        conversation=conversation,
        phone_number=None,
        provider_call_id=call_sid,
        provider_status=PhoneCallStatus.IN_PROGRESS,
        stream_token=token,
    )
    conversation.refresh_from_db()
    return conversation


class FakeSTT:
    async def transcribe(self, audio, *, content_type="audio/wav", language=None):
        return STTResult(transcript="book my appointment")


class FakeTTS:
    async def synthesize(self, text, *, voice=None, speed=1.0):
        return TTSResult(audio=_wav(), content_type="audio/wav")


def _patch_providers(monkeypatch, *, turns=None, finalize=None):
    monkeypatch.setattr("apps.voice.consumers.get_stt_provider", lambda: FakeSTT())
    monkeypatch.setattr("apps.voice.consumers.get_tts_provider", lambda: FakeTTS())

    if turns is not None:
        monkeypatch.setattr(
            "apps.voice.session.run_agent_turn",
            lambda c, a, t: turns.append(t) or SimpleNamespace(response="Done."),
        )

    if finalize is not None:
        monkeypatch.setattr("apps.telephony.services.finalize_call", finalize)


def _start_message(call_sid, stream_sid="MS1", encoding="audio/x-mulaw"):
    return {
        "event": "start",
        "streamSid": stream_sid,
        "callSid": call_sid,
        "mediaFormat": {"encoding": encoding},
    }


def _media_message(pcm_bytes):
    # Twilio ships the μ-law payload as base64 text, exactly like the consumer
    # receives it in production.
    payload = base64.b64encode(pcm_bytes).decode("ascii")
    return {"event": "media", "media": {"payload": payload}}


async def _wait_until(predicate, timeout=4.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.05)
    return False


async def _wait_closed(communicator, timeout=4.0):
    while True:
        try:
            message = await communicator.receive_output(timeout=timeout)
        except asyncio.TimeoutError:
            return None
        if message is None or message.get("type") == "websocket.close":
            return message


async def _read_media_frames(communicator, want, timeout=4.0):
    # The test communicator cancels the application on a timed-out receive, so
    # each wait uses the full remaining budget instead of short polls.
    frames = []
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline and len(frames) < want:
        remaining = max(0.05, deadline - asyncio.get_event_loop().time())
        try:
            message = await communicator.receive_output(timeout=remaining)
        except asyncio.TimeoutError:
            break
        if message is None:
            break
        if message.get("type") != "websocket.send":
            continue
        data = json.loads(message["text"])
        if data.get("event") == "media":
            frames.append(data)
    return frames


async def _conversation_state(conversation_id):
    def read():
        conversation = Conversation.objects.get(id=conversation_id)
        return conversation.status, conversation.phone_call.provider_status

    return await database_sync_to_async(read)()


async def _message_roles(conversation_id, min_count=4, timeout=5.0):
    """Poll persisted conversation messages until ``min_count`` rows exist."""
    deadline = asyncio.get_event_loop().time() + timeout
    roles = []
    while asyncio.get_event_loop().time() < deadline:
        roles = await database_sync_to_async(
            lambda: list(
                ConversationMessage.objects.filter(conversation_id=conversation_id)
                .order_by("id")
                .values_list("role", flat=True)
            )
        )()
        if len(roles) >= min_count:
            return roles
        await asyncio.sleep(0.05)
    return roles or []


async def _cleanup_db() -> None:
    """Release any connection the asgiref worker thread opened on the test DB.

    Without this, the idle worker session blocks pytest's test-database drop.
    """

    def close():
        from django.db import connections

        connections.close_all()

    await database_sync_to_async(close)()


def test_consumer_requires_token():
    async def scenario():
        communicator = WebsocketCommunicator(APPLICATION, "/telephony/twilio/media")
        connected, _ = await communicator.connect()
        return connected

    assert asyncio.run(scenario()) is False


def test_consumer_rejects_unknown_token():
    async def scenario():
        communicator = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=bogus"
        )
        connected, code = await communicator.connect()
        await _cleanup_db()
        return connected, code

    connected, code = asyncio.run(scenario())
    assert connected is False
    assert code == 4403


def test_consumer_rejects_duplicate_stream(tenant):
    _, org, _ = tenant
    agent = _make_agent(org)
    _stream_conversation(org, agent, "CA-1", "tok-dupe")

    async def scenario():
        first = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-dupe"
        )
        second = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-dupe"
        )

        connected_a, *_ = await first.connect()
        connected_b, code_b = await second.connect()

        await first.send_json_to({"event": "stop"})
        await _wait_closed(first)
        await _cleanup_db()
        return connected_a, connected_b, code_b

    connected_a, connected_b, code_b = asyncio.run(scenario())
    assert connected_a is True
    assert connected_b is False
    assert code_b == 4401


def test_consumer_rejects_start_with_wrong_callsid(tenant, stranger, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    _stream_conversation(org, agent, "CA-A", "tok-a")

    _, other_org, _ = stranger
    other_agent = _make_agent(other_org, "Rival")
    _stream_conversation(other_org, other_agent, "CA-B", "tok-b")

    _patch_providers(monkeypatch, turns=[])

    async def scenario():
        communicator = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-a"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to(_start_message("CA-B"))
        await _wait_closed(communicator)

        status, provider = await _conversation_state(conversation_a_id)
        await _cleanup_db()
        return status, provider

    conversation_a_id = Conversation.objects.get(
        phone_call__provider_call_id="CA-A"
    ).id
    status, provider = asyncio.run(scenario())
    # A rogue start must not touch the real call's lifecycle.
    assert status == "OPEN"
    assert provider == PhoneCallStatus.IN_PROGRESS


def test_consumer_happy_path_streams_and_finalizes(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _stream_conversation(org, agent, "CA-OK", "tok-ok")
    turns = []

    def finalize(conversation):
        conversation.summary = "handled over stream"
        conversation.save(update_fields=["summary"])
        return conversation

    _patch_providers(monkeypatch, turns=turns, finalize=finalize)

    async def scenario():
        communicator = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-ok"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to(_start_message("CA-OK"))

        greeting = await _read_media_frames(communicator, 1)
        assert greeting, "expected greeting audio out"

        status, provider = await _conversation_state(conversation.id)
        assert provider == PhoneCallStatus.IN_PROGRESS
        assert status == "OPEN"

        payload = encode_mulaw(_pcm(9000, 0.2) + _pcm(0, 1.0))
        await communicator.send_json_to(_media_message(payload))

        await _wait_until(lambda: bool(turns))
        assert turns == ["book my appointment"]

        reply_frames = await _read_media_frames(communicator, 1, timeout=4.0)
        assert reply_frames, "expected reply audio out"

        await communicator.send_json_to({"event": "stop"})
        await _wait_closed(communicator)

        _ACTIVE_STREAMS.pop("CA-OK", None)
        result = await _conversation_state(conversation.id)
        await _cleanup_db()
        return result

    status, provider = asyncio.run(scenario())
    assert status == "CLOSED"
    assert provider == PhoneCallStatus.COMPLETED


def test_consumer_heartbeat_marks(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    _stream_conversation(org, agent, "CA-HB", "tok-hb")
    _patch_providers(monkeypatch, turns=[])

    async def scenario():
        with override_settings(VOICE_HEARTBEAT_SECONDS=1):
            communicator = WebsocketCommunicator(
                APPLICATION, "/telephony/twilio/media?token=tok-hb"
            )
            connected, _ = await communicator.connect()
            await communicator.send_json_to(_start_message("CA-HB"))

            # Note: the test communicator cancels the application on a timed-out
            # receive, so read with generous timeouts until the heartbeat mark
            # arrives (or the stream clearly fails).
            for _ in range(6):
                message = await communicator.receive_output(timeout=2.0)
                if message is None:
                    break
                if message.get("type") != "websocket.send":
                    continue
                data = json.loads(message["text"])
                if data.get("event") == "mark" and data.get("mark", {}).get("name") == "heartbeat":
                    await communicator.send_json_to({"event": "stop"})
                    await _wait_closed(communicator)
                    await _cleanup_db()
                    return True

            await communicator.send_json_to({"event": "stop"})
            await _wait_closed(communicator)
            await _cleanup_db()
            return False

    assert asyncio.run(scenario()) is True


def test_consumer_negotiates_alaw_and_streams_reply(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    _stream_conversation(org, agent, "CA-AL", "tok-al")
    turns = []
    _patch_providers(monkeypatch, turns=turns)

    async def scenario():
        communicator = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-al"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to(
            _start_message("CA-AL", "MS-AL", encoding="audio/x-alaw")
        )
        greeting = await _read_media_frames(communicator, 1)
        assert greeting, "expected greeting audio out"

        utterance = encode_alaw(_pcm(9000, 0.2) + _pcm(0, 1.0))
        await communicator.send_json_to(_media_message(utterance))

        await _wait_until(lambda: bool(turns))
        assert turns == ["book my appointment"]

        reply_frames = await _read_media_frames(communicator, 1, timeout=4.0)
        assert reply_frames, "expected reply audio out"
        payload = base64.b64decode(reply_frames[0]["media"]["payload"])
        assert decode_alaw(payload), "reply should be valid A-law audio"

        await communicator.send_json_to({"event": "stop"})
        await _wait_closed(communicator)
        _ACTIVE_STREAMS.pop("CA-AL", None)
        await _cleanup_db()

    asyncio.run(scenario())


def test_consumer_dtmf_triggers_turn(tenant, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    _stream_conversation(org, agent, "CA-DT", "tok-dt")
    turns = []
    _patch_providers(monkeypatch, turns=turns)

    async def scenario():
        communicator = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-dt"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to(_start_message("CA-DT", "MS-DT"))
        greeting = await _read_media_frames(communicator, 1)
        assert greeting, "expected greeting audio out"

        await communicator.send_json_to({"event": "dtmf", "dtmf": {"digit": "1"}})

        await _wait_until(lambda: "1" in turns)
        assert "1" in turns

        reply_frames = await _read_media_frames(communicator, 1, timeout=4.0)
        assert reply_frames, "expected reply audio out"

        await communicator.send_json_to({"event": "stop"})
        await _wait_closed(communicator)
        _ACTIVE_STREAMS.pop("CA-DT", None)
        await _cleanup_db()

    asyncio.run(scenario())


def test_consumer_persists_messages_and_tool_results(tenant, monkeypatch):
    """Exercise the shared agent path (run_agent_turn -> tools -> messages)."""
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _stream_conversation(org, agent, "CA-PT", "tok-pt")

    calls = iter(
        [
            {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "check_appointment_availability",
                            "arguments": json.dumps(
                                {
                                    "start_time": "2026-08-31T15:00:00",
                                    "end_time": "2026-08-31T15:30:00",
                                }
                            ),
                        },
                    }
                ],
            },
            {"content": "3 PM is available tomorrow.", "tool_calls": []},
        ]
    )

    def fake_provider(messages, tools=None):
        return next(calls)

    from apps.conversations.services import run_agent_turn as real_run_agent_turn

    def run_and_close(conversation, agent, transcript):
        try:
            return real_run_agent_turn(conversation, agent, transcript)
        finally:
            from django.db import connections

            connections.close_all()

    monkeypatch.setattr("apps.ai.agent.generate_response", fake_provider)
    monkeypatch.setattr("apps.voice.session.run_agent_turn", run_and_close)
    monkeypatch.setattr("apps.voice.consumers.get_stt_provider", lambda: FakeSTT())
    monkeypatch.setattr("apps.voice.consumers.get_tts_provider", lambda: FakeTTS())
    monkeypatch.setattr("apps.telephony.services.finalize_call", lambda c: c)

    async def scenario():
        communicator = WebsocketCommunicator(
            APPLICATION, "/telephony/twilio/media?token=tok-pt"
        )
        connected, _ = await communicator.connect()
        assert connected is True

        await communicator.send_json_to(_start_message("CA-PT", "MS-PT"))
        greeting = await _read_media_frames(communicator, 1)
        assert greeting, "expected greeting audio out"

        utterance = encode_mulaw(_pcm(9000, 0.2) + _pcm(0, 1.0))
        await communicator.send_json_to(_media_message(utterance))

        roles = await _message_roles(conversation.id)
        assert roles == ["USER", "ASSISTANT", "TOOL", "ASSISTANT"]

        reply_frames = await _read_media_frames(communicator, 1, timeout=4.0)
        assert reply_frames, "expected reply audio out"

        await communicator.send_json_to({"event": "stop"})
        await _wait_closed(communicator)
        _ACTIVE_STREAMS.pop("CA-PT", None)
        await _cleanup_db()

    asyncio.run(scenario())