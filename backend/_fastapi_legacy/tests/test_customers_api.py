import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.customer import Customer
from app.models.user import User


SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_user(db_session):
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password_123",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def other_user(db_session):
    user = User(
        email="other@example.com",
        full_name="Other User",
        hashed_password="hashed_password_456",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def other_headers(other_user):
    token = create_access_token(other_user.id)
    return {"Authorization": f"Bearer {token}"}


class TestCreateCustomer:
    def test_creates_customer(self, db_session, auth_headers):
        client = TestClient(app)

        response = client.post(
            "/customers",
            json={
                "phone_number": "1234567890",
                "name": "Ahmed",
                "email": "ahmed@example.com",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "1234567890"
        assert data["name"] == "Ahmed"
        assert data["owner_id"] is not None

    def test_duplicate_phone_returns_409(self, db_session, test_user, auth_headers):
        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
            name="Existing",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.post(
            "/customers",
            json={"phone_number": "1234567890"},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_same_phone_allowed_for_other_user(
        self, db_session, other_user, auth_headers
    ):
        customer = Customer(
            owner_id=other_user.id,
            phone_number="1234567890",
            name="Other's customer",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.post(
            "/customers",
            json={"phone_number": "1234567890", "name": "Mine"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Mine"

    def test_requires_auth(self, db_session):
        client = TestClient(app)

        response = client.post(
            "/customers",
            json={"phone_number": "1234567890"},
        )

        assert response.status_code == 401


class TestListCustomers:
    def test_lists_only_own_customers(
        self, db_session, test_user, other_user, auth_headers
    ):
        db_session.add(
            Customer(owner_id=test_user.id, phone_number="1111", name="Mine")
        )
        db_session.add(
            Customer(owner_id=other_user.id, phone_number="2222", name="Theirs")
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get("/customers", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Mine"

    def test_search_filter(self, db_session, test_user, auth_headers):
        db_session.add(
            Customer(owner_id=test_user.id, phone_number="1111", name="Ahmed")
        )
        db_session.add(
            Customer(owner_id=test_user.id, phone_number="2222", name="Sara")
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get("/customers?q=ahm", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Ahmed"


class TestGetCustomer:
    def test_gets_customer(self, db_session, test_user, auth_headers):
        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
            name="Ahmed",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.get(f"/customers/{customer.id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["name"] == "Ahmed"

    def test_cross_user_returns_404(
        self, db_session, other_user, auth_headers
    ):
        customer = Customer(
            owner_id=other_user.id,
            phone_number="1234567890",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.get(f"/customers/{customer.id}", headers=auth_headers)

        assert response.status_code == 404


class TestUpdateCustomer:
    def test_updates_fields(self, db_session, test_user, auth_headers):
        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
            name="Old",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.patch(
            f"/customers/{customer.id}",
            json={"name": "New", "notes": "VIP"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New"
        assert data["notes"] == "VIP"

    def test_phone_conflict_returns_409(
        self, db_session, test_user, auth_headers
    ):
        db_session.add(
            Customer(owner_id=test_user.id, phone_number="1234567890")
        )
        other = Customer(
            owner_id=test_user.id,
            phone_number="9999999999",
        )
        db_session.add(other)
        db_session.commit()

        client = TestClient(app)

        response = client.patch(
            f"/customers/{other.id}",
            json={"phone_number": "1234567890"},
            headers=auth_headers,
        )

        assert response.status_code == 409


class TestDeleteCustomer:
    def test_deletes_customer(self, db_session, test_user, auth_headers):
        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.delete(f"/customers/{customer.id}", headers=auth_headers)

        assert response.status_code == 204
        db_session.expunge_all()
        assert db_session.get(Customer, customer.id) is None

    def test_cross_user_returns_404(
        self, db_session, other_user, auth_headers
    ):
        customer = Customer(
            owner_id=other_user.id,
            phone_number="1234567890",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.delete(f"/customers/{customer.id}", headers=auth_headers)

        assert response.status_code == 404