import pytest

pytestmark = pytest.mark.django_db


def test_customers_require_auth(api_client):
    assert api_client.get("/customers").status_code == 401


def test_customer_create_duplicate_search_patch_delete(tenant):
    _, org, client = tenant
    payload = {
        "phone_number": "+15551231234",
        "name": "Sam",
        "email": "sam@example.com",
        "notes": "VIP",
    }
    created = client.post("/customers", payload)
    assert created.status_code == 201
    data = created.json()
    assert data["organization_id"] == org.id
    assert data["phone_number"] == "+15551231234"
    assert data["email"] == "sam@example.com"
    assert data["notes"] == "VIP"
    assert data["memory"] is None

    conflict = client.post("/customers", payload)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "A customer with that phone number already exists"

    listing = client.get("/customers?q=sam")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [data["id"]]

    assert client.get("/customers?q=nomatch").json() == []

    patched = client.patch(
        f"/customers/{data['id']}", {"name": "Samuel", "email": None}
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Samuel"
    assert patched.json()["email"] is None

    client.post("/customers", {"phone_number": "+19991112222"})
    dup = client.patch(
        f"/customers/{data['id']}", {"phone_number": "+19991112222"}
    )
    assert dup.status_code == 409

    assert client.delete(f"/customers/{data['id']}").status_code == 204
    assert client.get(f"/customers/{data['id']}").status_code == 404


def test_customer_org_isolation(tenant, stranger):
    _, _, client = tenant
    _, _, other = stranger
    created = client.post("/customers", {"phone_number": "+14445556666"}).json()

    assert other.get(f"/customers/{created['id']}").status_code == 404
    assert other.patch(f"/customers/{created['id']}", {"name": "Nope"}).status_code == 404
    assert other.delete(f"/customers/{created['id']}").status_code == 404