import pytest
from django.db import IntegrityError

from agents.models import Agent
from tenancy.models import Organization

from .models import PhoneNumber

pytestmark = pytest.mark.django_db


def test_phone_number_globally_unique():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    PhoneNumber.objects.create(
        organization=org, agent=agent, phone_number="+15550001111", provider="twilio"
    )
    with pytest.raises(IntegrityError):
        PhoneNumber.objects.create(
            organization=org, agent=agent, phone_number="+15550001111", provider="twilio"
        )