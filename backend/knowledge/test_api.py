from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from agents.models import Agent
from knowledge.models import KnowledgeBase

pytestmark = pytest.mark.django_db

FAKE_VECTOR_SIZE = 3


class FakeEmbedder:
    def embed(self, texts):
        vector = [1.0 if index == 0 else 0.0 for index in range(FAKE_VECTOR_SIZE)]
        return [vector for _ in texts]


@pytest.fixture
def fake_embedder(monkeypatch):
    monkeypatch.setattr("knowledge.services.get_embedding_provider", lambda: FakeEmbedder())


def _agent(org, name="Docs"):
    return Agent.objects.create(organization=org, name=name, system_prompt="p")


def test_knowledge_require_auth(api_client):
    assert api_client.get("/knowledge/bases").status_code == 401


def test_base_crud(tenant):
    _, org, client = tenant
    agent = _agent(org)

    missing = client.post(
        "/knowledge/bases", {"agent_id": 9999, "name": "KB"}
    )
    assert missing.status_code == 404

    created = client.post(
        "/knowledge/bases",
        {"agent_id": agent.id, "name": "FAQ", "description": "Common answers"},
    )
    assert created.status_code == 201
    data = created.json()
    assert data["agent_id"] == agent.id
    assert data["name"] == "FAQ"

    listed = client.get("/knowledge/bases")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [data["id"]]

    detail = client.get(f"/knowledge/bases/{data['id']}")
    assert detail.status_code == 200
    assert detail.json()["description"] == "Common answers"

    assert client.delete(f"/knowledge/bases/{data['id']}").status_code == 204
    assert client.get(f"/knowledge/bases/{data['id']}").status_code == 404


def test_upload_document_and_search(fake_embedder, tenant):
    _, org, client = tenant
    agent = _agent(org)
    base = client.post(
        "/knowledge/bases", {"agent_id": agent.id, "name": "Wiki"}
    ).json()
    base_id = base["id"]

    upload = client.post(
        f"/knowledge/bases/{base_id}/documents",
        {"file": SimpleUploadedFile("notes.txt", b"Welcome to our support wiki here daily.")},
        format="multipart",
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document["filename"] == "notes.txt"
    assert document["source_type"] == "txt"
    assert document["status"] == "completed"
    assert document["knowledge_base_id"] == base_id

    documents = client.get(f"/knowledge/bases/{base_id}/documents")
    assert documents.status_code == 200
    assert [item["id"] for item in documents.json()] == [document["id"]]

    detail = client.get(f"/knowledge/documents/{document['id']}")
    assert detail.status_code == 200
    chunks = detail.json()["chunks"]
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 1

    search = client.post(
        "/knowledge/search",
        {"agent_id": agent.id, "query": "support"},
    )
    assert search.status_code == 200
    result = search.json()
    assert result["found"] is True
    assert result["query"] == "support"
    assert result["results"][0]["chunk_id"] == chunks[0]["id"]
    assert result["results"][0]["document_filename"] == "notes.txt"

    assert client.delete(f"/knowledge/documents/{document['id']}").status_code == 204
    assert client.get(f"/knowledge/bases/{base_id}/documents").json() == []

    assert client.delete(f"/knowledge/bases/{base_id}").status_code == 204
    assert KnowledgeBase.objects.count() == 0


def test_upload_requires_owned_base(tenant, stranger):
    _, org, client = tenant
    _, _, other = stranger
    agent = _agent(org)
    base = client.post(
        "/knowledge/bases", {"agent_id": agent.id, "name": "Private"}
    ).json()

    upload = other.post(
        f"/knowledge/bases/{base['id']}/documents",
        {"file": SimpleUploadedFile("x.txt", b"secret")},
        format="multipart",
    )
    assert upload.status_code == 404
    assert other.get(f"/knowledge/bases/{base['id']}/documents").status_code == 404
    assert other.delete(f"/knowledge/bases/{base['id']}").status_code == 404
    assert other.get("/knowledge/bases").json() == []


def test_search_no_base(tenant):
    _, org, client = tenant
    agent = _agent(org)
    result = client.post(
        "/knowledge/search", {"agent_id": agent.id, "query": "anything"}
    ).json()
    assert result["found"] is False
    assert result["results"] == []


def test_search_requires_owned_agent(tenant, stranger):
    _, org, client = tenant
    _, _, other = stranger
    agent = _agent(org)
    assert (
        other.post("/knowledge/search", {"agent_id": agent.id, "query": "x"}).status_code
        == 404
    )


def test_empty_upload_rejected(tenant):
    _, org, client = tenant
    agent = _agent(org)
    base = client.post(
        "/knowledge/bases", {"agent_id": agent.id, "name": "Empty"}
    ).json()
    upload = client.post(
        f"/knowledge/bases/{base['id']}/documents",
        {"file": SimpleUploadedFile("empty.txt", b"")},
        format="multipart",
    )
    assert upload.status_code == 400