import pytest

from apps.agents.models import Agent
from apps.ai.prompt_render import render_prompt
from apps.services.models import Service
from apps.tenancy.models import Organization

pytestmark = pytest.mark.django_db


def _org_agent():
    org = Organization.objects.create(
        name="Acme Org",
        business_name="Acme Realty",
        contact_phone="+15551234567",
        address="1 Main St",
        website_url="https://acme.example",
        timezone="UTC",
        business_hours={"1": {"start": "09:00", "end": "17:00"}},
    )
    agent = Agent.objects.create(
        organization=org, name="Receptionist", system_prompt="prompt"
    )
    Service.objects.create(
        organization=org, name="Viewing", duration_minutes=30, price="50.00"
    )
    return org, agent


def test_renders_known_placeholders():
    org, agent = _org_agent()
    out = render_prompt(
        "Hi {{agent_name}} of {{business_name}} at {{business_phone}} ({{timezone}}).",
        agent,
        org,
    )
    assert out == "Hi Receptionist of Acme Realty at +15551234567 (UTC)."


def test_renders_business_hours_and_services():
    org, agent = _org_agent()
    out = render_prompt(
        "Hours:\n{{business_hours}}\n\nServices:\n{{services}}",
        agent,
        org,
    )
    assert "Monday: 09:00 - 17:00" in out
    assert "Viewing" in out
    assert "30 minutes" in out
    assert "50.00" in out


def test_unknown_placeholder_blanked():
    org, agent = _org_agent()
    out = render_prompt("Before {{nope}} after", agent, org)
    assert out == "Before  after"
    assert "{{" not in out


def test_none_prompt_returns_none():
    org, agent = _org_agent()
    assert render_prompt(None, agent, org) is None
