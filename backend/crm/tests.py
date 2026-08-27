import pytest
from django.db import IntegrityError

from agents.models import Agent
from conversations.models import Conversation, ConversationMessage, ConversationStatus
from knowledge.models import KnowledgeBase
from tenancy.models import Organization

from .models import Customer

pytestmark = pytest.mark.django_db


def test_customer_org_scoped():
    org = Organization.objects.create(name="Org")
    customer = Customer.objects.create(organization=org, phone_number="+15555550000")
    assert customer.organization_id == org.id
    assert customer.name is None


def test_unique_customer_per_org_phone():
    org = Organization.objects.create(name="Org")
    Customer.objects.create(organization=org, phone_number="+1")
    with pytest.raises(IntegrityError):
        Customer.objects.create(organization=org, phone_number="+1")


def test_same_phone_different_org_allowed():
    org_a = Organization.objects.create(name="A")
    org_b = Organization.objects.create(name="B")
    Customer.objects.create(organization=org_a, phone_number="+1")
    Customer.objects.create(organization=org_b, phone_number="+1")


def test_customer_memory_and_conversation_link():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    customer = Customer.objects.create(organization=org, phone_number="+1", memory="prefers mornings")
    conv = Conversation.objects.create(organization=org, agent=agent, customer=customer)
    ConversationMessage.objects.create(conversation=conv, role="USER", content="hi")
    assert customer.conversations.count() == 1
    assert conv.status == ConversationStatus.OPEN