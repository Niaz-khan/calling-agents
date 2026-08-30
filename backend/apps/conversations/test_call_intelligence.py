import json

import pytest

from apps.agents.models import Agent
from apps.appointments.models import Appointment
from apps.conversations.call_intelligence import (
    build_transcript,
    classify_call_outcome,
    finalize_call,
    generate_call_summary,
    get_customer_memory,
)
from apps.conversations.models import (
    Conversation,
    ConversationMessage,
    ConversationOutcome,
    PhoneCall,
    PhoneCallStatus,
)
from apps.crm.models import Customer

pytestmark = pytest.mark.django_db


def _agent(org):
    return Agent.objects.create(organization=org, name="Front Desk", system_prompt="p")


def _conversation(org, customer=None):
    conversation = Conversation.objects.create(
        organization=org, agent=_agent(org), customer=customer
    )
    PhoneCall.objects.create(
        conversation=conversation,
        caller_number="+15553334444",
        provider_status=PhoneCallStatus.IN_PROGRESS,
    )
    return conversation


def _message(conversation, role, content, tool_call_id=None):
    return ConversationMessage.objects.create(
        conversation=conversation,
        role=role,
        content=content,
        tool_call_id=tool_call_id,
    )


class TestBuildTranscript:
    def test_builds_readable_transcript(self, tenant):
        _, org, _ = tenant
        conversation = _conversation(org)
        _message(conversation, "USER", "I need an appointment tomorrow.")
        _message(conversation, "ASSISTANT", "I'd be happy to help with that.")

        transcript = build_transcript(conversation)

        assert "Customer: I need an appointment tomorrow." in transcript
        assert "Agent: I'd be happy to help with that." in transcript

    def test_skips_tool_interactions(self, tenant):
        _, org, _ = tenant
        conversation = _conversation(org)
        _message(conversation, "USER", "Book it for 3 PM.")
        _message(conversation, "ASSISTANT", '{"tool_calls": [], "content": null}')
        _message(conversation, "TOOL", '{"success": true}', tool_call_id="call_1")
        _message(conversation, "ASSISTANT", "Your appointment is booked.")

        transcript = build_transcript(conversation)

        assert "tool_calls" not in transcript
        assert '{"success": true}' not in transcript
        assert "Your appointment is booked." in transcript


class TestGenerateCallSummary:
    def test_generates_summary(self, tenant, monkeypatch):
        _, org, _ = tenant
        conversation = _conversation(org)
        _message(conversation, "USER", "I need help.")

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response",
            lambda messages, tools=None: {
                "content": "Customer requested help.",
                "tool_calls": [],
            },
        )

        assert generate_call_summary(conversation) == "Customer requested help."


class TestClassifyCallOutcome:
    def _no_llm(self):
        def _boom(messages, tools=None):
            raise AssertionError("LLM should not have been called")

        return _boom

    def test_appointment_booked_from_database(self, tenant, monkeypatch):
        _, org, _ = tenant
        conversation = _conversation(org)
        Appointment.objects.create(
            organization=org,
            agent=conversation.agent,
            conversation=conversation,
            customer_name="John Doe",
            customer_phone="+15553334444",
            start_time="2026-08-28T15:00:00Z",
            end_time="2026-08-28T15:30:00Z",
        )

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response", self._no_llm()
        )

        assert (
            classify_call_outcome(conversation)
            == ConversationOutcome.APPOINTMENT_BOOKED
        )

    def test_transferred_from_provider_status(self, tenant, monkeypatch):
        _, org, _ = tenant
        conversation = _conversation(org)
        conversation.phone_call.provider_status = PhoneCallStatus.TRANSFERRED
        conversation.phone_call.save()

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response", self._no_llm()
        )

        assert (
            classify_call_outcome(conversation)
            == ConversationOutcome.TRANSFERRED_TO_HUMAN
        )

    def test_unknown_for_empty_call(self, tenant, monkeypatch):
        _, org, _ = tenant
        conversation = _conversation(org)

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response", self._no_llm()
        )

        assert classify_call_outcome(conversation) == ConversationOutcome.UNKNOWN

    def test_classifies_via_llm(self, tenant, monkeypatch):
        _, org, _ = tenant
        conversation = _conversation(org)
        _message(conversation, "USER", "Can you call me back tomorrow?")

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response",
            lambda messages, tools=None: {
                "content": "callback_requested",
                "tool_calls": [],
            },
        )

        assert (
            classify_call_outcome(conversation)
            == ConversationOutcome.CALLBACK_REQUESTED
        )

    def test_returns_unknown_when_llm_fails(self, tenant, monkeypatch):
        from apps.ai.provider import LLMError

        _, org, _ = tenant
        conversation = _conversation(org)
        _message(conversation, "USER", "Hello.")

        def _boom(messages, tools=None):
            raise LLMError("LLM down")

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response", _boom
        )

        assert classify_call_outcome(conversation) == ConversationOutcome.UNKNOWN


class TestFinalizeCall:
    def test_sets_summary_and_outcome(self, tenant, monkeypatch):
        _, org, _ = tenant
        conversation = _conversation(org)
        _message(conversation, "USER", "I need an appointment for Friday.")

        calls = iter([
            {"content": "Customer requested an appointment.", "tool_calls": []},
            {"content": "appointment_requested", "tool_calls": []},
        ])
        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response",
            lambda messages, tools=None: next(calls),
        )

        finalize_call(conversation)

        conversation.refresh_from_db()
        assert conversation.summary == "Customer requested an appointment."
        assert conversation.outcome == ConversationOutcome.APPOINTMENT_REQUESTED

    def test_appends_summary_to_customer_memory(self, tenant, monkeypatch):
        _, org, _ = tenant
        customer = Customer.objects.create(
            organization=org,
            phone_number="+15553334444",
            name="John Doe",
        )
        conversation = _conversation(org, customer=customer)
        _message(conversation, "USER", "I want to book for Friday.")

        monkeypatch.setattr(
            "apps.conversations.call_intelligence.generate_response",
            lambda messages, tools=None: {
                "content": "Customer booked an appointment for Friday.",
                "tool_calls": [],
            },
        )

        finalize_call(conversation)

        customer.refresh_from_db()
        assert customer.memory is not None
        assert "Customer booked an appointment for Friday." in customer.memory


class TestCustomerMemory:
    def test_returns_none_when_no_customer(self, tenant):
        _, org, _ = tenant
        conversation = _conversation(org)
        assert get_customer_memory(conversation) is None

    def test_returns_memory_for_customer(self, tenant):
        _, org, _ = tenant
        customer = Customer.objects.create(
            organization=org,
            phone_number="+15553334444",
            name="John Doe",
            memory="Customer prefers morning appointments.",
        )
        conversation = _conversation(org, customer=customer)
        assert get_customer_memory(conversation) == "Customer prefers morning appointments."