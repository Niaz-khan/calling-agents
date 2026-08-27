import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tenancy.models import Organization, OrganizationMember

User = get_user_model()


class JSONClient(APIClient):
    default_format = "json"


def _tenant_scope(email, org_name):
    user = User.objects.create_user(email=email, password="password123")
    org = Organization.objects.create(name=org_name)
    OrganizationMember.objects.create(
        organization=org, user=user, role=OrganizationMember.Role.OWNER
    )
    user.default_organization = org
    user.save(update_fields=["default_organization"])
    client = JSONClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}"
    )
    return user, org, client


@pytest.fixture
def api_client():
    return JSONClient()


@pytest.fixture
def tenant():
    return _tenant_scope("owner@example.com", "Acme")


@pytest.fixture
def stranger():
    return _tenant_scope("stranger@example.com", "Rival")