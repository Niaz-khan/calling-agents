import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from agents.models import Agent
from tenancy.models import Organization


class ImportLegacyDataCommandTests(TestCase):
    def test_requires_existing_organization(self):
        with pytest.raises(CommandError, match="not found"):
            call_command("import_legacy_data", org="Missing Org")

    def test_refuses_when_business_tables_already_populated(self):
        org = Organization.objects.create(name="Existing Org")
        Agent.objects.create(organization=org, name="Legacy Agent")
        with pytest.raises(CommandError, match="Already imported into Agent"):
            call_command("import_legacy_data", org="Existing Org")
        assert Agent.objects.filter(organization=org, name="Legacy Agent").exists()