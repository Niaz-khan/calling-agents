"""Runtime rendering of agent system-prompt templates.

Agent ``system_prompt`` values may contain ``{{variable}}`` placeholders that
are filled at conversation time with data from the agent and its organization.
This keeps the stored templates business-agnostic so the same template can
power many businesses without hardcoding their details.

The authoritative business facts (services, hours, knowledge) are still
resolved by tools at runtime; the renderer only injects stable business/agent
metadata into the prompt text. Any leftover unknown placeholders are blanked so
they never leak bare ``{{...}}`` tokens into the prompt.
"""

import re

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def _render_business_hours(business_hours):
    """Render the JSON weekly schedule dict into a readable multi-line string."""
    if not business_hours:
        return "Always open (no fixed schedule configured)."
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    lines = []
    for weekday in range(1, 8):
        slot = business_hours.get(str(weekday)) or business_hours.get(weekday)
        if not slot:
            continue
        start = slot.get("start")
        end = slot.get("end")
        if start and end:
            lines.append(f"{days[weekday - 1]}: {start} - {end}")
    if not lines:
        return "Always open (no fixed schedule configured)."
    return "\n".join(lines)


def _render_services(organization):
    from apps.services.models import Service

    services = Service.objects.filter(organization=organization, active=True)
    if not services:
        return "No services have been configured yet."
    lines = []
    for service in services:
        parts = [service.name]
        if service.duration_minutes:
            parts.append(f"{service.duration_minutes} minutes")
        if service.price is not None:
            parts.append(f"{service.currency} {service.price}")
        lines.append(
            f"- {', '.join(parts)}"
            + (f" — {service.description}" if service.description else "")
        )
    return "\n".join(lines)


def _variables_for(agent, organization):
    return {
        "agent_name": agent.name or "",
        "business_name": organization.display_name,
        "business_description": organization.name or "",
        "website": organization.website_url or "",
        "address": organization.address or "",
        "business_phone": organization.contact_phone or "",
        "timezone": organization.timezone or "UTC",
        "business_hours": _render_business_hours(organization.business_hours),
        "services": _render_services(organization),
        # Knowledge is resolved via the search_knowledge_base tool at runtime,
        # so this slot holds guidance rather than an embedded document blob.
        "knowledge_context": (
            "Use the knowledge base/search tool for business facts (FAQ, "
            "policies, details). Only report information the tool actually "
            "returns."
        ),
    }


def render_prompt(system_prompt, agent, organization):
    """Fill all ``{{placeholders}}`` in ``system_prompt`` from an agent+org.

    Unknown placeholders are replaced with an empty string so no literal
    template tokens reach the LLM.
    """
    if not system_prompt:
        return system_prompt

    variables = _variables_for(agent, organization)

    def _substitute(match):
        return variables.get(match.group(1), "")

    return _PLACEHOLDER_RE.sub(_substitute, system_prompt)
