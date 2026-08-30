import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from .access import (
    get_request_organization,
    resolve_organization,
    visible_organization_ids,
    visible_organizations,
)
from .models import Organization, OrganizationMember

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def tenants():
    a = User.objects.create_user(email="a@example.com", password="x")
    b = User.objects.create_user(email="b@example.com", password="x")
    org_a = Organization.objects.create(name="Org A")
    org_b = Organization.objects.create(name="Org B")
    OrganizationMember.objects.create(
        organization=org_a, user=a, role=OrganizationMember.Role.OWNER
    )
    OrganizationMember.objects.create(
        organization=org_b, user=b, role=OrganizationMember.Role.OWNER
    )
    a.default_organization = org_a
    a.save()
    b.default_organization = org_b
    b.save()
    return a, b, org_a, org_b


def test_visible_organizations_scoped(tenants):
    a, b, org_a, org_b = tenants
    assert list(visible_organizations(a)) == [org_a]
    assert visible_organization_ids(a) == {org_a.id}
    assert visible_organization_ids(b) == {org_b.id}


def test_resolve_organization_default_and_explicit(tenants):
    a, b, org_a, org_b = tenants
    assert resolve_organization(a) == org_a
    assert resolve_organization(a, org_a.id) == org_a
    assert resolve_organization(a, org_b.id) is None  # cross-tenant -> 404 boundary
    assert resolve_organization(b, org_b.id) == org_b


def test_inactive_organization_invisible(tenants):
    a, b, org_a, org_b = tenants
    org_b.is_active = False
    org_b.save()
    assert resolve_organization(b) is None


def test_get_request_organization_honors_header(tenants):
    a, b, org_a, org_b = tenants
    factory = APIRequestFactory()

    req = factory.get("/x")
    req.user = a
    assert get_request_organization(req) == org_a

    req = factory.get("/x", HTTP_X_ORGANIZATION_ID=str(org_b.id))
    req.user = a
    assert get_request_organization(req) is None

    req = factory.get("/x", HTTP_X_ORGANIZATION_ID="not-an-id")
    req.user = a
    assert get_request_organization(req) is None


def test_member_roles(tenants):
    a, b, org_a, org_b = tenants
    assert OrganizationMember.Role.OWNER in OrganizationMember.Role.values
    assert OrganizationMember.Role.ADMIN in OrganizationMember.Role.values
    assert OrganizationMember.Role.STAFF in OrganizationMember.Role.values
    assert org_a.members.get(user=a).role == OrganizationMember.Role.OWNER