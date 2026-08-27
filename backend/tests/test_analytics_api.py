from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.agent import Agent
from app.models.appointment import Appointment, AppointmentStatus
from app.models.call import Call, CallDirection, CallOutcome, CallStatus
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
def other_agent(db_session, other_user):
    agent = Agent(
        owner_id=other_user.id,
        name="Other Agent",
        description="Another agent",
        system_prompt="You are another agent.",
        is_active=True,
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


def _ended_call(agent, caller, status, outcome, started, ended):
    return Call(
        agent_id=agent.id,
        caller_number=caller,
        direction=CallDirection.INBOUND,
        status=status,
        outcome=outcome,
        started_at=started,
        ended_at=ended,
    )


class TestAnalyticsOverview:
    def test_empty_overview_returns_zeros(self, db_session, test_user, auth_headers):
        client = TestClient(app)

        response = client.get("/analytics/overview", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 0
        assert data["in_progress_calls"] == 0
        assert data["completed_calls"] == 0
        assert data["average_duration_seconds"] is None
        assert data["appointments_scheduled"] == 0
        assert data["total_agents"] == 0
        assert len(data["calls_last_7_days"]) == 7
        assert all(entry["count"] == 0 for entry in data["calls_last_7_days"])

    def test_counts_calls_by_status(
        self, db_session, test_agent, test_user, auth_headers
    ):
        now = datetime.now(timezone.utc)

        db_session.add_all(
            [
                _ended_call(
                    test_agent, "1111", CallStatus.COMPLETED,
                    CallOutcome.APPOINTMENT_BOOKED, now - timedelta(hours=3),
                    now - timedelta(hours=2, minutes=50),
                ),
                _ended_call(
                    test_agent, "2222", CallStatus.COMPLETED,
                    CallOutcome.INFORMATION_PROVIDED, now - timedelta(hours=2),
                    now - timedelta(hours=1, minutes=45),
                ),
                _ended_call(
                    test_agent, "3333", CallStatus.RINGING, None,
                    now - timedelta(hours=1), None,
                ),
            ]
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get("/analytics/overview", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 3
        assert data["completed_calls"] == 2
        assert data["missed_calls"] == 1
        assert data["average_duration_seconds"] == pytest.approx(750.0, abs=0.01)
        assert data["outcome_breakdown"]["appointment_booked"] == 1
        assert data["outcome_breakdown"]["information_provided"] == 1

    def test_counts_appointments_and_customers(
        self, db_session, test_agent, test_user, auth_headers
    ):
        now = datetime.now(timezone.utc)
        db_session.add_all(
            [
                Customer(owner_id=test_user.id, phone_number="1111"),
                Customer(owner_id=test_user.id, phone_number="2222"),
            ]
        )
        db_session.add_all(
            [
                Appointment(
                    agent_id=test_agent.id,
                    customer_name="Ahmed",
                    customer_phone="1111",
                    start_time=now + timedelta(days=1),
                    end_time=now + timedelta(days=1, minutes=30),
                    status=AppointmentStatus.SCHEDULED,
                ),
                Appointment(
                    agent_id=test_agent.id,
                    customer_name="Sara",
                    customer_phone="2222",
                    start_time=now + timedelta(days=2),
                    end_time=now + timedelta(days=2, minutes=30),
                    status=AppointmentStatus.CANCELLED,
                ),
            ]
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get("/analytics/overview", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_customers"] == 2
        assert data["total_agents"] == 1
        assert data["appointments_scheduled"] == 1
        assert data["appointments_cancelled"] == 1

    def test_scopes_to_own_data(
        self, db_session, test_agent, other_user, other_agent,
        other_headers, auth_headers,
    ):
        now = datetime.now(timezone.utc)
        db_session.add_all(
            [
                _ended_call(
                    test_agent, "1111", CallStatus.COMPLETED,
                    CallOutcome.APPOINTMENT_BOOKED, now - timedelta(hours=3),
                    now - timedelta(hours=2),
                ),
                _ended_call(
                    other_agent, "2222", CallStatus.COMPLETED,
                    CallOutcome.CUSTOMER_HUNG_UP, now - timedelta(hours=3),
                    now - timedelta(hours=2),
                ),
            ]
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get("/analytics/overview", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] == 1
        assert data["outcome_breakdown"] == {"appointment_booked": 1}
        assert len(data["recent_calls"]) == 1
        assert data["recent_calls"][0]["caller_number"] == "1111"

    def test_includes_only_recent_calls(
        self, db_session, test_agent, auth_headers
    ):
        now = datetime.now(timezone.utc)
        calls = [
            _ended_call(
                test_agent, f"{i:04d}", CallStatus.COMPLETED,
                CallOutcome.INFORMATION_PROVIDED, now - timedelta(hours=i),
                now - timedelta(hours=i, minutes=30),
            )
            for i in range(1, 8)
        ]
        db_session.add_all(calls)
        db_session.commit()

        client = TestClient(app)

        response = client.get("/analytics/overview", headers=auth_headers)

        data = response.json()
        assert len(data["recent_calls"]) == 5

    def test_requires_auth(self, db_session):
        client = TestClient(app)

        response = client.get("/analytics/overview")

        assert response.status_code == 401