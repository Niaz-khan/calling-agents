import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.embeddings import set_embedding_provider
from app.database import Base
from app.models.agent import Agent
from app.models.user import User
from tests.fake_embedding import FakeEmbeddingProvider


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


@pytest.fixture(autouse=True)
def fake_embedding_provider():
    set_embedding_provider(FakeEmbeddingProvider())
    yield
    set_embedding_provider(None)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


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
