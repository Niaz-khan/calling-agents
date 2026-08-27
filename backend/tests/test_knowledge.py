import zlib

import pytest
from sqlalchemy import select

from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.services.document_processing import (
    DocumentProcessingError,
    UnsupportedDocumentError,
    extract_text,
    split_text,
)
from app.services.knowledge import (
    create_knowledge_base,
    delete_document,
    delete_knowledge_base,
    get_knowledge_base_for_agent,
    get_owned_document,
    get_owned_knowledge_base,
    ingest_document,
    list_documents,
    list_knowledge_bases,
    search_knowledge_base,
)


PRICING_TEXT = (
    "Our dental clinic offers the following pricing. "
    "The consultation cost is fifty dollars per session. "
    "A dental cleaning appointment costs eighty dollars. "
    "We accept cash and all major credit cards."
)

HOURS_TEXT = (
    "Our dental clinic opening hours are Monday to Friday from nine to five. "
    "We are closed on weekends and public holidays."
)


def _chunks_for_document(db_session, document_id: int) -> list[KnowledgeChunk]:
    return list(
        db_session.scalars(
            select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == document_id
            )
        ).all()
    )


@pytest.fixture
def knowledge_base(db_session, test_agent):
    return create_knowledge_base(
        db=db_session,
        agent_id=test_agent.id,
        name="Acme Clinic Knowledge",
        description="Services and pricing",
    )


@pytest.fixture
def ingested_pricing_document(db_session, knowledge_base):
    return ingest_document(
        db=db_session,
        knowledge_base=knowledge_base,
        filename="pricing.txt",
        content=PRICING_TEXT.encode("utf-8"),
        content_type="text/plain",
    )


class TestChunking:
    def test_only_splits_long_text(self):
        assert split_text("short text") == ["short text"]

    def test_empty_text_produces_no_chunks(self):
        assert split_text("   \n\t ") == []

    def test_splits_into_multiple_ordered_chunks(self):
        text = " ".join(f"sentence number {i} here" for i in range(200))
        chunks = split_text(text, max_chars=400, overlap=60)

        assert len(chunks) > 1
        assert all(len(chunk) <= 400 for chunk in chunks)
        assert all(chunk for chunk in chunks)

    def test_rejects_invalid_overlap(self):
        with pytest.raises(ValueError):
            split_text("some text", max_chars=100, overlap=150)


class TestTextExtraction:
    def test_extracts_txt(self):
        source_type, text = extract_text(
            b"Hello knowledge base",
            "notes.txt",
        )

        assert source_type == "txt"
        assert text == "Hello knowledge base"

    def test_rejects_unsupported_extension(self):
        with pytest.raises(UnsupportedDocumentError):
            extract_text(b"data", "data.docx")

    def test_rejects_blank_document(self):
        with pytest.raises(DocumentProcessingError):
            extract_text(b"   ", "blank.txt")

    def test_extracts_pdf_text(self):
        pdf = _minimal_pdf("Hello from the PDF knowledge base")
        source_type, text = extract_text(pdf, "document.pdf")

        assert source_type == "pdf"
        assert "Hello from the PDF knowledge base" in text


class TestKnowledgeBaseCrud:
    def test_creates_knowledge_base(self, db_session, test_agent, knowledge_base):
        assert knowledge_base.agent_id == test_agent.id
        assert knowledge_base.name == "Acme Clinic Knowledge"

        stored = get_knowledge_base_for_agent(db_session, test_agent.id)
        assert stored is not None
        assert stored.id == knowledge_base.id

    def test_get_knowledge_base_for_agent_returns_none_when_absent(self, db_session, test_agent):
        assert get_knowledge_base_for_agent(db_session, test_agent.id) is None

    def test_ownership_check_returns_none_for_other_owner(
        self, db_session, knowledge_base, test_user
    ):
        assert get_owned_knowledge_base(db_session, knowledge_base.id, 999) is None
        assert get_owned_knowledge_base(db_session, knowledge_base.id, test_user.id) is not None

    def test_list_only_returns_owned_bases(self, db_session, knowledge_base, test_user):
        bases = list_knowledge_bases(db_session, test_user.id)
        assert len(bases) == 1
        assert bases[0].id == knowledge_base.id

        bases_other = list_knowledge_bases(db_session, 999)
        assert bases_other == []

    def test_delete_knowledge_base_removes_everything(
        self, db_session, knowledge_base, ingested_pricing_document
    ):
        delete_knowledge_base(db_session, knowledge_base)

        assert get_knowledge_base_for_agent(db_session, knowledge_base.agent_id) is None
        assert db_session.get(KnowledgeDocument, ingested_pricing_document.id) is None
        assert _chunks_for_document(db_session, ingested_pricing_document.id) == []


class TestIngestDocument:
    def test_ingests_txt_and_stores_chunks(
        self, db_session, knowledge_base, ingested_pricing_document
    ):
        assert ingested_pricing_document.status == "completed"
        assert ingested_pricing_document.source_type == "txt"

        chunks = _chunks_for_document(db_session, ingested_pricing_document.id)
        assert len(chunks) > 0
        assert chunks[0].chunk_index == 1
        assert len(chunks[0].embedding) > 0

        combined = " ".join(c.content for c in chunks)
        assert "consultation cost is fifty dollars" in combined

    def test_reports_failed_extraction(
        self, db_session, test_agent, knowledge_base
    ):
        document = ingest_document(
            db=db_session,
            knowledge_base=knowledge_base,
            filename="empty.txt",
            content=b"   ",
        )

        assert document.status == "failed"
        assert document.error is not None
        assert _chunks_for_document(db_session, document.id) == []


class TestSearchKnowledgeBase:
    def test_returns_most_relevant_chunk(
        self, db_session, knowledge_base, ingested_pricing_document
    ):
        result = search_knowledge_base(
            db=db_session,
            agent_id=knowledge_base.agent_id,
            query="consultation cost per session",
        )

        assert result["found"] is True
        assert len(result["results"]) > 0

        top = result["results"][0]
        assert "fifty dollars" in top["content"]
        assert top["document_id"] == ingested_pricing_document.id
        assert top["score"] > 0.30

    def test_returns_no_results_below_threshold(
        self, db_session, knowledge_base, ingested_pricing_document
    ):
        result = search_knowledge_base(
            db=db_session,
            agent_id=knowledge_base.agent_id,
            query="violet walrus kangaroo",
        )

        assert result["found"] is False
        assert result["results"] == []

    def test_returns_none_when_no_knowledge_base(self, db_session, test_agent):
        result = search_knowledge_base(
            db=db_session,
            agent_id=test_agent.id,
            query="consultation cost",
        )

        assert result["found"] is False
        assert result["results"] == []
        assert "no knowledge base" in result["message"].lower()

    def test_is_scoped_to_agent(
        self, db_session, test_user, test_agent, knowledge_base, ingested_pricing_document
    ):
        from app.models.agent import Agent

        other_agent = Agent(
            owner_id=test_user.id,
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
            name="Other Base",
        )
        ingest_document(
            db=db_session,
            knowledge_base=other_base,
            filename="hours.txt",
            content=HOURS_TEXT.encode("utf-8"),
        )

        pricing_search = search_knowledge_base(
            db=db_session,
            agent_id=test_agent.id,
            query="consultation cost per session",
        )

        assert pricing_search["found"] is True
        assert all(
            r["document_id"] == ingested_pricing_document.id
            for r in pricing_search["results"]
        )

        hours_search = search_knowledge_base(
            db=db_session,
            agent_id=test_agent.id,
            query="opening hours monday friday nine five",
        )

        assert hours_search["found"] is False


class TestDeleteDocument:
    def test_deletes_document_and_chunks(
        self, db_session, knowledge_base, ingested_pricing_document
    ):
        delete_document(db_session, ingested_pricing_document)

        assert db_session.get(KnowledgeDocument, ingested_pricing_document.id) is None
        assert _chunks_for_document(db_session, ingested_pricing_document.id) == []
        assert list_documents(db_session, knowledge_base) == []

    def test_get_owned_document_hides_other_owners_document(
        self, db_session, knowledge_base, ingested_pricing_document, test_agent
    ):
        assert get_owned_document(
            db_session, ingested_pricing_document.id, 999
        ) is None
        assert get_owned_document(
            db_session, ingested_pricing_document.id, test_agent.owner_id
        ) is not None


def _minimal_pdf(text: str) -> bytes:
    """Build a minimal single-page PDF containing ``text``."""
    content_stream = (
        "BT /F1 24 Tf 72 720 Td "
        f"({text}) Tj ET"
    ).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        (
            b"<< /Length " + str(len(content_stream)).encode() + b" >>\n"
            b"stream\n" + content_stream + b"\nendstream"
        ),
        (
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
        ),
    ]

    output = bytearray(b"%PDF-1.4\n")
    offsets = []

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_offset = len(output)

    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")

    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode())

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )

    return bytes(output)