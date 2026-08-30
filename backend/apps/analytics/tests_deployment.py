import json
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.agents.models import Agent, AgentDeployment
from apps.appointments.models import Appointment
from apps.conversations.models import (
    Conversation,
    ConversationChannel,
    ConversationMessage,
)

pytestmark = pytest.mark.django_db


def _deployment(org, **kwargs):
    agent = Agent.objects.create(
        organization=org, name="Receptionist", system_prompt="p"
    )
    defaults = {"channel": AgentDeployment.Channel.WEBSITE}
    defaults.update(kwargs)
    return AgentDeployment.objects.create(organization=org, agent=agent, **defaults)


def _conversation(org, deployment, start=None, visitor_id=None):
    return Conversation.objects.create(
        organization=org,
        agent=deployment.agent,
        deployment=deployment,
        channel=ConversationChannel.WEBSITE,
        visitor_id=visitor_id,
        started_at=start or timezone.now(),
    )


def _message(conversation, role, content, tool_call_id=None):
    return ConversationMessage.objects.create(
        conversation=conversation,
        role=role,
        content=content,
        tool_call_id=tool_call_id,
    )


class TestDeploymentAnalytics:
    def _deployment_and_client(self, tenant):
        _, org, client = tenant
        deployment = _deployment(org)
        return deployment, client

    def test_requires_auth(self, tenant, api_client):
        deployment, _ = self._deployment_and_client(tenant)
        assert (
            api_client.get(f"/deployments/{deployment.id}/analytics").status_code == 401
        )

    def test_counts_payload(self, tenant):
        deployment, client = self._deployment_and_client(tenant)

        conv = _conversation(deployment.organization, deployment, visitor_id="vis-1")
        _message(conv, ConversationMessage.Role.USER, "hello")
        _message(conv, ConversationMessage.Role.ASSISTANT, "hi there")
        _message(conv, ConversationMessage.Role.ASSISTANT, "anything else?")

        conv2 = _conversation(
            deployment.organization, deployment, visitor_id="vis-1"
        )
        _message(conv2, ConversationMessage.Role.USER, "again")

        Appointment.objects.create(
            organization=deployment.organization,
            agent=deployment.agent,
            conversation=conv,
            customer_name="John Doe",
            customer_phone="+15551234567",
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=1),
            status=Appointment.Status.SCHEDULED,
        )

        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()

        assert data["deployment_id"] == deployment.id
        assert data["agent_name"] == "Receptionist"
        assert data["total_conversations"] == 2
        assert data["unique_visitors"] == 1
        assert data["total_messages"] == 4
        assert data["average_messages_per_conversation"] == 2.0
        assert data["conversations_started"]["today"] == 2
        assert data["appointments_booked"] == 1
        assert data["tool_calls"] == 0
        assert data["transfers"] == 0
        assert data["days"] == 7
        assert len(data["conversations_by_day"]) == 7
        assert sum(day["count"] for day in data["conversations_by_day"]) == 2

    def test_empty_deployment(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        assert data["total_conversations"] == 0
        assert data["unique_visitors"] == 0
        assert data["total_messages"] == 0
        assert data["average_messages_per_conversation"] == 0
        assert data["appointments_booked"] == 0
        assert data["tool_calls"] == 0
        assert data["transfers"] == 0
        assert all(day["count"] == 0 for day in data["conversations_by_day"])

    def test_org_isolation(self, tenant, stranger):
        deployment, client = self._deployment_and_client(tenant)
        _, _, other = stranger
        assert (
            other.get(f"/deployments/{deployment.id}/analytics").status_code == 404
        )
        assert client.get(f"/deployments/{deployment.id}/analytics").status_code == 200

    def test_deployment_isolation(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        org = deployment.organization
        sister = _deployment(org)

        other_conv = _conversation(org, deployment, visitor_id="vis-a")
        _message(other_conv, ConversationMessage.Role.USER, "one")
        _conversation(org, sister, visitor_id="vis-b")
        _message(
            _conversation(org, sister),
            ConversationMessage.Role.USER,
            "two",
        )

        deployment_data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        sister_data = client.get(
            f"/deployments/{sister.id}/analytics"
        ).json()

        assert deployment_data["total_conversations"] == 1
        assert deployment_data["total_messages"] == 1
        assert deployment_data["unique_visitors"] == 1
        assert sister_data["total_conversations"] == 2
        assert sister_data["unique_visitors"] == 1

    def test_date_filtering_days_param(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        now = timezone.now()
        _conversation(deployment.organization, deployment, start=now - timedelta(days=1))
        _conversation(deployment.organization, deployment, start=now - timedelta(days=10))

        two_days = client.get(
            f"/deployments/{deployment.id}/analytics?days=2"
        ).json()
        assert two_days["days"] == 2
        assert len(two_days["conversations_by_day"]) == 2
        assert two_days["total_conversations"] == 2
        assert sum(d["count"] for d in two_days["conversations_by_day"]) == 1

        data = client.get(
            f"/deployments/{deployment.id}/analytics?days=30"
        ).json()
        assert len(data["conversations_by_day"]) == 30
        assert sum(d["count"] for d in data["conversations_by_day"]) == 2

    def test_days_param_bounded(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        assert client.get(
            f"/deployments/{deployment.id}/analytics?days=999"
        ).json()["days"] == 90
        assert (
            client.get(
                f"/deployments/{deployment.id}/analytics?days=0"
            ).json()["days"]
            == 1
        )
        assert client.get(
            f"/deployments/{deployment.id}/analytics?days=banana"
        ).json()["days"] == 7

    def test_tool_calls_and_transfers_metrics(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        conv = _conversation(deployment.organization, deployment, visitor_id="v1")
        _message(
            conv,
            ConversationMessage.Role.ASSISTANT,
            json.dumps(
                {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "transfer_to_human",
                                "arguments": "{}",
                            },
                        }
                    ]
                }
            ),
        )
        _message(conv, ConversationMessage.Role.TOOL, '{"success": true}', "call_1")

        # A non-transfer tool call on another conversation
        conv2 = _conversation(deployment.organization, deployment, visitor_id="v2")
        _message(
            conv2,
            ConversationMessage.Role.ASSISTANT,
            json.dumps(
                {
                    "tool_calls": [
                        {
                            "id": "call_2",
                            "function": {
                                "name": "check_appointment_availability",
                                "arguments": "{}",
                            },
                        }
                    ]
                }
            ),
        )
        _message(
            conv2,
            ConversationMessage.Role.TOOL,
            '{"available": true}',
            "call_2",
        )

        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        assert data["tool_calls"] == 2
        assert data["transfers"] == 1

    def test_online_depends_on_deployment_and_business_hours(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        org = deployment.organization
        org.timezone = "UTC"
        org.business_hours = {
            "1": {"start": "09:00", "end": "17:00"},
            "2": {"start": "09:00", "end": "17:00"},
            "3": {"start": "09:00", "end": "17:00"},
            "4": {"start": "09:00", "end": "17:00"},
            "5": {"start": "09:00", "end": "17:00"},
            "6": {"start": "09:00", "end": "13:00"},
        }
        org.save()

        now = timezone.now()
        weekday = now.astimezone(timezone.utc).isoweekday()
        hour = now.astimezone(timezone.utc).hour
        expected = (
            weekday in (1, 2, 3, 4, 5, 6)
            and (hour >= 9 and (weekday != 6 or hour < 13) and hour < 17)
        )

        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        assert data["online"] is bool(expected)

        # Disabled deployment is always offline regardless of business hours.
        deployment.enabled = False
        deployment.save()
        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        assert data["online"] is False

        # Always-open schedule means online whenever the deployment is enabled.
        deployment.enabled = True
        deployment.save()
        org.business_hours = {}
        org.save()
        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        assert data["online"] is True

    def test_business_info_present(self, tenant):
        deployment, client = self._deployment_and_client(tenant)
        deployment.organization.business_name = "Acme Dental"
        deployment.organization.save()
        data = client.get(
            f"/deployments/{deployment.id}/analytics"
        ).json()
        assert data["business_name"] == "Acme Dental"
        assert data["timezone"] == "UTC"
        assert isinstance(data["business_hours"], list)