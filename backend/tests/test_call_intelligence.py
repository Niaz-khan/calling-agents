import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.models.appointment import Appointment, AppointmentStatus
from app.models.call import Call, CallDirection, CallOutcome, CallStatus
from app.models.call_message import CallMessage, MessageRole
from app.services.call_intelligence import (
    build_transcript,
    classify_call_outcome,
    finalize_call,
    generate_call_summary,
    get_customer_memory,
)


@pytest.fixture
def call_with_messages(db_session, test_agent):
    call = Call(
        agent_id=test_agent.id,
        caller_number="1234567890",
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    return call


class TestBuildTranscript:
    def test_builds_readable_transcript(self, db_session, call_with_messages):
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.USER,
                content="I need an appointment tomorrow.",
            )
        )
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.ASSISTANT,
                content="I'd be happy to help with that.",
            )
        )
        db_session.commit()

        transcript = build_transcript(db_session, call_with_messages)

        assert "Customer: I need an appointment tomorrow." in transcript
        assert "Agent: I'd be happy to help with that." in transcript

    def test_skips_tool_interactions(self, db_session, call_with_messages):
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.USER,
                content="Book it for 3 PM.",
            )
        )
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.ASSISTANT,
                content='{"tool_calls": [], "content": null}',
            )
        )
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.TOOL,
                content='{"success": true}',
                tool_call_id="call_1",
            )
        )
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.ASSISTANT,
                content="Your appointment is booked.",
            )
        )
        db_session.commit()

        transcript = build_transcript(db_session, call_with_messages)

        assert "tool_calls" not in transcript
        assert '{"success": true}' not in transcript
        assert "Your appointment is booked." in transcript


@pytest.mark.asyncio
class TestGenerateCallSummary:
    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_generates_summary(self, mock_generate, db_session, call_with_messages):
        mock_generate.return_value = {
            "content": "Customer called to book an appointment.",
            "tool_calls": [],
        }

        summary = await generate_call_summary(db_session, call_with_messages)

        assert summary == "Customer called to book an appointment."


@pytest.mark.asyncio
class TestClassifyCallOutcome:
    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_classifies_appointment_booked_from_database(
        self, mock_generate, db_session, call_with_messages, test_agent
    ):
        db_session.add(
            Appointment(
                agent_id=test_agent.id,
                call_id=call_with_messages.id,
                customer_name="John Doe",
                customer_phone="1234567890",
                start_time=datetime(2026, 8, 28, 15, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 8, 28, 15, 30, tzinfo=timezone.utc),
                status=AppointmentStatus.SCHEDULED,
            )
        )
        db_session.commit()

        outcome = await classify_call_outcome(db_session, call_with_messages)

        assert outcome == CallOutcome.APPOINTMENT_BOOKED
        mock_generate.assert_not_awaited()

    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_classifies_transferred_from_status(
        self, mock_generate, db_session, call_with_messages
    ):
        call_with_messages.status = CallStatus.TRANSFERRED
        db_session.commit()

        outcome = await classify_call_outcome(db_session, call_with_messages)

        assert outcome == CallOutcome.TRANSFERRED_TO_HUMAN
        mock_generate.assert_not_awaited()

    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_classifies_unknown_for_empty_call(
        self, mock_generate, db_session, call_with_messages
    ):
        outcome = await classify_call_outcome(db_session, call_with_messages)

        assert outcome == CallOutcome.UNKNOWN
        mock_generate.assert_not_awaited()

    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_classifies_via_llm(self, mock_generate, db_session, call_with_messages):
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.USER,
                content="Can you call me back tomorrow?",
            )
        )
        db_session.commit()

        mock_generate.return_value = {
            "content": "callback_requested",
            "tool_calls": [],
        }

        outcome = await classify_call_outcome(db_session, call_with_messages)

        assert outcome == CallOutcome.CALLBACK_REQUESTED

    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_returns_unknown_when_llm_fails(
        self, mock_generate, db_session, call_with_messages
    ):
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.USER,
                content="Hello.",
            )
        )
        db_session.commit()

        mock_generate.side_effect = Exception("LLM unavailable")

        outcome = await classify_call_outcome(db_session, call_with_messages)

        assert outcome == CallOutcome.UNKNOWN


@pytest.mark.asyncio
class TestFinalizeCall:
    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_sets_summary_and_outcome(self, mock_generate, db_session, call_with_messages):
        db_session.add(
            CallMessage(
                call_id=call_with_messages.id,
                role=MessageRole.USER,
                content="I need an appointment for Friday.",
            )
        )
        db_session.commit()

        mock_generate.side_effect = [
            {"content": "Customer requested an appointment.", "tool_calls": []},
            {"content": "appointment_requested", "tool_calls": []},
        ]

        call = await finalize_call(db_session, call_with_messages)

        call_id = call.id
        db_session.expire_all()
        persisted = db_session.get(Call, call_id)

        assert persisted.summary == "Customer requested an appointment."
        assert persisted.outcome == CallOutcome.APPOINTMENT_REQUESTED


class TestCustomerMemory:
    @pytest.mark.asyncio
    @patch("app.services.call_intelligence.generate_response", new_callable=AsyncMock)
    async def test_appends_summary_to_customer_memory(
        self, mock_generate, db_session, test_agent, test_user
    ):
        from app.models.customer import Customer

        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
            name="John Doe",
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
            CallMessage(
                call_id=call.id,
                role=MessageRole.USER,
                content="I want to book for Friday.",
            )
        )
        db_session.commit()

        mock_generate.side_effect = [
            {"content": "Customer booked an appointment for Friday.", "tool_calls": []},
            {"content": "appointment_requested", "tool_calls": []},
        ]

        await finalize_call(db_session, call)

        db_session.expire_all()
        updated = db_session.get(Customer, customer.id)
        assert updated.memory is not None
        assert "Customer booked an appointment for Friday." in updated.memory

    def test_returns_none_when_no_customer(self, db_session, test_agent):
        call = Call(
            agent_id=test_agent.id,
            caller_number="1234567890",
            direction=CallDirection.INBOUND,
            status=CallStatus.IN_PROGRESS,
        )
        db_session.add(call)
        db_session.commit()
        db_session.refresh(call)

        assert get_customer_memory(db_session, call) is None

    def test_returns_memory_for_customer(self, db_session, test_agent, test_user):
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

        assert get_customer_memory(db_session, call) == "Customer prefers morning appointments."