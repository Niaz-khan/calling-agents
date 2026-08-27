from datetime import timedelta

import pytest
from django.utils import timezone

from agents.models import Agent

pytestmark = pytest.mark.django_db


def _agent(org):
    return Agent.objects.create(organization=org, name="Billing", system_prompt="p")


def _times(start_delta=1, end_delta=2):
    now = timezone.now()
    return now + timedelta(days=start_delta), now + timedelta(days=end_delta)


def _base_payload(agent, start=None, end=None):
    start, end = start or _times()[0], end or _times()[1]
    return {
        "agent_id": agent.id,
        "customer_name": "Alice",
        "customer_phone": "+15557778888",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "notes": "Remote",
    }


def test_appointments_require_auth(api_client):
    assert api_client.get("/appointments").status_code == 401


def test_appointment_create_list_status_update(tenant):
    _, org, client = tenant
    agent = _agent(org)

    missing = client.post(
        "/appointments",
        {**_base_payload(agent), "agent_id": 9999},
    )
    assert missing.status_code == 404

    created = client.post("/appointments", _base_payload(agent))
    assert created.status_code == 201
    data = created.json()
    assert data["status"] == "scheduled"
    assert data["call_id"] is None
    assert data["agent_id"] == agent.id

    listed = client.get("/appointments")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]

    filtered = client.get("/appointments?status_filter=scheduled")
    assert [item["id"] for item in filtered.json()] == [data["id"]]
    assert client.get("/appointments?status_filter=cancelled").json() == []

    cancelled = client.patch(f"/appointments/{data['id']}", {"status": "cancelled"})
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    assert client.get("/appointments?status_filter=cancelled").json()[0]["id"] == data["id"]


def test_appointment_time_validation(tenant):
    _, org, client = tenant
    agent = _agent(org)
    start, end = _times()
    payload = {**_base_payload(agent, end, start)}
    resp = client.post("/appointments", payload)
    assert resp.status_code == 400


def test_appointment_overlap_is_conflict(tenant):
    _, org, client = tenant
    agent = _agent(org)
    first = client.post("/appointments", _base_payload(agent))
    assert first.status_code == 201

    start, end = _times()
    overlap = client.post(
        "/appointments", _base_payload(agent, start + timedelta(minutes=30), end + timedelta(minutes=30))
    )
    assert overlap.status_code == 409
    assert overlap.json()["detail"] == "The requested time is not available"

    adjacent = client.post(
        "/appointments", _base_payload(agent, end, end + timedelta(hours=2))
    )
    assert adjacent.status_code == 201


def test_appointment_delete_and_isolation(tenant, stranger):
    _, org, client = tenant
    _, _, other = stranger
    agent = _agent(org)
    created = client.post("/appointments", _base_payload(agent)).json()

    assert other.get(f"/appointments/{created['id']}").status_code == 404
    assert other.patch(f"/appointments/{created['id']}", {"status": "cancelled"}).status_code == 404
    assert other.delete(f"/appointments/{created['id']}").status_code == 404

    assert client.delete(f"/appointments/{created['id']}").status_code == 204
    assert client.get(f"/appointments/{created['id']}").status_code == 404