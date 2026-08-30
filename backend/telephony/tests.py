import asyncio
import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import httpx
import pytest
from django.test import override_settings

from agents.models import Agent
from conversations.models import (
    Conversation,
    ConversationOutcome,
    PhoneCall,
    PhoneCallStatus,
)

from .models import PhoneNumber

pytestmark = pytest.mark.django_db


def _sign(url, params, token):
    sorted_params = "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(
        token.encode(),
        (url + sorted_params).encode(),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode()


def _make_agent(org, name="Sales"):
    return Agent.objects.create(organization=org, name=name, system_prompt="p")


def test_phone_numbers_require_auth(api_client):
    assert api_client.get("/phone-numbers").status_code == 401


def test_phone_number_crud(tenant):
    _, org, client = tenant
    agent = _make_agent(org)

    unknown_agent = client.post(
        "/phone-numbers",
        {"phone_number": "+14441112222", "agent_id": 9999},
    )
    assert unknown_agent.status_code == 404

    created = client.post(
        "/phone-numbers",
        {
            "phone_number": "+14441112222",
            "agent_id": agent.id,
            "provider": "twilio",
            "provider_number_id": "PN123",
        },
    )
    assert created.status_code == 201
    data = created.json()
    assert data["organization_id"] == org.id
    assert data["agent_id"] == agent.id
    assert data["provider"] == "twilio"
    assert data["provider_number_id"] == "PN123"
    assert data["is_active"] is True

    assert (
        client.post("/phone-numbers", {"phone_number": "+14441112222", "agent_id": agent.id}).status_code
        == 409
    )

    toggled = client.patch(f"/phone-numbers/{data['id']}", {"is_active": False})
    assert toggled.status_code == 200
    assert toggled.json()["is_active"] is False

    listed = client.get("/phone-numbers")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]

    assert client.delete(f"/phone-numbers/{data['id']}").status_code == 204


def test_phone_number_reassign_validates_agent(tenant):
    _, org, client = tenant
    agent_a = _make_agent(org, "A")
    agent_b = _make_agent(org, "B")
    number = client.post(
        "/phone-numbers", {"phone_number": "+15550001111", "agent_id": agent_a.id}
    ).json()

    reassigned = client.patch(
        f"/phone-numbers/{number['id']}", {"agent_id": agent_b.id}
    )
    assert reassigned.status_code == 200
    assert reassigned.json()["agent_id"] == agent_b.id

    assert (
        client.patch(f"/phone-numbers/{number['id']}", {"agent_id": 9999}).status_code
        == 404
    )


def test_phone_number_org_isolation(tenant, stranger):
    _, org, client = tenant
    _, _, other = stranger
    agent = _make_agent(org)
    number = client.post(
        "/phone-numbers", {"phone_number": "+15556667777", "agent_id": agent.id}
    ).json()

    assert other.get(f"/phone-numbers/{number['id']}").status_code == 404
    assert other.delete(f"/phone-numbers/{number['id']}").status_code == 404
    assert other.get("/phone-numbers").json() == []


TOKEN = "test-twilio-auth"


def _make_number(org, agent, phone="+14441110000"):
    return PhoneNumber.objects.create(
        organization=org,
        agent=agent,
        phone_number=phone,
        provider="twilio",
    )


def _make_conversation(org, agent, phone=None, call_sid="CA123"):
    if phone is None:
        phone = _make_number(org, agent)
    conversation = Conversation.objects.create(organization=org, agent=agent)
    PhoneCall.objects.create(
        conversation=conversation,
        phone_number=phone,
        caller_number="+15550001111",
        provider_call_id=call_sid,
        direction="INBOUND",
        provider_status=PhoneCallStatus.IN_PROGRESS,
    )
    return conversation


def test_twilio_signature_validation():
    from .providers.twilio import validate_twilio_signature

    url = "https://example.com/twilio/webhook/status"
    params = {"CallSid": "CA1", "CallStatus": "completed"}
    token = "secret"

    assert validate_twilio_signature(url, params, _sign(url, params, token), token)
    assert not validate_twilio_signature(url, params, _sign(url, params, "other"), token)
    assert not validate_twilio_signature(url, params, _sign(url, params, token), "other")
    assert not validate_twilio_signature(url, params, None, token)
    assert not validate_twilio_signature(url, params, _sign(url, params, token), "")


def test_twiml_builders_escape_and_shape():
    from .providers.twilio import (
        build_dial_twiml,
        build_gather_twiml,
        build_hangup_twiml,
    )

    gather = build_gather_twiml("How can I help?", "https://app.example/gather")
    assert '<Gather input="speech"' in gather
    assert 'action="https://app.example/gather"' in gather
    assert "<Say" in gather
    assert gather.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    assert "&lt;tag&gt;" in build_gather_twiml("a <tag>", "https://x/y")
    assert "</Dial>" in build_dial_twiml("+15550001111")
    assert build_hangup_twiml().endswith("<Response></Response>")


def test_resolve_phone_number_active_only(tenant):
    from .services import resolve_phone_number

    _, org, _ = tenant
    agent = _make_agent(org)
    active = _make_number(org, agent, phone="+14441110001")
    inactive = _make_number(org, agent, phone="+14441110002")
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])

    assert resolve_phone_number("+14441110001") == active
    assert resolve_phone_number("+14441110002") is None
    assert resolve_phone_number("+19990000000") is None


def test_create_inbound_call(tenant):
    from .services import create_inbound_call, resolve_phone_number

    _, org, _ = tenant
    agent = _make_agent(org)
    phone = _make_number(org, agent)

    conversation = create_inbound_call(phone, "+15550007777", "CAINBOUND")
    conversation.refresh_from_db()
    call = conversation.phone_call

    assert conversation.channel == "phone"
    assert conversation.agent_id == agent.id
    assert conversation.organization_id == org.id
    assert call.provider_call_id == "CAINBOUND"
    assert call.direction == "INBOUND"
    assert call.caller_number == "+15550007777"
    assert call.provider_status == PhoneCallStatus.RINGING
    assert conversation.customer.phone_number == "+15550007777"
    assert resolve_phone_number(call.phone_number.phone_number) == phone


def test_apply_provider_status_in_progress_and_completed(tenant, monkeypatch):
    from .services import apply_provider_status

    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)

    finalization = {}

    def fake_finalize(conversation):
        finalization["called"] = True
        conversation.summary = "handled"
        conversation.outcome = ConversationOutcome.INFORMATION_PROVIDED
        conversation.save(update_fields=["summary", "outcome"])
        return conversation

    monkeypatch.setattr("telephony.services.finalize_call", fake_finalize)

    assert apply_provider_status("CA123", "completed") == conversation
    conversation.refresh_from_db()
    assert conversation.status == "CLOSED"
    assert conversation.ended_at is not None
    assert conversation.phone_call.provider_status == PhoneCallStatus.COMPLETED
    assert conversation.summary == "handled"
    assert finalization["called"] is True

    # A second completed callback must not re-finalize
    monkeypatch.setattr("telephony.services.finalize_call", lambda c: conversation)
    assert apply_provider_status("CA123", "completed") == conversation


def test_apply_provider_status_failed_closes(tenant):
    from .services import apply_provider_status

    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)

    assert apply_provider_status("CA123", "busy") == conversation
    conversation.refresh_from_db()
    assert conversation.status == "CLOSED"
    assert conversation.phone_call.provider_status == PhoneCallStatus.FAILED


def test_apply_provider_status_does_not_downgrade_completed(tenant):
    from .services import apply_provider_status

    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    call = conversation.phone_call
    call.provider_status = PhoneCallStatus.COMPLETED
    call.save(update_fields=["provider_status"])

    assert apply_provider_status("CA123", "no-answer") == conversation
    conversation.refresh_from_db()
    assert conversation.phone_call.provider_status == PhoneCallStatus.COMPLETED


def test_apply_provider_status_unknowns(tenant, api_client):
    from .services import apply_provider_status

    assert apply_provider_status("", "completed") is None
    assert apply_provider_status("NOPE", "completed") is None

    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)
    assert apply_provider_status("CA123", "super-weird-status") == conversation
    conversation.refresh_from_db()
    assert conversation.phone_call.provider_status == PhoneCallStatus.IN_PROGRESS


def test_inbound_webhook_rejects_bad_signature(api_client):
    assert (
        api_client.post(
            "/telephony/webhook/inbound",
            {"To": "+1", "From": "+2"},
            format="multipart",
        ).status_code
        == 403
    )


def test_inbound_webhook_unknown_number_returns_hangup(api_client):
    params = {"To": "+14440000000", "From": "+15550001111", "CallSid": "CA000"}
    sig = _sign("http://testserver/telephony/webhook/inbound", params, TOKEN)

    with override_settings(TWILIO_AUTH_TOKEN=TOKEN):
        resp = api_client.post(
            "/telephony/webhook/inbound",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    assert b"<Response></Response>" in resp.content


def test_inbound_webhook_creates_conversation(tenant, api_client):
    _, org, _ = tenant
    agent = _make_agent(org)
    _make_number(org, agent)

    params = {"To": "+14441110000", "From": "+15550001111", "CallSid": "CAIN1"}
    sig = _sign("http://testserver/telephony/webhook/inbound", params, TOKEN)

    with override_settings(TWILIO_AUTH_TOKEN=TOKEN):
        resp = api_client.post(
            "/telephony/webhook/inbound",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )
        retry = api_client.post(
            "/telephony/webhook/inbound",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    assert b"<Gather input=\"speech\"" in resp.content
    assert retry.status_code == 200
    assert Conversation.objects.count() == 1

    conversation = Conversation.objects.get()
    assert conversation.phone_call.provider_call_id == "CAIN1"
    assert conversation.phone_call.direction == "INBOUND"
    assert conversation.phone_call.provider_status == PhoneCallStatus.RINGING
    assert conversation.customer.phone_number == "+15550001111"


def test_status_webhook_completed(tenant, api_client, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)

    monkeypatch.setattr(
        "telephony.services.finalize_call",
        lambda c: c,
    )

    params = {"CallSid": "CA123", "CallStatus": "completed"}
    sig = _sign("http://testserver/telephony/webhook/status", params, TOKEN)

    with override_settings(TWILIO_AUTH_TOKEN=TOKEN):
        resp = api_client.post(
            "/telephony/webhook/status",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    conversation.refresh_from_db()
    assert conversation.status == "CLOSED"
    assert conversation.phone_call.provider_status == PhoneCallStatus.COMPLETED


def test_status_webhook_requires_signature(api_client):
    assert (
        api_client.post(
            "/telephony/webhook/status",
            {"CallSid": "CA1", "CallStatus": "completed"},
            format="multipart",
        ).status_code
        == 403
    )


def test_gather_webhook_runs_agent_turn(tenant, api_client, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    conversation = _make_conversation(org, agent)

    calls = []

    def fake_turn(conversation, agent, text):
        calls.append((conversation.id, agent.id, text))
        return SimpleNamespace(response="Great, see you at 3 PM!")

    monkeypatch.setattr("telephony.webhooks.run_agent_turn", fake_turn)

    params = {"CallSid": "CA123", "From": "+15550001111", "SpeechResult": "book it"}
    sig = _sign("http://testserver/telephony/webhook/gather", params, TOKEN)

    with override_settings(TWILIO_AUTH_TOKEN=TOKEN):
        resp = api_client.post(
            "/telephony/webhook/gather",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    assert b"Great, see you at 3 PM!" in resp.content
    assert b"<Gather input=\"speech\"" in resp.content
    assert calls == [(conversation.id, agent.id, "book it")]
    assert conversation.messages.count() == 0


def test_gather_webhook_empty_speech_repeats(tenant, api_client, monkeypatch):
    _, org, _ = tenant
    agent = _make_agent(org)
    _make_conversation(org, agent)

    called = []
    monkeypatch.setattr(
        "telephony.webhooks.run_agent_turn",
        lambda c, a, t: called.append(t),
    )

    params = {"CallSid": "CA123", "SpeechResult": ""}
    sig = _sign("http://testserver/telephony/webhook/gather", params, TOKEN)

    with override_settings(TWILIO_AUTH_TOKEN=TOKEN):
        resp = api_client.post(
            "/telephony/webhook/gather",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    assert b"didn't catch that" in resp.content
    assert called == []


def test_gather_webhook_unknown_call_hangs_up(api_client):
    params = {"CallSid": "CA_MISSING", "SpeechResult": "hello"}
    sig = _sign("http://testserver/telephony/webhook/gather", params, TOKEN)

    with override_settings(TWILIO_AUTH_TOKEN=TOKEN):
        resp = api_client.post(
            "/telephony/webhook/gather",
            params,
            format="multipart",
            HTTP_X_TWILIO_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    assert b"<Response></Response>" in resp.content


def test_telephony_provider_factory_requires_credentials():
    from .providers.factory import get_telephony_provider

    with override_settings(TWILIO_ACCOUNT_SID="", TWILIO_AUTH_TOKEN="", TELEPHONY_PROVIDER="twilio"):
        try:
            get_telephony_provider()
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for missing Twilio credentials")


def test_telnyx_ed25519_signature_validation():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from .providers.telnyx import validate_telnyx_signature

    private_key = Ed25519PrivateKey.generate()
    public_key = base64.b64encode(
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
    ).decode()

    raw_body = b'{"data": {"event_type": "call.initiated"}}'
    timestamp = str(int(time.time()))
    signature = base64.b64encode(
        private_key.sign(f"{timestamp}|".encode() + raw_body)
    ).decode()

    other_pub = base64.b64encode(b"0" * 32).decode()

    assert validate_telnyx_signature(raw_body, signature, timestamp, public_key)
    assert not validate_telnyx_signature(raw_body + b"x", signature, timestamp, public_key)
    assert not validate_telnyx_signature(raw_body, signature, timestamp, other_pub)
    assert not validate_telnyx_signature(raw_body, "bm90LWEtc2ln", timestamp, public_key)
    assert not validate_telnyx_signature(raw_body, signature, "notanint", public_key)
    assert not validate_telnyx_signature(raw_body, signature, str(int(time.time()) - 3600), public_key)
    assert not validate_telnyx_signature(raw_body, None, timestamp, public_key)
    assert not validate_telnyx_signature(raw_body, signature, None, public_key)
    assert not validate_telnyx_signature(raw_body, signature, timestamp, "")


def test_telnyx_event_to_status():
    from .providers.telnyx import telnyx_event_to_status

    assert telnyx_event_to_status("call.initiated") == "ringing"
    assert telnyx_event_to_status("call.answered") == "in-progress"
    assert telnyx_event_to_status("call.hangup") == "completed"
    assert telnyx_event_to_status("call.machine.detection.ended") is None
    assert telnyx_event_to_status("") is None
    assert telnyx_event_to_status(None) is None


def test_telnyx_provider_create_call():
    from .providers.telnyx import TelnyxProvider

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"data": {"call_control_id": "CC123", "record_type": "call"}},
        )

    provider = TelnyxProvider(
        api_key="k",
        connection_id="conn",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    assert asyncio.run(provider.create_call("+15125550000", "+15550001111")) == "CC123"

    (req,) = requests
    assert req.method == "POST"
    assert req.url.path == "/v2/calls"
    assert req.headers["Authorization"] == "Bearer k"
    assert json.loads(req.content) == {
        "from": "+15125550000",
        "to": "+15550001111",
        "connection_id": "conn",
    }


def test_telnyx_provider_create_call_requires_connection(api_client):
    from .providers.telnyx import TelnyxProvider

    provider = TelnyxProvider(api_key="k", connection_id=None)
    try:
        asyncio.run(provider.create_call("+15125550000", "+15550001111"))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for missing connection_id")


def test_telnyx_provider_call_control_commands():
    from .providers.telnyx import TelnyxProvider

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"data": {"record_type": "call_control"}})

    provider = TelnyxProvider(
        api_key="k",
        connection_id="conn",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    asyncio.run(provider.end_call("CC123"))
    asyncio.run(provider.transfer_call("CC123", "+15550009999"))

    assert [r.url.path for r in requests] == [
        "/v2/calls/CC123/actions/hangup",
        "/v2/calls/CC123/actions/transfer",
    ]
    assert requests[1].content == b'{"to":"+15550009999"}'


def test_telnyx_provider_get_call():
    from .providers.telnyx import TelnyxProvider

    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/v2/calls/CC123"
        return httpx.Response(
            200,
            json={
                "data": {
                    "from": "+15125550000",
                    "to": "+15550001111",
                    "state": "active",
                    "record_type": "call",
                }
            },
        )

    provider = TelnyxProvider(
        api_key="k",
        connection_id="conn",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    call = asyncio.run(provider.get_call("CC123"))
    assert call.provider_call_id == "CC123"
    assert call.from_number == "+15125550000"
    assert call.to_number == "+15550001111"
    assert call.status == "active"


def test_telephony_provider_factory_telnyx():
    from .providers.factory import get_telephony_provider
    from .providers.telnyx import TelnyxProvider

    with override_settings(
        TELEPHONY_PROVIDER="telnyx",
        TELNYX_API_KEY="k",
        TELNYX_CONNECTION_ID="conn",
    ):
        provider = get_telephony_provider()

    assert isinstance(provider, TelnyxProvider)
    assert provider._api_key == "k"

    with override_settings(TELEPHONY_PROVIDER="telnyx", TELNYX_API_KEY=""):
        try:
            get_telephony_provider()
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for missing Telnyx API key")