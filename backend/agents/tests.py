import pytest

from tenancy.models import Organization

from .models import Agent, AgentDeployment, generate_public_identifier

pytestmark = pytest.mark.django_db

_URLSAFE = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org")


def test_agent_requires_organization(org):
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    assert agent.organization_id == org.id
    assert agent.is_active is True


def test_public_identifier_is_unique_and_opaque():
    ids = {generate_public_identifier() for _ in range(300)}
    assert len(ids) == 300
    assert all(len(i) == 22 for i in ids)
    assert all(set(i) <= _URLSAFE for i in ids)


def test_resolve_public_returns_deployment(org):
    agent = Agent.objects.create(organization=org, name="W", system_prompt="p")
    dep = AgentDeployment.objects.create(
        organization=org,
        agent=agent,
        channel=AgentDeployment.Channel.WEBSITE,
        allowed_domains=["https://example.com"],
    )
    resolved = AgentDeployment.objects.resolve_public(
        dep.public_identifier, channel=AgentDeployment.Channel.WEBSITE
    )
    assert resolved is not None
    assert resolved.pk == dep.pk
    assert resolved.organization_id == org.id
    assert resolved.agent_id == agent.id
    assert resolved.allowed_domains == ["https://example.com"]


def test_resolve_public_unknown_token_is_none(org):
    assert AgentDeployment.objects.resolve_public("no-such-token") is None


def test_resolve_public_respects_channel(org):
    agent = Agent.objects.create(organization=org, name="W", system_prompt="p")
    dep = AgentDeployment.objects.create(
        organization=org, agent=agent, channel=AgentDeployment.Channel.API
    )
    assert (
        AgentDeployment.objects.resolve_public(
            dep.public_identifier, channel=AgentDeployment.Channel.WEBSITE
        )
        is None
    )
    assert (
        AgentDeployment.objects.resolve_public(
            dep.public_identifier, channel=AgentDeployment.Channel.API
        )
        is not None
    )


def test_resolve_public_rejects_disabled_and_inactive(org):
    agent = Agent.objects.create(organization=org, name="W", system_prompt="p")
    dep = AgentDeployment.objects.create(organization=org, agent=agent)

    dep.enabled = False
    dep.save()
    assert AgentDeployment.objects.resolve_public(dep.public_identifier) is None

    dep.enabled = True
    dep.save()
    agent.is_active = False
    agent.save()
    assert AgentDeployment.objects.resolve_public(dep.public_identifier) is None

    agent.is_active = True
    agent.save()
    org.is_active = False
    org.save()
    assert AgentDeployment.objects.resolve_public(dep.public_identifier) is None


def test_deployments_share_one_agent(org):
    """Multiple channels deploy the SAME agent configuration."""
    agent = Agent.objects.create(organization=org, name="Universal", system_prompt="p")
    for channel in AgentDeployment.Channel.values:
        AgentDeployment.objects.create(organization=org, agent=agent, channel=channel)
    assert agent.deployments.count() == len(AgentDeployment.Channel.values)
    assert set(agent.deployments.values_list("channel", flat=True)) == set(
        AgentDeployment.Channel.values
    )