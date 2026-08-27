import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.agent import AgentResult
from app.auth.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.agent import Agent
from app.models.call import Call, CallDirection, CallStatus
from app.models.call_message import CallMessage, MessageRole
from app.models.user import User
from app.services.calls import build_conversation_history, run_agent_turn
from app.services.voice_session import (
    EmptyUtteranceError,
    UtteranceBuffer,
    VoiceSessionEngine,
)
from app.voice.base import STTResult, TTSResult


class FakeSTT:
    def __init__(self, transcript="Book an appointment for Friday"):
        self._transcript = transcript

    async def transcribe(self, audio, *, content_type="audio/wav", language=None):
        return STTResult(transcript=self._transcript)


class FakeTTS:
    async def synthesize(self, text, *, voice=None, speed=1.0):
        return TTSResult(audio=b"AUDIOWAVEDATA", content_type="audio/wav")


class TestUtteranceBuffer:
    def test_accumulates_and_snapshots(self):
        buffer = UtteranceBuffer()
        assert buffer.is_empty is True

        buffer.append(b"abc")
        buffer.append(b"def")

        assert buffer.is_empty is False
        assert buffer.snapshot() == b"abcdef"

    def test_clear_empties_buffer(self):
        buffer = UtteranceBuffer()
        buffer.append(b"abc")
        buffer.clear()
        assert buffer.is_empty is True
        assert buffer.snapshot() == b""

    def test_rejects_oversized_utterance(self):
        buffer = UtteranceBuffer(max_bytes=4)
        buffer.append(b"abcd")

        with pytest.raises(ValueError):
            buffer.append(b"e")


class TestVoiceSessionEngine:
    @pytest.mark.asyncio
    @patch("app.services.voice_session.run_agent_turn", new_callable=AsyncMock)
    async def test_process_utterance_round_trip(self, mock_turn, db_session, test_agent):
        call = Call(
            agent_id=test_agent.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        agent = db_session.get(Agent, test_agent.id)
        engine = VoiceSessionEngine(
            db=db_session,
            call=call,
            agent=agent,
            stt_provider=FakeSTT(),
            tts_provider=FakeTTS(),
        )

        mock_turn.return_value = AgentResult(
            response="Great! I can book that for you.",
            messages=[],
        )

        turn = await engine.process_utterance(b"\x00\x01audio")

        assert turn.user_text == "Book an appointment for Friday"
        assert turn.assistant_text == "Great! I can book that for you."
        assert turn.audio == b"AUDIOWAVEDATA"
        assert turn.content_type == "audio/wav"

        mock_turn.assert_awaited_once()
        args = mock_turn.await_args.kwargs
        assert args["user_text"] == "Book an appointment for Friday"

    @pytest.mark.asyncio
    async def test_raises_on_empty_transcript(self, db_session, test_agent):
        call = Call(
            agent_id=test_agent.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        agent = db_session.get(Agent, test_agent.id)
        engine = VoiceSessionEngine(
            db=db_session,
            call=call,
            agent=agent,
            stt_provider=FakeSTT(transcript=""),
            tts_provider=FakeTTS(),
        )

        with pytest.raises(EmptyUtteranceError):
            await engine.process_utterance(b"\x00\x01audio")


class TestConversationHistory:
    def test_rebuilds_messages_in_order(self, db_session, test_agent):
        call = Call(
            agent_id=test_agent.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        db_session.add(
            CallMessage(call_id=call.id, role=MessageRole.USER, content="Hi")
        )
        db_session.add(
            CallMessage(
                call_id=call.id,
                role=MessageRole.ASSISTANT,
                content="Hello! How can I help?",
            )
        )
        db_session.commit()

        conversation = build_conversation_history(db_session, call)

        assert conversation[0] == {"role": "user", "content": "Hi"}
        assert conversation[1] == {
            "role": "assistant",
            "content": "Hello! How can I help?",
        }

    def test_skips_customer_memory_system_injection(self, db_session, test_agent, test_user):
        from app.models.customer import Customer

        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
            name="John Doe",
            memory="Customer prefers morning appointments.",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        call = Call(
            agent_id=test_agent.id,
            customer_id=customer.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        db_session.add(
            CallMessage(call_id=call.id, role=MessageRole.USER, content="Hello")
        )
        db_session.commit()

        conversation = build_conversation_history(db_session, call)

        assert conversation[0]["role"] == "system"
        assert "morning appointments" in conversation[0]["content"]
        assert conversation[1] == {"role": "user", "content": "Hello"}

    def test_includes_tool_calls_and_results(self, db_session, test_agent):
        call = Call(
            agent_id=test_agent.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        db_session.add(
            CallMessage(
                call_id=call.id,
                role=MessageRole.ASSISTANT,
                content=json.dumps(
                    {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "check_appointment_availability",
                                    "arguments": "{}",
                                },
                            }
                        ]
                    }
                ),
            )
        )
        db_session.add(
            CallMessage(
                call_id=call.id,
                role=MessageRole.TOOL,
                content='{"available": true}',
                tool_call_id="call_1",
            )
        )
        db_session.commit()

        conversation = build_conversation_history(db_session, call)

        assert conversation[0]["role"] == "assistant"
        assert conversation[0]["tool_calls"][0]["id"] == "call_1"
        assert conversation[1] == {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": '{"available": true}',
        }

    @pytest.mark.asyncio
    @patch("app.services.calls.run_agent", new_callable=AsyncMock)
    async def test_run_agent_turn_persists_user_and_assistant(
        self, mock_run_agent, db_session, test_agent
    ):
        call = Call(
            agent_id=test_agent.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        agent = db_session.get(Agent, test_agent.id)
        mock_run_agent.return_value = AgentResult(
            response="Sure, I can help with that.",
            messages=[
                {
                    "role": "assistant",
                    "content": "tool info",
                    "tool_calls": [],
                }
            ],
        )

        result = await run_agent_turn(db_session, call, agent, "I need an appointment")

        assert result.response == "Sure, I can help with that."

        db_session.expire_all()
        messages = (
            db_session.query(CallMessage)
            .filter(CallMessage.call_id == call.id)
            .order_by(CallMessage.id.asc())
            .all()
        )
        roles = [m.role.value for m in messages]

        assert roles == ["user", "assistant", "assistant"]


SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def ws_user(db_session):
    user = User(
        email="voice@example.com",
        full_name="Voice User",
        hashed_password="hashed_password_123",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def ws_agent(db_session, ws_user):
    agent = Agent(
        owner_id=ws_user.id,
        name="Voice Agent",
        description="A voice test agent",
        system_prompt="You are a concise voice agent.",
        is_active=True,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


class TestVoiceWebSocket:
    def test_full_voice_round_trip(self, db_session, ws_agent, ws_user):
        token = create_access_token(ws_user.id)
        client = TestClient(app)

        fake_stt = FakeSTT(transcript="Book an appointment tomorrow")
        fake_tts = FakeTTS()

        with patch("app.api.routes.voice.get_stt_provider", return_value=fake_stt):
            with patch("app.api.routes.voice.get_tts_provider", return_value=fake_tts):
                with patch(
                    "app.services.voice_session.run_agent_turn",
                    new_callable=AsyncMock,
                ) as mock_turn:
                    mock_turn.return_value = AgentResult(
                        response="I can help you book that.",
                        messages=[],
                    )

                    with client.websocket_connect(f"/voice/ws?token={token}") as ws:
                        ws.send_json(
                            {
                                "type": "session_start",
                                "agent_id": ws_agent.id,
                                "caller_number": "1234567890",
                            }
                        )
                        started = ws.receive_json()
                        assert started["type"] == "session_started"

                        ws.send_bytes(b"\x00\x01audiodata")
                        ws.send_json({"type": "utterance_end"})

                        events = []
                        for _ in range(4):
                            events.append(ws.receive_json())

                        types = [e["type"] for e in events]

                        assert "stt_result" in types
                        assert "assistant_text" in types
                        assert "audio" in types
                        assert "audio_end" in types

                        stt_event = next(e for e in events if e["type"] == "stt_result")
                        assert stt_event["text"] == "Book an appointment tomorrow"

    def test_rejects_unauthorized_connection(self):
        client = TestClient(app)

        with client.websocket_connect("/voice/ws?token=invalid-token") as ws:
            error = ws.receive_json()
            assert error == {"type": "error", "detail": "Unauthorized"}