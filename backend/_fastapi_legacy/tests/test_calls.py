import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.agent import Agent
from app.models.call import Call, CallDirection, CallStatus
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
def auth_headers(test_user):
    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_agent(db_session, test_user):
    agent = Agent(
        owner_id=test_user.id,
        name="Test Agent",
        description="A test agent",
        system_prompt="You are a test agent.",
        is_active=True,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture(scope="function")
def test_call(db_session, test_agent):
    call = Call(
        agent_id=test_agent.id,
        caller_number="1234567890",
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    return call


class TestCreateCall:
    def test_creates_call_successfully(self, db_session, test_agent, auth_headers):
        client = TestClient(app)

        response = client.post(
            f"/calls?agent_id={test_agent.id}",
            json={
                "caller_number": "1234567890",
                "direction": "inbound",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["caller_number"] == "1234567890"
        assert data["status"] == "in_progress"
        assert data["customer_id"] is not None

    def test_creates_customer_on_first_call(
        self, db_session, test_agent, test_user, auth_headers
    ):
        client = TestClient(app)

        response = client.post(
            f"/calls?agent_id={test_agent.id}",
            json={
                "caller_number": "0987654321",
                "direction": "inbound",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        customer = db_session.get(Customer, data["customer_id"])
        assert customer is not None
        assert customer.phone_number == "0987654321"
        assert customer.owner_id == test_user.id

    def test_reuses_existing_customer(
        self, db_session, test_agent, test_user, auth_headers
    ):
        customer = Customer(
            owner_id=test_user.id,
            phone_number="1234567890",
            name="Existing Customer",
        )
        db_session.add(customer)
        db_session.commit()

        client = TestClient(app)

        response = client.post(
            f"/calls?agent_id={test_agent.id}",
            json={
                "caller_number": "1234567890",
                "direction": "inbound",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["customer_id"] == customer.id

    def test_returns_404_for_nonexistent_agent(self, db_session, auth_headers):
        client = TestClient(app)

        response = client.post(
            "/calls?agent_id=999",
            json={
                "caller_number": "1234567890",
                "direction": "inbound",
            },
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_returns_401_without_auth(self, db_session, test_agent):
        client = TestClient(app)

        response = client.post(
            f"/calls?agent_id={test_agent.id}",
            json={
                "caller_number": "1234567890",
                "direction": "inbound",
            },
        )

        assert response.status_code == 401


class TestListCalls:
    def test_lists_calls_for_user(self, db_session, test_call, auth_headers):
        client = TestClient(app)

        response = client.get("/calls", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_filters_by_agent_id(self, db_session, test_call, test_agent, auth_headers):
        client = TestClient(app)

        response = client.get(f"/calls?agent_id={test_agent.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestGetCall:
    def test_gets_call_with_messages(self, db_session, test_call, auth_headers):
        client = TestClient(app)

        response = client.get(f"/calls/{test_call.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_call.id
        assert "messages" in data

    def test_returns_404_for_nonexistent_call(self, db_session, auth_headers):
        client = TestClient(app)

        response = client.get("/calls/999", headers=auth_headers)

        assert response.status_code == 404


class TestGetCallMessages:
    def test_returns_messages_in_order(self, db_session, test_call, auth_headers):
        from app.models.call_message import CallMessage, MessageRole

        db_session.add(
            CallMessage(
                call_id=test_call.id,
                role=MessageRole.USER,
                content="Hello",
            )
        )
        db_session.add(
            CallMessage(
                call_id=test_call.id,
                role=MessageRole.ASSISTANT,
                content="Hi there",
            )
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get(f"/calls/{test_call.id}/messages", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Hello"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Hi there"

    def test_returns_404_for_nonexistent_call(self, db_session, auth_headers):
        client = TestClient(app)

        response = client.get("/calls/999/messages", headers=auth_headers)

        assert response.status_code == 404


class TestEndCall:
    def test_ends_active_call(self, db_session, test_call, auth_headers):
        client = TestClient(app)

        response = client.post(f"/calls/{test_call.id}/end", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["ended_at"] is not None

    def test_cannot_end_completed_call(self, db_session, test_call, auth_headers):
        client = TestClient(app)

        test_call.status = CallStatus.COMPLETED
        db_session.commit()

        response = client.post(f"/calls/{test_call.id}/end", headers=auth_headers)

        assert response.status_code == 400

    def test_returns_404_for_nonexistent_call(self, db_session, auth_headers):
        client = TestClient(app)

        response = client.post("/calls/999/end", headers=auth_headers)

        assert response.status_code == 404
