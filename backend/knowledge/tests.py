import pytest
from django.db import IntegrityError, transaction

from agents.models import Agent
from tenancy.models import Organization

from .models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def org_agent():
    org = Organization.objects.create(name="Org")
    agent = Agent.objects.create(organization=org, name="A", system_prompt="p")
    return org, agent


def test_knowledge_base_is_one_to_one_with_agent(org_agent):
    org, agent = org_agent
    KnowledgeBase.objects.create(organization=org, agent=agent, name="KB")
    with pytest.raises(IntegrityError):
        KnowledgeBase.objects.create(organization=org, agent=agent, name="KB2")


def test_document_and_chunk_chain(org_agent):
    org, agent = org_agent
    kb = KnowledgeBase.objects.create(organization=org, agent=agent, name="KB")
    doc = KnowledgeDocument.objects.create(
        knowledge_base=kb, filename="f.txt", source_type="manual", status="PROCESSED"
    )
    KnowledgeChunk.objects.create(document=doc, chunk_index=0, content="c0", embedding=[0.1, 0.2])
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            KnowledgeChunk.objects.create(document=doc, chunk_index=0, content="dup", embedding=[1.0])
    assert kb.documents.count() == 1
    assert doc.chunks.count() == 1