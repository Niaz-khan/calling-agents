import json
from unittest.mock import AsyncMock, patch

import pytest

from app.ai.agent import run_agent


@pytest.mark.asyncio
class TestRunAgent:
    async def test_returns_text_response_without_tools(self, db_session, test_agent):
        mock_response = {
            "content": "Hello! How can I help you?",
            "tool_calls": [],
        }

        with patch("app.ai.agent.generate_response", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await run_agent(
                system_prompt=test_agent.system_prompt,
                conversation=[{"role": "user", "content": "Hi"}],
                db=db_session,
                agent_id=test_agent.id,
            )

            assert result.response == "Hello! How can I help you?"
            assert result.messages == []
            mock_gen.assert_called_once()

    async def test_executes_tool_and_returns_final_response(self, db_session, test_agent):
        tool_call = {
            "id": "call_123",
            "function": {
                "name": "check_appointment_availability",
                "arguments": json.dumps({
                    "start_time": "2026-08-28T15:00:00",
                    "end_time": "2026-08-28T15:30:00",
                }),
            },
        }

        tool_result_response = {
            "content": None,
            "tool_calls": [tool_call],
        }

        final_response = {
            "content": "3 PM is available. Would you like me to book it?",
            "tool_calls": [],
        }

        with patch("app.ai.agent.generate_response", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = [tool_result_response, final_response]

            result = await run_agent(
                system_prompt=test_agent.system_prompt,
                conversation=[{"role": "user", "content": "I want an appointment tomorrow at 3 PM"}],
                db=db_session,
                agent_id=test_agent.id,
            )

            assert result.response == "3 PM is available. Would you like me to book it?"
            assert len(result.messages) == 2
            assert result.messages[0]["role"] == "assistant"
            assert result.messages[1]["role"] == "tool"
            assert mock_gen.call_count == 2

    async def test_handles_multiple_tool_calls(self, db_session, test_agent):
        check_tool_call = {
            "id": "call_123",
            "function": {
                "name": "check_appointment_availability",
                "arguments": json.dumps({
                    "start_time": "2026-08-28T15:00:00",
                    "end_time": "2026-08-28T15:30:00",
                }),
            },
        }

        book_tool_call = {
            "id": "call_456",
            "function": {
                "name": "book_appointment",
                "arguments": json.dumps({
                    "customer_name": "John Doe",
                    "customer_phone": "1234567890",
                    "start_time": "2026-08-28T15:00:00",
                    "end_time": "2026-08-28T15:30:00",
                }),
            },
        }

        first_response = {
            "content": None,
            "tool_calls": [check_tool_call],
        }

        second_response = {
            "content": "3 PM is available. Booking now.",
            "tool_calls": [book_tool_call],
        }

        final_response = {
            "content": "Your appointment has been booked successfully!",
            "tool_calls": [],
        }

        with patch("app.ai.agent.generate_response", new_callable=AsyncMock) as mock_gen:
            mock_gen.side_effect = [first_response, second_response, final_response]

            result = await run_agent(
                system_prompt=test_agent.system_prompt,
                conversation=[{"role": "user", "content": "Book me an appointment tomorrow at 3 PM"}],
                db=db_session,
                agent_id=test_agent.id,
            )

            assert result.response == "Your appointment has been booked successfully!"
            assert len(result.messages) == 4
            assert mock_gen.call_count == 3

    async def test_returns_fallback_after_max_rounds(self, db_session, test_agent):
        tool_call = {
            "id": "call_123",
            "function": {
                "name": "check_appointment_availability",
                "arguments": json.dumps({
                    "start_time": "2026-08-28T15:00:00",
                    "end_time": "2026-08-28T15:30:00",
                }),
            },
        }

        tool_response = {
            "content": None,
            "tool_calls": [tool_call],
        }

        with patch("app.ai.agent.generate_response", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = tool_response

            result = await run_agent(
                system_prompt=test_agent.system_prompt,
                conversation=[{"role": "user", "content": "Help me"}],
                db=db_session,
                agent_id=test_agent.id,
            )

            assert "trouble processing" in result.response
            assert len(result.messages) == 10
            assert mock_gen.call_count == 5

    async def test_uses_default_prompt_when_none_provided(self, db_session, test_agent):
        mock_response = {
            "content": "I can help you with that.",
            "tool_calls": [],
        }

        with patch("app.ai.agent.generate_response", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response

            result = await run_agent(
                system_prompt=None,
                conversation=[{"role": "user", "content": "Hello"}],
                db=db_session,
                agent_id=test_agent.id,
            )

            assert result.response == "I can help you with that."

            call_args = mock_gen.call_args
            messages = call_args[0][0]
            assert messages[0]["role"] == "system"
            assert "phone receptionist" in messages[0]["content"].lower()
