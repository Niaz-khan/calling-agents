import pytest

from agents.models import Agent
from services.models import Service

pytestmark = pytest.mark.django_db


class TestServices:
    def _agent(self, org):
        return Agent.objects.create(organization=org, name="Receptionist", system_prompt="p")

    def _payload(self, **overrides):
        payload = {
            "name": "Consultation",
            "description": "Dental consultation",
            "duration_minutes": 30,
            "price": "50.00",
            "currency": "usd",
        }
        payload.update(overrides)
        return payload

    def test_requires_auth(self, api_client):
        assert api_client.get("/services").status_code == 401
        assert api_client.post("/services", {}).status_code == 401

    def test_create_service(self, tenant):
        _, org, client = tenant
        self._agent(org)
        response = client.post("/services", self._payload())
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Consultation"
        assert data["duration_minutes"] == 30
        assert data["price"] == "50.00"
        assert data["currency"] == "USD"
        assert data["active"] is True
        assert data["organization_id"] == org.id

    def test_list_and_order(self, tenant):
        _, org, client = tenant
        Service.objects.create(
            organization=org, name="Cleaning", duration_minutes=45, price="80.00",
        )
        Service.objects.create(
            organization=org, name="Alpha", duration_minutes=15, price=None,
        )
        data = client.get("/services").json()
        assert [row["name"] for row in data] == ["Alpha", "Cleaning"]

    def test_retrieve_patch_delete(self, tenant):
        _, org, client = tenant
        service = Service.objects.create(
            organization=org, name="Checkup", duration_minutes=30, price="25.00"
        )
        data = client.get(f"/services/{service.id}").json()
        assert data["name"] == "Checkup"

        response = client.patch(
            f"/services/{service.id}",
            {"duration_minutes": 45, "active": False},
        )
        assert response.status_code == 200
        assert response.json()["duration_minutes"] == 45
        assert response.json()["active"] is False

        assert client.delete(f"/services/{service.id}").status_code == 204
        assert client.get(f"/services/{service.id}").status_code == 404

    def test_org_isolation(self, tenant, stranger):
        _, org, client = tenant
        service = Service.objects.create(
            organization=org, name="Private", duration_minutes=30
        )
        _, _, other = stranger
        assert other.get(f"/services/{service.id}").status_code == 404
        assert client.get(f"/services/{service.id}").status_code == 200

    def test_validation(self, tenant):
        _, org, client = tenant
        assert client.post("/services", self._payload(name="")).status_code == 400
        assert (
            client.post(
                "/services", self._payload(duration_minutes=0)
            ).status_code
            == 400
        )
        assert (
            client.post("/services", self._payload(currency="US")).status_code
            == 400
        )
        assert (
            client.post("/services", self._payload(price="-5")).status_code
            == 400
        )