import pytest
from rest_framework.test import APIClient

from tenancy.models import OrganizationMember

from .models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def _legacy_argon2_hash(password: str) -> str:
    """Produce a pwdlib-style ``$argon2id$...`` hash (single leading ``$``)."""
    from argon2.low_level import Type, hash_secret

    raw = hash_secret(
        password.encode(),
        b"012345678901234567",
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        type=Type.ID,
    )
    return raw.decode("ascii")


def test_register_creates_user_and_organization(client):
    resp = client.post(
        "/auth/register",
        {"email": "alice@example.com", "full_name": "Alice A", "password": "secret1"},
        format="json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice A"

    user = User.objects.get(email="alice@example.com")
    member = OrganizationMember.objects.get(user=user)
    assert member.role == OrganizationMember.Role.OWNER
    assert user.default_organization_id == member.organization_id


def test_register_duplicate_email_409(client):
    User.objects.create_user(email="dup@example.com", password="secret1")
    resp = client.post(
        "/auth/register",
        {"email": "dup@example.com", "full_name": "Dup User", "password": "secret1"},
        format="json",
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Email already registered"


def test_register_validates_password_length(client):
    resp = client.post(
        "/auth/register",
        {"email": "weak@example.com", "full_name": "Weak User", "password": "123"},
        format="json",
    )
    assert resp.status_code == 400


def test_login_returns_access_token_contract(client):
    User.objects.create_user(email="bob@example.com", password="secret1")
    resp = client.post(
        "/auth/login",
        {"email": "bob@example.com", "password": "secret1"},
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert "refresh" in data


def test_login_invalid_credentials_401(client):
    User.objects.create_user(email="bob@example.com", password="secret1")
    resp = client.post(
        "/auth/login",
        {"email": "bob@example.com", "password": "wrongpass"},
        format="json",
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


def test_email_login_and_registration_are_case_insensitive(client):
    User.objects.create_user(email="CaseTest@Example.com", password="secret1")
    resp = client.post(
        "/auth/login",
        {"email": "casetest@example.com", "password": "secret1"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    reg = client.post(
        "/auth/register",
        {"email": "NewUser@Example.com", "full_name": "New User", "password": "secret1"},
        format="json",
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == "newuser@example.com"

    dup = client.post(
        "/auth/register",
        {"email": "NEWUSER@example.com", "full_name": "Dup User", "password": "secret1"},
        format="json",
    )
    assert dup.status_code == 409


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_user_and_organizations(client):
    client.post(
        "/auth/register",
        {"email": "carol@example.com", "full_name": "Carol C", "password": "secret1"},
        format="json",
    )
    login = client.post(
        "/auth/login",
        {"email": "carol@example.com", "password": "secret1"},
        format="json",
    )
    token = login.json()["access_token"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    resp = client.get("/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "carol@example.com"
    assert body["full_name"] == "Carol C"
    assert body["organizations"][0]["role"] == "OWNER"
    assert body["default_organization"]["id"] == body["organizations"][0]["id"]


def test_legacy_argon2_password_authenticates(client):
    password = "legacy-pass"
    encoded = f"argon2${_legacy_argon2_hash(password)[1:]}"
    User(email="legacy@example.com", full_name="Legacy User", password=encoded).save()

    resp = client.post(
        "/auth/login",
        {"email": "legacy@example.com", "password": password},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]