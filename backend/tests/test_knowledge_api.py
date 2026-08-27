import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.auth.security import create_access_token
from app.database import Base, get_db
from app.main import app
from app.models.agent import Agent
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.models.user import User
from app.services.knowledge import (
    create_knowledge_base,
    ingest_document,
)


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
def knowledge_base(db_session, test_agent):
    return create_knowledge_base(
        db=db_session,
        agent_id=test_agent.id,
        name="Acme Clinic Knowledge",
    )


class TestCreateKnowledgeBase:
    def test_creates_base(self, db_session, test_agent, auth_headers):
        client = TestClient(app)

        response = client.post(
            "/knowledge/bases",
            json={
                "agent_id": test_agent.id,
                "name": "Acme Clinic Knowledge",
                "description": "Pricing",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == test_agent.id
        assert data["name"] == "Acme Clinic Knowledge"

    def test_rejects_base_for_unowned_agent(self, db_session, test_user, auth_headers):
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hashed_password_123",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_agent = Agent(
            owner_id=other_user.id,
            name="Other Agent",
            system_prompt="test",
            is_active=True,
        )
        db_session.add(other_agent)
        db_session.commit()
        db_session.refresh(other_agent)

        client = TestClient(app)

        response = client.post(
            "/knowledge/bases",
            json={"agent_id": other_agent.id, "name": "Sneaky"},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_requires_authentication(self, db_session, test_agent):
        client = TestClient(app)

        response = client.post(
            "/knowledge/bases",
            json={"agent_id": test_agent.id, "name": "X"},
        )

        assert response.status_code in (401, 403)


class TestListKnowledgeBases:
    def test_lists_only_owned_bases(self, db_session, knowledge_base, test_agent, auth_headers):
        client = TestClient(app)

        response = client.get("/knowledge/bases", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == knowledge_base.id


class TestGetKnowledgeBase:
    def test_returns_base(self, db_session, knowledge_base, auth_headers):
        client = TestClient(app)

        response = client.get(
            f"/knowledge/bases/{knowledge_base.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["id"] == knowledge_base.id

    def test_returns_404_for_unknown_base(self, auth_headers):
        client = TestClient(app)

        response = client.get("/knowledge/bases/999", headers=auth_headers)

        assert response.status_code == 404


class TestDeleteKnowledgeBase:
    def test_deletes_base(self, db_session, knowledge_base, auth_headers):
        client = TestClient(app)

        response = client.delete(
            f"/knowledge/bases/{knowledge_base.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204
        assert db_session.scalar(
            select(KnowledgeBase).where(
                KnowledgeBase.id == knowledge_base.id
            )
        ) is None


class TestUploadDocument:
    def test_uploads_txt_document(
        self, db_session, knowledge_base, auth_headers
    ):
        client = TestClient(app)

        response = client.post(
            f"/knowledge/bases/{knowledge_base.id}/documents",
            headers=auth_headers,
            files={
                "file": (
                    "pricing.txt",
                    b"the consultation cost is fifty dollars per session",
                    "text/plain",
                )
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert data["filename"] == "pricing.txt"

        chunks = db_session.scalars(
            select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == data["id"]
            )
        ).all()
        assert len(chunks) > 0

    def test_rejects_unsupported_file_type(self, knowledge_base, auth_headers):
        client = TestClient(app)

        response = client.post(
            f"/knowledge/bases/{knowledge_base.id}/documents",
            headers=auth_headers,
            files={"file": ("data.docx", b"content", "application/octet-stream")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "failed"
        assert "unsupported" in data["error"].lower()

    def test_rejects_empty_file(self, knowledge_base, auth_headers):
        client = TestClient(app)

        response = client.post(
            f"/knowledge/bases/{knowledge_base.id}/documents",
            headers=auth_headers,
            files={"file": ("empty.txt", b"", "text/plain")},
        )

        assert response.status_code == 400


class TestListDocuments:
    def test_lists_documents(
        self, db_session, knowledge_base, auth_headers
    ):
        ingest_document(
            db=db_session,
            knowledge_base=knowledge_base,
            filename="pricing.txt",
            content=b"consultation cost fifty dollars",
        )

        client = TestClient(app)

        response = client.get(
            f"/knowledge/bases/{knowledge_base.id}/documents",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "pricing.txt"


class TestDocumentDetail:
    def test_returns_document_with_chunks(
        self, db_session, knowledge_base, auth_headers
    ):
        document = ingest_document(
            db=db_session,
            knowledge_base=knowledge_base,
            filename="pricing.txt",
            content=b"the consultation cost is fifty dollars per session",
        )

        client = TestClient(app)

        response = client.get(
            f"/knowledge/documents/{document.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == document.id
        assert len(data["chunks"]) == 1
        assert "fifty dollars" in data["chunks"][0]["content"]

    def test_hides_other_owners_document(
        self,
        db_session,
        test_user,
        knowledge_base,
        auth_headers,
    ):
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hashed_password_123",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_agent = Agent(
            owner_id=other_user.id,
            name="Other Agent",
            system_prompt="test",
            is_active=True,
        )
        db_session.add(other_agent)
        db_session.commit()
        db_session.refresh(other_agent)

        other_base = create_knowledge_base(
            db=db_session,
            agent_id=other_agent.id,
            name="Other",
        )
        other_document = ingest_document(
            db=db_session,
            knowledge_base=other_base,
            filename="secret.txt",
            content=b"secret pricing information",
        )

        client = TestClient(app)

        response = client.get(
            f"/knowledge/documents/{other_document.id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDeleteDocument:
    def test_deletes_document(
        self, db_session, knowledge_base, auth_headers
    ):
        document = ingest_document(
            db=db_session,
            knowledge_base=knowledge_base,
            filename="pricing.txt",
            content=b"consultation cost fifty dollars",
        )

        client = TestClient(app)

        response = client.delete(
            f"/knowledge/documents/{document.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204
        assert db_session.scalar(
            select(KnowledgeDocument.id).where(
                KnowledgeDocument.id == document.id
            )
        ) is None


class TestSearchEndpoint:
    def test_searches_owned_agent(
        self, db_session, knowledge_base, test_agent, auth_headers
    ):
        ingest_document(
            db=db_session,
            knowledge_base=knowledge_base,
            filename="pricing.txt",
            content=b"consultation cost fifty dollars per session",
        )

        client = TestClient(app)

        response = client.post(
            "/knowledge/search",
            json={
                "agent_id": test_agent.id,
                "query": "consultation cost per session",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is True
        assert len(data["results"]) > 0
        assert data["results"][0]["document_filename"] == "pricing.txt"
        assert data["results"][0]["score"] > 0

    def test_rejects_search_for_unowned_agent(
        self, db_session, test_user, test_agent, auth_headers
    ):
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hashed_password_123",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        other_agent = Agent(
            owner_id=other_user.id,
            name="Other Agent",
            system_prompt="test",
            is_active=True,
        )
        db_session.add(other_agent)
        db_session.commit()
        db_session.refresh(other_agent)

        client = TestClient(app)

        response = client.post(
            "/knowledge/search",
            json={"agent_id": other_agent.id, "query": "anything"},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_returns_not_found_when_no_match(
        self, db_session, knowledge_base, test_agent, auth_headers
    ):
        ingest_document(
            db=db_session,
            knowledge_base=knowledge_base,
            filename="pricing.txt",
            content=b"consultation cost fifty dollars",
        )

        client = TestClient(app)

        response = client.post(
            "/knowledge/search",
            json={"agent_id": test_agent.id, "query": "walrus violet kangaroo"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["found"] is False
        assert data["results"] == []