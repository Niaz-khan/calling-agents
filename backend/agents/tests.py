import pytest

from ai.provider import LLMError

from .models import AgentDeployment

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


class TestDeployments:
    def test_deployments_require_auth(self, api_client):
        assert api_client.get("/deployments").status_code == 401

    def test_deployment_crud(self, tenant):
        _, org, client = tenant
        agent = client.post(
            "/agents", {"name": "Receptionist", "system_prompt": "p"}
        ).json()

        bad = client.post("/deployments", {"agent_id": 9999, "channel": "website"})
        assert bad.status_code == 400

        created = client.post(
            "/deployments",
            {
                "agent_id": agent["id"],
                "channel": "website",
                "name": "Main site",
                "allowed_domains": ["acme.com", "www.acme.com"],
            },
        )
        assert created.status_code == 201
        data = created.json()
        assert data["organization_id"] == org.id
        assert data["agent_id"] == agent["id"]
        assert data["agent_name"] == "Receptionist"
        assert data["public_identifier"].startswith("pub_")
        assert data["enabled"] is True
        assert data["allowed_domains"] == ["acme.com", "www.acme.com"]
        assert "system_prompt" not in data

        listing = client.get(f"/deployments?agent_id={agent['id']}")
        assert listing.status_code == 200
        assert [d["id"] for d in listing.json()] == [data["id"]]

        patched = client.patch(
            f"/deployments/{data['id']}", {"enabled": False, "allowed_domains": []}
        )
        assert patched.status_code == 200
        assert patched.json()["enabled"] is False
        assert patched.json()["allowed_domains"] == []

        assert client.delete(f"/deployments/{data['id']}").status_code == 204

    def test_deployment_org_isolation(self, tenant, stranger):
        _, _, client = tenant
        _, _, other = stranger
        agent = client.post(
            "/agents", {"name": "Private", "system_prompt": "p"}
        ).json()
        dep = client.post(
            "/deployments", {"agent_id": agent["id"], "channel": "website"}
        ).json()

        assert other.get(f"/deployments/{dep['id']}").status_code == 404
        assert other.patch(f"/deployments/{dep['id']}", {"name": "X"}).status_code == 404
        assert other.delete(f"/deployments/{dep['id']}").status_code == 404
        assert (
            other.post("/deployments", {"agent_id": agent["id"], "channel": "website"}).status_code
            == 400
        )


class TestPublicChat:
    def _deployment(self, org, **kwargs):
        from agents.models import Agent

        agent = Agent.objects.create(
            organization=org, name="Receptionist", system_prompt="p"
        )
        defaults = {"channel": AgentDeployment.Channel.WEBSITE}
        defaults.update(kwargs)
        return AgentDeployment.objects.create(organization=org, agent=agent, **defaults)

    def test_unknown_deployment_returns_404(self, tenant, api_client):
        _, _, _ = tenant
        assert api_client.post("/public/chat/pub_missing", {"message": "hi"}).status_code == 404

    def test_disabled_deployment_returns_404(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org, enabled=False)
        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
        )
        assert resp.status_code == 404

    def test_non_public_channel_returns_404(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org, channel=AgentDeployment.Channel.PHONE)
        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
        )
        assert resp.status_code == 404

    def test_requires_visitor_id_and_message(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org)

        no_visitor = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
        )
        assert no_visitor.status_code == 400

        no_message = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": ""},
            format="json",
            HTTP_X_VISITOR_ID="v",
        )
        assert no_message.status_code == 400

    def test_chat_creates_website_conversation(self, tenant, api_client, monkeypatch):
        from conversations.models import Conversation, ConversationMessage

        _, org, _ = tenant
        deployment = self._deployment(org)
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "Gladly. What day works for you?",
            "tool_calls": [],
        })

        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "I want an appointment"},
            format="json",
            HTTP_X_VISITOR_ID="vis-1",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["visitor_id"] == "vis-1"
        assert data["message"] == "Gladly. What day works for you?"

        conversation = Conversation.objects.get(id=data["conversation_id"])
        assert conversation.channel == "website"
        assert conversation.organization_id == org.id
        assert conversation.agent_id == deployment.agent_id
        assert conversation.deployment_id == deployment.id
        assert conversation.visitor_id == "vis-1"

        roles = list(conversation.messages.values_list("role", flat=True))
        assert roles == ["USER", "ASSISTANT"]
        assert (
            conversation.messages.get(role="USER").content == "I want an appointment"
        )

    def test_reuses_open_conversation_for_same_visitor(self, tenant, api_client, monkeypatch):
        from conversations.models import Conversation

        _, org, _ = tenant
        deployment = self._deployment(org)
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "ok", "tool_calls": []
        })

        first = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hello"},
            format="json",
            HTTP_X_VISITOR_ID="vis-1",
        ).json()
        second = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "still here"},
            format="json",
            HTTP_X_VISITOR_ID="vis-1",
        ).json()

        assert first["conversation_id"] == second["conversation_id"]
        assert Conversation.objects.filter(
            deployment=deployment, visitor_id="vis-1"
        ).count() == 1

    def test_new_visitor_starts_new_conversation(self, tenant, api_client, monkeypatch):
        from conversations.models import Conversation

        _, org, _ = tenant
        deployment = self._deployment(org)
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "ok", "tool_calls": []
        })

        a = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="a",
        ).json()
        b = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="b",
        ).json()

        assert a["conversation_id"] != b["conversation_id"]
        assert Conversation.objects.filter(deployment=deployment).count() == 2

    def test_history_returns_transcript(self, tenant, api_client, monkeypatch):
        _, org, _ = tenant
        deployment = self._deployment(org)
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "Sure, at 3 PM.", "tool_calls": []
        })

        chat = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "book me for 3pm"},
            format="json",
            HTTP_X_VISITOR_ID="vis-1",
        ).json()

        history = api_client.get(
            f"/public/chat/{deployment.public_identifier}",
            HTTP_X_VISITOR_ID="vis-1",
        )
        assert history.status_code == 200
        data = history.json()
        assert data["conversation_id"] == chat["conversation_id"]
        assert data["messages"] == [
            {"role": "user", "content": "book me for 3pm"},
            {"role": "assistant", "content": "Sure, at 3 PM."},
        ]

    def test_llm_error_returns_503(self, tenant, api_client, monkeypatch):
        def boom(conversation, agent, text):
            raise LLMError("down")

        monkeypatch.setattr("agents.public.run_agent_turn", boom)

        _, org, _ = tenant
        deployment = self._deployment(org)
        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "AI service is currently unavailable"

    def test_allowed_domains_are_enforced(self, tenant, api_client, monkeypatch):
        _, org, _ = tenant
        deployment = self._deployment(org, allowed_domains=["acme.com"])
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "ok", "tool_calls": []
        })

        blocked = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
            HTTP_ORIGIN="https://evil.com",
        )
        assert blocked.status_code == 403

        allowed = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
            HTTP_ORIGIN="https://acme.com",
        )
        assert allowed.status_code == 200
        assert allowed["Access-Control-Allow-Origin"] == "https://acme.com"

    def test_empty_allowed_domains_allows_any_origin(self, tenant, api_client, monkeypatch):
        _, org, _ = tenant
        deployment = self._deployment(org, allowed_domains=[])
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "ok", "tool_calls": []
        })

        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
            HTTP_ORIGIN="https://anything.test",
        )
        assert resp.status_code == 200
        assert resp["Access-Control-Allow-Origin"] == "https://anything.test"

    def test_api_channel_ignores_domain_restriction(self, tenant, api_client, monkeypatch):
        _, org, _ = tenant
        deployment = self._deployment(
            org, channel=AgentDeployment.Channel.API, allowed_domains=["acme.com"]
        )
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "ok", "tool_calls": []
        })

        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "hi"},
            format="json",
            HTTP_X_VISITOR_ID="v",
            HTTP_ORIGIN="https://anywhere.else",
        )
        assert resp.status_code == 200
        assert resp.json()["conversation_id"] is not None

    def test_preflight_returns_cors_headers(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org, allowed_domains=["acme.com"])

        resp = api_client.options(
            f"/public/chat/{deployment.public_identifier}",
            HTTP_ORIGIN="https://acme.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert resp.status_code == 200
        assert resp["Access-Control-Allow-Origin"] == "https://acme.com"
        assert "POST" in resp["Access-Control-Allow-Methods"]

        blocked = api_client.options(
            f"/public/chat/{deployment.public_identifier}",
            HTTP_ORIGIN="https://evil.com",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert blocked.status_code == 403

    def test_message_too_long_returns_400(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org)
        resp = api_client.post(
            f"/public/chat/{deployment.public_identifier}",
            {"message": "x" * 2001},
            format="json",
            HTTP_X_VISITOR_ID="v",
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "message is too long"

    def test_throttling_returns_429(self, tenant, api_client, monkeypatch):
        import agents.public as public_module

        _, org, _ = tenant
        deployment = self._deployment(org)
        monkeypatch.setattr("agents.public.THROTTLE_LIMIT_PER_WINDOW", 3)
        monkeypatch.setattr("agents.public.THROTTLE_WINDOW_SECONDS", 3600)
        monkeypatch.setattr("ai.agent.generate_response", lambda messages, tools=None: {
            "content": "ok", "tool_calls": []
        })

        url = f"/public/chat/{deployment.public_identifier}"
        for _ in range(3):
            assert api_client.post(
                url, {"message": "hi"}, format="json", HTTP_X_VISITOR_ID="v-rt"
            ).status_code == 200

        limited = api_client.post(
            url, {"message": "hi"}, format="json", HTTP_X_VISITOR_ID="v-rt"
        )
        assert limited.status_code == 429
        data = limited.json()
        assert data["detail"] == "Too many requests"
        assert int(data["retry_after"]) >= 1
        assert int(limited["Retry-After"]) >= 1


class TestWidgetConfig:
    def _deployment(self, org, **kwargs):
        from agents.models import Agent

        agent = Agent.objects.create(
            organization=org, name="Receptionist", system_prompt="p"
        )
        defaults = {"channel": AgentDeployment.Channel.WEBSITE}
        defaults.update(kwargs)
        return AgentDeployment.objects.create(organization=org, agent=agent, **defaults)

    def test_config_unknown_or_phone_returns_404(self, tenant, api_client):
        _, org, _ = tenant
        assert api_client.get("/public/config/pub_missing").status_code == 404

        phone = self._deployment(org, channel=AgentDeployment.Channel.PHONE)
        assert (
            api_client.get(f"/public/config/{phone.public_identifier}").status_code == 404
        )

    def test_config_returns_branding(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(
            org,
            widget_title="Acme Support",
            widget_primary_color="#0F766E",
            welcome_message="Hi! Ask me about appointments.",
            allowed_domains=["acme.com"],
        )
        resp = api_client.get(
            f"/public/config/{deployment.public_identifier}",
            HTTP_ORIGIN="https://acme.com",
        )
        assert resp.status_code == 200
        assert resp["Access-Control-Allow-Origin"] == "https://acme.com"
        data = resp.json()
        assert data["identifier"] == deployment.public_identifier
        assert data["agent"] == {"name": "Receptionist"}
        assert data["title"] == "Acme Support"
        assert data["primary_color"] == "#0F766E"
        assert data["welcome_message"] == "Hi! Ask me about appointments."
        assert data["online"] is True

    def test_config_defaults_when_unset(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org)
        data = api_client.get(
            f"/public/config/{deployment.public_identifier}"
        ).json()
        assert data["title"] == "Receptionist"
        assert data["primary_color"] == "#4f46e5"
        assert data["welcome_message"] == ""

    def test_config_rejects_disallowed_origin(self, tenant, api_client):
        _, org, _ = tenant
        deployment = self._deployment(org, allowed_domains=["acme.com"])
        blocked = api_client.get(
            f"/public/config/{deployment.public_identifier}",
            HTTP_ORIGIN="https://evil.com",
        )
        assert blocked.status_code == 403


def test_deployment_branding_validation(tenant):
    _, _, client = tenant
    agent = client.post(
        "/agents", {"name": "Branded", "system_prompt": "p"}
    ).json()
    created = client.post(
        "/deployments",
        {
            "agent_id": agent["id"],
            "channel": "website",
            "widget_title": "Acme",
            "widget_primary_color": "#0F766E",
            "welcome_message": "Hello!",
        },
    )
    assert created.status_code == 201
    assert created.json()["widget_title"] == "Acme"
    assert created.json()["widget_primary_color"] == "#0F766E"
    assert created.json()["welcome_message"] == "Hello!"

    bad = client.post(
        "/deployments",
        {
            "agent_id": agent["id"],
            "channel": "website",
            "widget_primary_color": "not-a-color",
        },
    )
    assert bad.status_code == 400


def test_widget_endpoints():
    from django.test import Client as DjangoClient

    client = DjangoClient()
    js = client.get("/widget.js")
    assert js.status_code == 200
    assert js["Content-Type"].startswith("application/javascript")
    assert "dataset.agent" in js.content.decode()
    assert "/public/chat/" in js.content.decode()
    assert "/public/config/" in js.content.decode()
    assert "--ai-primary" in js.content.decode()

    page = client.get("/widget")
    assert page.status_code == 200
    assert b"/widget.js" in page.content
    assert b"Widget Demo" in page.content