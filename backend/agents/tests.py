import pytest

from ai.provider import LLMError

pytestmark = pytest.mark.django_db


def test_agents_require_auth(api_client):
    assert api_client.get("/agents").status_code == 401


def test_agent_create_list_patch_delete(tenant):
    user, org, client = tenant
    created = client.post(
        "/agents",
        {
            "name": "Support",
            "description": "Customer support",
            "system_prompt": "You are helpful.",
        },
    )
    assert created.status_code == 201
    agent = created.json()
    assert agent["name"] == "Support"
    assert agent["description"] == "Customer support"
    assert agent["system_prompt"] == "You are helpful."
    assert agent["organization_id"] == org.id
    assert agent["is_active"] is True
    assert "created_at" in agent and "updated_at" in agent

    listing = client.get("/agents")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [agent["id"]]

    patched = client.patch(f"/agents/{agent['id']}", {"is_active": False})
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False

    detail = client.get(f"/agents/{agent['id']}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Support"

    assert client.delete(f"/agents/{agent['id']}").status_code == 204
    assert client.get(f"/agents/{agent['id']}").status_code == 404


def test_agent_org_isolation(tenant, stranger):
    _, _, client = tenant
    _, _, other = stranger
    created = client.post(
        "/agents", {"name": "Mine", "system_prompt": "p"}
    ).json()

    assert other.get(f"/agents/{created['id']}").status_code == 404
    assert other.patch(f"/agents/{created['id']}", {"name": "Hijack"}).status_code == 404
    assert other.delete(f"/agents/{created['id']}").status_code == 404
    assert all(item["id"] != created["id"] for item in other.get("/agents").json())


def test_agent_create_validation(tenant):
    _, _, client = tenant
    assert client.post("/agents", {"name": "", "system_prompt": ""}).status_code == 400
    assert client.post("/agents", {"name": "NoPrompt"}).status_code == 400


class TestAgentChat:
    def test_chat_returns_response(self, tenant, monkeypatch):
        _, _, client = tenant
        agent = client.post(
            "/agents", {"name": "Front Desk", "system_prompt": "Be concise."}
        ).json()

        monkeypatch.setattr(
            "ai.agent.generate_response",
            lambda messages, tools=None: {
                "content": "Sure, what day works for you?",
                "tool_calls": [],
            },
        )

        response = client.post(
            f"/agents/{agent['id']}/chat",
            {"message": "I want an appointment"},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == agent["id"]
        assert data["message"] == "Sure, what day works for you?"

    def test_chat_org_isolation(self, tenant, stranger, monkeypatch):
        _, _, client = tenant
        _, _, other = stranger
        agent = client.post(
            "/agents", {"name": "Private", "system_prompt": "p"}
        ).json()

        monkeypatch.setattr(
            "ai.agent.generate_response",
            lambda messages, tools=None: {"content": "x", "tool_calls": []},
        )

        assert (
            other.post(
                f"/agents/{agent['id']}/chat", {"message": "hi"}, format="json"
            ).status_code
            == 404
        )

    def test_chat_llm_unavailable_returns_503(self, tenant, monkeypatch):
        _, _, client = tenant
        agent = client.post(
            "/agents", {"name": "Down", "system_prompt": "p"}
        ).json()

        def boom(messages, tools=None):
            raise LLMError("LLM down")

        monkeypatch.setattr("ai.agent.generate_response", boom)

        response = client.post(
            f"/agents/{agent['id']}/chat", {"message": "hi"}, format="json"
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "AI service is currently unavailable"

    def test_chat_invalid_message(self, tenant, monkeypatch):
        _, _, client = tenant
        agent = client.post(
            "/agents", {"name": "Strict", "system_prompt": "p"}
        ).json()
        assert (
            client.post(f"/agents/{agent['id']}/chat", {"message": ""}, format="json").status_code
            == 400
        )