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


def _slot(days=1, hour=10):
    base = datetime.now(timezone.utc) + timedelta(days=days)
    start = base.replace(hour=hour, minute=0, second=0, microsecond=0)
    return start, start + timedelta(minutes=30)


class TestCreateAppointment:
    def test_creates_appointment(self, db_session, test_agent, auth_headers):
        client = TestClient(app)
        start, end = _slot()

        response = client.post(
            "/appointments",
            json={
                "agent_id": test_agent.id,
                "customer_name": "Ahmed",
                "customer_phone": "1234567890",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "scheduled"
        assert data["customer_name"] == "Ahmed"

    def test_rejects_overlapping_appointment(
        self, db_session, test_agent, auth_headers
    ):
        client = TestClient(app)
        start, end = _slot()

        db_session.add(
            Appointment(
                agent_id=test_agent.id,
                customer_name="Existing",
                customer_phone="0001",
                start_time=start,
                end_time=end,
                status=AppointmentStatus.SCHEDULED,
            )
        )
        db_session.commit()

        response = client.post(
            "/appointments",
            json={
                "agent_id": test_agent.id,
                "customer_name": "Ahmed",
                "customer_phone": "1234567890",
                "start_time": (start + timedelta(minutes=10)).isoformat(),
                "end_time": (end + timedelta(minutes=10)).isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_rejects_invalid_times(self, db_session, test_agent, auth_headers):
        client = TestClient(app)
        start, end = _slot()

        response = client.post(
            "/appointments",
            json={
                "agent_id": test_agent.id,
                "customer_name": "Ahmed",
                "customer_phone": "1234567890",
                "start_time": end.isoformat(),
                "end_time": start.isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_returns_404_for_other_users_agent(
        self, db_session, other_agent, auth_headers
    ):
        client = TestClient(app)
        start, end = _slot()

        response = client.post(
            "/appointments",
            json={
                "agent_id": other_agent.id,
                "customer_name": "Ahmed",
                "customer_phone": "1234567890",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_requires_auth(self, db_session, test_agent):
        client = TestClient(app)
        start, end = _slot()

        response = client.post(
            "/appointments",
            json={
                "agent_id": test_agent.id,
                "customer_name": "Ahmed",
                "customer_phone": "1234567890",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        )

        assert response.status_code == 401


class TestListAppointments:
    def test_lists_only_own_appointments(
        self, db_session, test_agent, other_agent, auth_headers
    ):
        start, end = _slot()
        db_session.add(
            Appointment(
                agent_id=test_agent.id,
                customer_name="Mine",
                customer_phone="1111",
                start_time=start,
                end_time=end,
            )
        )
        other_start, other_end = _slot(hour=15)
        db_session.add(
            Appointment(
                agent_id=other_agent.id,
                customer_name="Theirs",
                customer_phone="2222",
                start_time=other_start,
                end_time=other_end,
            )
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get("/appointments", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["customer_name"] == "Mine"

    def test_filters_by_status(self, db_session, test_agent, auth_headers):
        start, end = _slot()
        db_session.add(
            Appointment(
                agent_id=test_agent.id,
                customer_name="Scheduled One",
                customer_phone="1111",
                start_time=start,
                end_time=end,
                status=AppointmentStatus.SCHEDULED,
            )
        )
        cancelled_start, cancelled_end = _slot(hour=15)
        db_session.add(
            Appointment(
                agent_id=test_agent.id,
                customer_name="Cancelled One",
                customer_phone="2222",
                start_time=cancelled_start,
                end_time=cancelled_end,
                status=AppointmentStatus.CANCELLED,
            )
        )
        db_session.commit()

        client = TestClient(app)

        response = client.get(
            "/appointments?status_filter=cancelled",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["customer_name"] == "Cancelled One"


class TestGetAppointment:
    def test_gets_appointment(self, db_session, test_agent, auth_headers):
        start, end = _slot()
        appointment = Appointment(
            agent_id=test_agent.id,
            customer_name="Ahmed",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )
        db_session.add(appointment)
        db_session.commit()

        client = TestClient(app)

        response = client.get(
            f"/appointments/{appointment.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["customer_name"] == "Ahmed"

    def test_cross_user_returns_404(
        self, db_session, other_agent, auth_headers
    ):
        start, end = _slot()
        appointment = Appointment(
            agent_id=other_agent.id,
            customer_name="Ahmed",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )
        db_session.add(appointment)
        db_session.commit()

        client = TestClient(app)

        response = client.get(
            f"/appointments/{appointment.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestUpdateAppointment:
    def test_updates_status(self, db_session, test_agent, auth_headers):
        start, end = _slot()
        appointment = Appointment(
            agent_id=test_agent.id,
            customer_name="Ahmed",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )
        db_session.add(appointment)
        db_session.commit()

        client = TestClient(app)

        response = client.patch(
            f"/appointments/{appointment.id}",
            json={"status": "cancelled", "notes": "No longer needed"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["notes"] == "No longer needed"

    def test_rejects_overlapping_reschedule(
        self, db_session, test_agent, auth_headers
    ):
        start, end = _slot()
        appointment = Appointment(
            agent_id=test_agent.id,
            customer_name="Ahmed",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )
        db_session.add(appointment)
        db_session.commit()

        blocker_start, blocker_end = _slot(hour=13)
        db_session.add(
            Appointment(
                agent_id=test_agent.id,
                customer_name="Blocker",
                customer_phone="0002",
                start_time=blocker_start,
                end_time=blocker_end,
            )
        )
        db_session.commit()

        client = TestClient(app)

        response = client.patch(
            f"/appointments/{appointment.id}",
            json={
                "start_time": (blocker_start + timedelta(minutes=5)).isoformat(),
                "end_time": (blocker_end + timedelta(minutes=5)).isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 409


class TestDeleteAppointment:
    def test_deletes_appointment(self, db_session, test_agent, auth_headers):
        start, end = _slot()
        appointment = Appointment(
            agent_id=test_agent.id,
            customer_name="Ahmed",
            customer_phone="1234567890",
            start_time=start,
            end_time=end,
        )
        db_session.add(appointment)
        db_session.commit()

        client = TestClient(app)

        response = client.delete(
            f"/appointments/{appointment.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204
        db_session.expunge_all()
        assert db_session.get(Appointment, appointment.id) is None