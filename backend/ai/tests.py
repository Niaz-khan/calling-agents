import json
from datetime import timedelta

import pytest
from django.utils import timezone

from agents.models import Agent
from ai.agent import MAX_TOOL_ROUNDS, run_agent
from ai.provider import LLMError
from ai.tools import TOOLS, execute_tool
from appointments.models import Appointment
from conversations.models import (
    Conversation,
    ConversationStatus,
    PhoneCall,
    PhoneCallStatus,
)
from crm.models import Customer
from knowledge.models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument
from services.models import Service
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


def test_tool_registry_contains_all_tools():
    for name in [
        "list_services",
        "check_appointment_availability",
        "book_appointment",
        "lookup_customer",
        "search_knowledge_base",
        "transfer_to_human",
    ]:
        assert name in TOOLS


class _HashEmbedder:
    """Deterministic fake embedder: flag presence of known vocabulary words."""

    _VOCAB = ["consultation", "cost", "fifty", "dollars", "dental", "cleaning"]

    def embed(self, texts):
        return [
            [1.0 if word in text else 0.0 for word in self._VOCAB]
            for text in texts
        ]


def _conversation(org, agent):
    conversation = Conversation.objects.create(organization=org, agent=agent)
    PhoneCall.objects.create(
        conversation=conversation,
        caller_number="+15553334444",
        provider_status=PhoneCallStatus.IN_PROGRESS,
    )
    return conversation


class TestLookupCustomerTool:
    def test_found(self, org_agent):
        org, agent = org_agent
        Customer.objects.create(
            organization=org,
            phone_number="+15551234567",
            name="John Doe",
            email="john@example.com",
            notes="Prefers email",
        )
        result = json.loads(
            execute_tool(
                org, agent.id, None, "lookup_customer",
                json.dumps({"phone_number": "+15551234567"}),
            )
        )
        assert result["found"] is True
        assert result["name"] == "John Doe"
        assert result["notes"] == "Prefers email"

    def test_not_found(self, org_agent):
        org, agent = org_agent
        result = json.loads(
            execute_tool(
                org, agent.id, None, "lookup_customer",
                json.dumps({"phone_number": "+15559999999"}),
            )
        )
        assert result["found"] is False

    def test_cross_org_isolation(self, org_agent):
        org, agent = org_agent
        other = Organization.objects.create(name="Rival")
        Customer.objects.create(
            organization=other, phone_number="+15551234567", name="Rival Customer"
        )
        result = json.loads(
            execute_tool(
                org, agent.id, None, "lookup_customer",
                json.dumps({"phone_number": "+15551234567"}),
            )
        )
        assert result["found"] is False
        assert Customer.objects.count() == 1

    def test_missing_phone_number_rejected(self, org_agent):
        org, agent = org_agent
        result = json.loads(
            execute_tool(org, agent.id, None, "lookup_customer", "{}")
        )
        assert "error" in result


class TestSearchKnowledgeBaseTool:
    def _ingest(self, org, agent):
        knowledge_base = KnowledgeBase.objects.create(organization=org, agent=agent, name="Pricing")
        document = KnowledgeDocument.objects.create(
            knowledge_base=knowledge_base,
            filename="pricing.txt",
            source_type="manual",
            status="PROCESSED",
        )
        content = (
            "consultation cost fifty dollars per session "
            "dental cleaning eighty dollars"
        )
        KnowledgeChunk.objects.create(
            document=document,
            chunk_index=0,
            content=content,
            embedding=_HashEmbedder().embed([content])[0],
        )
        return knowledge_base

    def test_returns_relevant_documents(self, org_agent, monkeypatch):
        org, agent = org_agent
        self._ingest(org, agent)
        monkeypatch.setattr("knowledge.services.get_embedding_provider", lambda: _HashEmbedder())
        result = json.loads(
            execute_tool(
                org, agent.id, None, "search_knowledge_base",
                json.dumps({"query": "consultation cost"}),
            )
        )
        assert result["found"] is True
        assert "fifty dollars" in result["results"][0]["content"]
        assert result["results"][0]["score"] > 0

    def test_guards_against_hallucination(self, org_agent, monkeypatch):
        org, agent = org_agent
        self._ingest(org, agent)
        monkeypatch.setattr("knowledge.services.get_embedding_provider", lambda: _HashEmbedder())
        result = json.loads(
            execute_tool(
                org, agent.id, None, "search_knowledge_base",
                json.dumps({"query": "violet walrus kangaroo"}),
            )
        )
        assert result["found"] is False
        assert "do not guess or invent" in result["message"].lower()

    def test_handles_agent_without_knowledge_base(self, org_agent, monkeypatch):
        org, agent = org_agent
        monkeypatch.setattr("knowledge.services.get_embedding_provider", lambda: _HashEmbedder())
        result = json.loads(
            execute_tool(
                org, agent.id, None, "search_knowledge_base",
                json.dumps({"query": "consultation cost"}),
            )
        )
        assert result["found"] is False
        assert "no knowledge base" in result["message"].lower()

    def test_missing_query_rejected(self, org_agent):
        org, agent = org_agent
        result = json.loads(
            execute_tool(org, agent.id, None, "search_knowledge_base", "{}")
        )
        assert "error" in result


class TestServicesTools:
    def _services(self, org):
        return Service.objects.create(
            organization=org,
            name="Consultation",
            description="Dental consultation",
            duration_minutes=30,
            price="50.00",
            currency="USD",
        )

    def test_list_services_returns_active_org_services(self, org_agent):
        org, agent = org_agent
        self._services(org)
        Service.objects.create(
            organization=org, name="Hidden", duration_minutes=60, active=False
        )
        other = Organization.objects.create(name="Rival")
        Service.objects.create(
            organization=other, name="Foreign", duration_minutes=15
        )

        data = json.loads(
            execute_tool(org, agent.id, None, "list_services", "{}")
        )
        names = [row["name"] for row in data["services"]]
        assert names == ["Consultation"]
        row = data["services"][0]
        assert row["duration_minutes"] == 30
        assert row["price"] == "50.00"
        assert row["currency"] == "USD"
        assert row["id"] == Service.objects.get(name="Consultation").id

    def test_availability_uses_service_duration(self, org_agent):
        org, agent = org_agent
        service = self._services(org)
        start, _ = _slot(0)
        result = json.loads(
            execute_tool(
                org, agent.id, None, "check_appointment_availability",
                json.dumps({"start_time": start.isoformat(), "service_id": service.id}),
            )
        )
        assert result["available"] is True
        assert result["requested_end"] == (start + timedelta(minutes=30)).isoformat()
        assert result["service_id"] == service.id

    def test_availability_rejects_end_only_llm_end_ignored_with_service(self, org_agent):
        org, agent = org_agent
        service = self._services(org)
        start, _ = _slot(0)
        result = json.loads(
            execute_tool(
                org, agent.id, None, "check_appointment_availability",
                json.dumps({
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=3)).isoformat(),
                    "service_id": service.id,
                }),
            )
        )
        # The service duration is authoritative; the LLM-supplied end is ignored.
        assert result["requested_end"] == (start + timedelta(minutes=30)).isoformat()

    def test_availability_requires_end_without_service(self, org_agent):
        org, agent = org_agent
        start, _ = _slot(0)
        result = json.loads(
            execute_tool(
                org, agent.id, None, "check_appointment_availability",
                json.dumps({"start_time": start.isoformat()}),
            )
        )
        assert "error" in result

    def test_availability_rejects_foreign_or_inactive_service(self, org_agent):
        org, agent = org_agent
        start, _ = _slot(0)
        other = Organization.objects.create(name="Rival")
        foreign = Service.objects.create(
            organization=other, name="Foreign", duration_minutes=30
        )
        result = json.loads(
            execute_tool(
                org, agent.id, None, "check_appointment_availability",
                json.dumps({"start_time": start.isoformat(), "service_id": foreign.id}),
            )
        )
        assert "error" in result

    def test_book_with_service_derives_end_and_links(self, org_agent):
        org, agent = org_agent
        service = self._services(org)
        start, _ = _slot(0)
        result = json.loads(
            execute_tool(
                org, agent.id, None, "book_appointment",
                json.dumps({
                    "customer_name": "Jane",
                    "customer_phone": "+15551234567",
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=5)).isoformat(),
                    "service_id": service.id,
                }),
            )
        )
        assert result["success"] is True
        assert result["service_id"] == service.id
        assert result["service_name"] == "Consultation"
        assert result["requested_end"] == (start + timedelta(minutes=30)).isoformat()
        appointment = Appointment.objects.get()
        assert appointment.service == service
        assert appointment.start_time == start
        assert appointment.end_time == start + timedelta(minutes=30)

    def test_book_rejects_foreign_service(self, org_agent):
        org, agent = org_agent
        start, _ = _slot(0)
        other = Organization.objects.create(name="Rival")
        foreign = Service.objects.create(
            organization=other, name="Foreign", duration_minutes=30
        )
        result = json.loads(
            execute_tool(
                org, agent.id, None, "book_appointment",
                json.dumps({
                    "customer_name": "Jane",
                    "customer_phone": "+15551234567",
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(minutes=30)).isoformat(),
                    "service_id": foreign.id,
                }),
            )
        )
        assert "error" in result
        assert Appointment.objects.count() == 0

    def test_book_rejects_overlap_between_service_slots(self, org_agent):
        org, agent = org_agent
        service = self._services(org)
        start, _ = _slot(0)
        execute_tool(
            org, agent.id, None, "book_appointment",
            json.dumps({
                "customer_name": "First",
                "customer_phone": "+15551111111",
                "start_time": start.isoformat(),
                "service_id": service.id,
            }),
        )
        overlap = json.loads(
            execute_tool(
                org, agent.id, None, "book_appointment",
                json.dumps({
                    "customer_name": "Second",
                    "customer_phone": "+15552222222",
                    "start_time": (start + timedelta(minutes=15)).isoformat(),
                    "service_id": service.id,
                }),
            )
        )
        assert overlap["success"] is False
        assert "error" in overlap


class TestTransferToHumanTool:
    def test_transfers_conversation(self, org_agent):
        org, agent = org_agent
        conversation = _conversation(org, agent)

        result = json.loads(
            execute_tool(
                org, agent.id, conversation.id, "transfer_to_human",
                json.dumps({"reason": "Customer requested a manager"}),
            )
        )
        assert result["success"] is True

        conversation.refresh_from_db()
        assert conversation.status == ConversationStatus.CLOSED
        assert conversation.ended_at is not None
        assert conversation.phone_call.provider_status == PhoneCallStatus.TRANSFERRED

    def test_transfer_authorization_refused(self, org_agent):
        org, agent = org_agent
        agent.can_transfer = False
        agent.save(update_fields=["can_transfer"])
        conversation = _conversation(org, agent)

        result = json.loads(
            execute_tool(
                org, agent.id, conversation.id, "transfer_to_human",
                json.dumps({"reason": "Customer requested a manager"}),
            )
        )
        assert result["success"] is False
        assert "error" in result
        assert "disabled" in result["error"]

        conversation.refresh_from_db()
        assert conversation.status == ConversationStatus.OPEN
        assert (
            conversation.phone_call.provider_status
            == PhoneCallStatus.IN_PROGRESS
        )

    def test_succeeds_without_call(self, org_agent):
        org, agent = org_agent
        result = json.loads(
            execute_tool(
                org, agent.id, None, "transfer_to_human",
                json.dumps({"reason": "Escalation"}),
            )
        )
        assert result["success"] is True

    def test_cross_org_call_untouched(self, org_agent):
        org, agent = org_agent
        other = Organization.objects.create(name="Rival")
        rival_agent = Agent.objects.create(organization=other, name="R", system_prompt="p")
        rival_conversation = _conversation(other, rival_agent)

        result = json.loads(
            execute_tool(
                org, agent.id, rival_conversation.id, "transfer_to_human",
                json.dumps({"reason": "Whatever"}),
            )
        )
        assert result["success"] is True

        rival_conversation.refresh_from_db()
        assert rival_conversation.status == ConversationStatus.OPEN
        assert (
            rival_conversation.phone_call.provider_status
            == PhoneCallStatus.IN_PROGRESS
        )

    def test_missing_reason_rejected(self, org_agent):
        org, agent = org_agent
        result = json.loads(
            execute_tool(org, agent.id, None, "transfer_to_human", "{}")
        )
        assert "error" in result