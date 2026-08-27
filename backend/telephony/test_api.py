import pytest

from agents.models import Agent

pytestmark = pytest.mark.django_db


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