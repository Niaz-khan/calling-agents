import json
from datetime import timedelta

import pytest
from django.utils import timezone

from agents.models import Agent
from ai.agent import MAX_TOOL_ROUNDS, run_agent
from ai.provider import LLMError
from ai.tools import TOOLS, execute_tool
from appointments.models import Appointment
from tenancy.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def org_agent():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="Scheduler", system_prompt="p")
    return org, agent


def _slot(hours):
    now = timezone.now() + timedelta(days=2, minutes=30)
    return now + timedelta(hours=hours), now + timedelta(hours=hours + 0.5)


class TestExecuteTool:
    def test_check_availability_valid(self, org_agent):
        org, agent = org_agent
        start, end = _slot(0)
        result = execute_tool(
            org, agent.id, None, "check_appointment_availability",
            json.dumps({"start_time": start.isoformat(), "end_time": end.isoformat()}),
        )
        data = json.loads(result)
        assert data["available"] is True
        assert data["requested_start"] == start.isoformat()

    def test_book_appointment_success(self, org_agent):
        org, agent = org_agent
        start, end = _slot(0)
        result = execute_tool(
            org, agent.id, None, "book_appointment",
            json.dumps({
                "customer_name": "John Doe",
                "customer_phone": "+15551234567",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "notes": "General",
            }),
        )
        data = json.loads(result)
        assert data["success"] is True
        assert data["customer_name"] == "John Doe"
        assert Appointment.objects.count() == 1

    def test_book_appointment_rejects_overlap(self, org_agent):
        org, agent = org_agent
        start, end = _slot(0)
        execute_tool(
            org, agent.id, None, "book_appointment",
            json.dumps({
                "customer_name": "First",
                "customer_phone": "+15551111111",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            }),
        )
        result = execute_tool(
            org, agent.id, None, "book_appointment",
            json.dumps({
                "customer_name": "Second",
                "customer_phone": "+15552222222",
                "start_time": (start + timedelta(minutes=10)).isoformat(),
                "end_time": (end + timedelta(minutes=10)).isoformat(),
            }),
        )
        data = json.loads(result)
        assert data["success"] is False
        assert "error" in data

    def test_unknown_tool_rejected(self, org_agent):
        org, agent = org_agent
        result = execute_tool(org, agent.id, None, "delete_database", "{}")
        data = json.loads(result)
        assert "error" in data

    def test_invalid_json_arguments(self, org_agent):
        org, agent = org_agent
        result = execute_tool(org, agent.id, None, "check_appointment_availability", "not json")
        data = json.loads(result)
        assert "error" in data

    def test_missing_agent_rejected(self, org_agent):
        org, _ = org_agent
        start, end = _slot(0)
        result = execute_tool(
            org, 9999, None, "check_appointment_availability",
            json.dumps({"start_time": start.isoformat(), "end_time": end.isoformat()}),
        )
        data = json.loads(result)
        assert data["error"] == "Agent not found"

    def test_invalid_time_arguments(self, org_agent):
        org, agent = org_agent
        result = execute_tool(
            org, agent.id, None, "check_appointment_availability",
            json.dumps({"start_time": "not-a-time", "end_time": "also-bad"}),
        )
        data = json.loads(result)
        assert "error" in data


class TestAgentOrchestrator:
    def test_direct_response(self, org_agent, monkeypatch):
        org, agent = org_agent
        monkeypatch.setattr(
            "ai.agent.generate_response",
            lambda messages, tools=None: {"content": "Hello!", "tool_calls": []},
        )
        result = run_agent("You are helpful.", [], org, agent.id)
        assert result.response == "Hello!"
        assert result.messages == []

    def test_tool_call_then_response(self, org_agent, monkeypatch):
        org, agent = org_agent
        start, end = _slot(0)
        calls = iter([
            {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "check_appointment_availability",
                            "arguments": json.dumps({
                                "start_time": start.isoformat(),
                                "end_time": end.isoformat(),
                            }),
                        },
                    }
                ],
            },
            {"content": "That time is available.", "tool_calls": []},
        ])

        def fake_provider(messages, tools=None):
            return next(calls)

        monkeypatch.setattr("ai.agent.generate_response", fake_provider)
        result = run_agent("You are helpful.", [], org, agent.id)

        assert result.response == "That time is available."
        assert [message["role"] for message in result.messages] == ["assistant", "tool"]

    def test_booking_tool_round(self, org_agent, monkeypatch):
        org, agent = org_agent
        start, end = _slot(0)
        calls = iter([
            {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_book",
                        "function": {
                            "name": "book_appointment",
                            "arguments": json.dumps({
                                "customer_name": "Jane",
                                "customer_phone": "+15551234567",
                                "start_time": start.isoformat(),
                                "end_time": end.isoformat(),
                            }),
                        },
                    }
                ],
            },
            {"content": "Booked!", "tool_calls": []},
        ])

        def fake_provider(messages, tools=None):
            return next(calls)

        monkeypatch.setattr("ai.agent.generate_response", fake_provider)
        result = run_agent("You are helpful.", [], org, agent.id)

        assert result.response == "Booked!"
        assert Appointment.objects.count() == 1
        tool_result = json.loads(result.messages[1]["content"])
        assert tool_result["success"] is True

    def test_loop_caps_at_max_rounds(self, org_agent, monkeypatch):
        org, agent = org_agent
        monkeypatch.setattr(
            "ai.agent.generate_response",
            lambda messages, tools=None: {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_x",
                        "function": {
                            "name": "check_appointment_availability",
                            "arguments": json.dumps({
                                "start_time": timezone.now().isoformat(),
                                "end_time": (timezone.now() + timedelta(minutes=30)).isoformat(),
                            }),
                        },
                    }
                ],
            },
        )
        result = run_agent("You are helpful.", [], org, agent.id)
        assert result.response == (
            "I apologize, but I'm having trouble processing your request. "
            "Please try again."
        )
        tool_rounds = sum(
            1 for message in result.messages if message["role"] == "assistant"
        )
        assert tool_rounds == MAX_TOOL_ROUNDS

    def test_llm_failure_propagates(self, org_agent, monkeypatch):
        org, agent = org_agent

        def boom(messages, tools=None):
            raise LLMError("LLM down")

        monkeypatch.setattr("ai.agent.generate_response", boom)
        with pytest.raises(LLMError):
            run_agent("You are helpful.", [], org, agent.id)


def test_tool_registry_contains_appointment_tools():
    assert "check_appointment_availability" in TOOLS
    assert "book_appointment" in TOOLS