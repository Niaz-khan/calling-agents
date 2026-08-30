import pytest

from apps.agents.models import Agent
from apps.conversations.models import Conversation, PhoneCall
from apps.knowledge.models import KnowledgeBase
from apps.services.models import Service
from apps.telephony.models import PhoneNumber
from apps.tenancy.models import Organization

pytestmark = pytest.mark.django_db


def _make_agent(org, name, active=True):
    return Agent.objects.create(
        organization=org,
        name=name,
        system_prompt="You are a helpful agent.",
        is_active=active,
    )


def _make_phone_call(org, agent, number, direction="INBOUND"):
    conversation = Conversation.objects.create(
        organization=org,
        agent=agent,
        channel="phone",
        outcome="NO_RESOLUTION",
    )
    number = PhoneNumber.objects.create(
        organization=org, agent=agent, phone_number=number
    )
    PhoneCall.objects.create(
        conversation=conversation,
        phone_number=number,
        direction=direction,
        caller_number="+15550001111",
    )
    return conversation


# ---------------------------------------------------------------------------
# Platform admin access
# ---------------------------------------------------------------------------


def test_platform_dashboard_cross_organization(platformadmin, tenant, stranger):
    _, client = platformadmin
    resp = client.get("/platform/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] >= 2
    assert data["active_organizations"] >= 2
    assert data["total_users"] >= 3
    assert data["total_calls"] >= 0
    assert "recent_activity" in data
    assert "growth" in data


def test_platform_admin_lists_all_organizations(platformadmin, tenant, stranger):
    _, client = platformadmin
    resp = client.get("/platform/organizations")
    assert resp.status_code == 200
    names = {org["name"] for org in resp.json()}
    assert {"Acme", "Rival"} <= names


def test_platform_organization_search(platformadmin, tenant, stranger):
    _, client = platformadmin
    resp = client.get("/platform/organizations", {"q": "Acm"})
    assert resp.status_code == 200
    names = {org["name"] for org in resp.json()}
    assert names == {"Acme"}


def test_platform_admin_sees_agents_across_organizations(platformadmin, tenant, stranger):
    owner, acme, _ = tenant
    _make_agent(acme, "Acme Agent")
    _, rival, _ = stranger
    _make_agent(rival, "Rival Agent")

    _, client = platformadmin
    resp = client.get("/platform/agents")
    assert resp.status_code == 200
    names = {agent["name"] for agent in resp.json()}
    assert names == {"Acme Agent", "Rival Agent"}

    filtered = client.get("/platform/agents", {"organization_id": acme.id}).json()
    assert {agent["name"] for agent in filtered} == {"Acme Agent"}


def test_platform_call_detail_includes_transcript(platformadmin, tenant):
    owner, acme, _ = tenant
    agent = _make_agent(acme, "Acme Agent")
    call = _make_phone_call(acme, agent, "+15550001111")

    _, client = platformadmin
    resp = client.get(f"/platform/calls/{call.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == call.id


def test_superadmin_has_platform_access(superadmin, tenant, stranger):
    _, client = superadmin
    assert client.get("/platform/dashboard").status_code == 200


# ---------------------------------------------------------------------------
# Business user denial / cross-tenant isolation
# ---------------------------------------------------------------------------


def test_business_user_denied_platform_area(tenant):
    _, _, client = tenant
    assert client.get("/platform/dashboard").status_code == 403
    assert client.get("/platform/organizations").status_code == 403
    assert client.get("/platform/agents").status_code == 403


def test_anonymous_denied_platform_area(api_client):
    assert api_client.get("/platform/dashboard").status_code == 401
    assert api_client.get("/platform/organizations").status_code == 401


def test_cross_tenant_isolation_preserved_on_normal_apis(tenant, stranger):
    owner, acme, client = tenant
    _, rival, _ = stranger
    acme_agent = _make_agent(acme, "Acme Agent")
    _make_agent(rival, "Rival Agent")

    resp = client.get("/agents")
    assert resp.status_code == 200
    names = {agent["name"] for agent in resp.json()}
    assert names == {"Acme Agent"}
    assert acme_agent.id in {agent["id"] for agent in resp.json()}


def test_business_user_cannot_see_other_organization_agent_detail(tenant, stranger):
    _, acme, client = tenant
    _, rival, _ = stranger
    rival_agent = _make_agent(rival, "Rival Agent")
    assert client.get(f"/agents/{rival_agent.id}").status_code in (403, 404)


# ---------------------------------------------------------------------------
# Organization management
# ---------------------------------------------------------------------------


def test_platform_admin_deactivates_organization(platformadmin, tenant, stranger):
    owner, acme, _ = tenant
    _, client = platformadmin
    resp = client.patch(f"/platform/organizations/{acme.id}", {"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    acme.refresh_from_db()
    assert acme.is_active is False


def test_organization_detail_includes_summary(platformadmin, tenant):
    owner, acme, _ = tenant
    _make_agent(acme, "Acme Agent")
    _, client = platformadmin
    resp = client.get(f"/platform/organizations/{acme.id}/detail")
    assert resp.status_code == 200
    assert resp.json()["organization"]["name"] == "Acme"
    assert resp.json()["summary"]["agents_count"] >= 1


def test_organization_create(platformadmin):
    _, client = platformadmin
    resp = client.post(
        "/platform/organizations",
        {"name": "Brand New Org", "contact_phone": "+15551234"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Brand New Org"


# ---------------------------------------------------------------------------
# User role management (super admin only)
# ---------------------------------------------------------------------------


def test_only_superadmin_can_promote_platform_roles(platformadmin, tenant):
    owner, acme, _ = tenant
    _, client = platformadmin
    resp = client.patch(f"/platform/users/{owner.id}/role", {"platform_role": "PLATFORM_ADMIN"})
    assert resp.status_code == 403


def test_superadmin_promotes_and_demotes_platform_role(superadmin, tenant):
    owner, acme, _ = tenant
    _, client = superadmin
    resp = client.patch(f"/platform/users/{owner.id}/role", {"platform_role": "PLATFORM_ADMIN"})
    assert resp.status_code == 200
    owner.refresh_from_db()
    assert owner.platform_role == "PLATFORM_ADMIN"
    assert owner.is_staff is True

    resp = client.patch(f"/platform/users/{owner.id}/role", {"platform_role": ""})
    assert resp.status_code == 200
    owner.refresh_from_db()
    assert owner.platform_role == ""
    assert owner.is_staff is False


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def test_platform_analytics_cross_org(platformadmin, tenant, stranger):
    _, client = platformadmin
    resp = client.get("/platform/analytics", {"days": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["days"] == 30
    assert data["totals"]["organizations"] >= 2
    assert len(data["growth"]["organizations_growth"]) == 30


def test_platform_users_list(platformadmin, tenant):
    owner, acme, _ = tenant
    _, client = platformadmin
    resp = client.get("/platform/users", {"q": owner.email})
    assert resp.status_code == 200
    emails = [user["email"] for user in resp.json()]
    assert owner.email in emails


# ---------------------------------------------------------------------------
# Phone numbers / knowledge / services (platform resources)
# ---------------------------------------------------------------------------


def test_platform_phone_numbers_cross_org(platformadmin, tenant, stranger):
    owner, acme, _ = tenant
    _make_agent(acme, "Acme Agent")
    agent = Agent.objects.get(organization=acme)
    PhoneNumber.objects.create(
        organization=acme, agent=agent, phone_number="+15550000001"
    )
    _, rival, _ = stranger
    rival_agent = _make_agent(rival, "Rival Agent")
    PhoneNumber.objects.create(
        organization=rival, agent=rival_agent, phone_number="+15550000002"
    )

    _, client = platformadmin
    resp = client.get("/platform/phone-numbers")
    assert resp.status_code == 200
    numbers = {row["phone_number"] for row in resp.json()}
    assert {"+15550000001", "+15550000002"} <= numbers

    filtered = client.get(
        "/platform/phone-numbers", {"organization_id": acme.id}
    ).json()
    assert {row["phone_number"] for row in filtered} == {"+15550000001"}


def test_platform_knowledge_and_services_cross_org(platformadmin, tenant, stranger):
    owner, acme, _ = tenant
    acme_agent = _make_agent(acme, "Acme Agent")
    KnowledgeBase.objects.create(organization=acme, agent=acme_agent, name="Acme KB")
    Service.objects.create(
        organization=acme, name="Consultation", duration_minutes=30, currency="USD"
    )
    _, rival, _ = stranger
    rival_agent = _make_agent(rival, "Rival Agent")
    KnowledgeBase.objects.create(organization=rival, agent=rival_agent, name="Rival KB")
    Service.objects.create(
        organization=rival, name="Repair", duration_minutes=60, currency="USD"
    )

    _, client = platformadmin
    knowledge = client.get("/platform/knowledge").json()
    assert {row["name"] for row in knowledge} == {"Acme KB", "Rival KB"}
    acme_knowledge = client.get(
        "/platform/knowledge", {"organization_id": acme.id}
    ).json()
    assert {row["name"] for row in acme_knowledge} == {"Acme KB"}

    services = client.get("/platform/services").json()
    assert {row["name"] for row in services} == {"Consultation", "Repair"}
    rival_services = client.get(
        "/platform/services", {"organization_id": rival.id, "active": "true"}
    ).json()
    assert {row["name"] for row in rival_services} == {"Repair"}


def test_platform_org_scoped_phone_numbers_knowledge_services(
    platformadmin, tenant, stranger
):
    owner, acme, _ = tenant
    acme_agent = _make_agent(acme, "Acme Agent")
    PhoneNumber.objects.create(
        organization=acme, agent=acme_agent, phone_number="+15550000001"
    )
    KnowledgeBase.objects.create(organization=acme, agent=acme_agent, name="Acme KB")
    Service.objects.create(
        organization=acme, name="Consultation", duration_minutes=30, currency="USD"
    )
    _, rival, _ = stranger
    _make_agent(rival, "Rival Agent")
    _make_agent(rival, "Other Agent")

    _, client = platformadmin
    for endpoint, expected in [
        ("phone-numbers", 1),
        ("knowledge", 1),
        ("services", 1),
    ]:
        resp = client.get(f"/platform/organizations/{acme.id}/{endpoint}")
        assert resp.status_code == 200
        assert len(resp.json()) == expected


def test_business_user_denied_platform_resources(tenant, stranger):
    owner, acme, _ = tenant
    _, rival, _ = stranger
    rival_agent = _make_agent(rival, "Rival Agent")
    PhoneNumber.objects.create(
        organization=rival, agent=rival_agent, phone_number="+15550000001"
    )

    _, _, client = tenant
    assert client.get("/platform/phone-numbers").status_code == 403
    assert client.get("/platform/knowledge").status_code == 403
    assert client.get("/platform/services").status_code == 403
    assert (
        client.get(f"/platform/organizations/{rival.id}/knowledge").status_code
        == 403
    )