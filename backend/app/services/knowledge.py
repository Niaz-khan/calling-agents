from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.embeddings import (
    cosine_similarity,
    get_embedding_provider,
    normalize_embedding,
)
from app.config import settings
from app.models.agent import Agent
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.services.document_processing import (
    DocumentProcessingError,
    extract_text,
    split_text,
)


class KnowledgeBaseNotFoundError(Exception):
    pass


def create_knowledge_base(
    db: Session,
    agent_id: int,
    name: str,
    description: str | None = None,
) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(
        agent_id=agent_id,
        name=name,
        description=description,
    )

    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)

    return knowledge_base


def get_knowledge_base_for_agent(
    db: Session,
    agent_id: int,
) -> KnowledgeBase | None:
    return db.scalar(
        select(KnowledgeBase).where(KnowledgeBase.agent_id == agent_id)
    )


def get_owned_knowledge_base(
    db: Session,
    knowledge_base_id: int,
    owner_id: int,
) -> KnowledgeBase | None:
    statement = (
        select(KnowledgeBase)
        .join(Agent, Agent.id == KnowledgeBase.agent_id)
        .where(
            KnowledgeBase.id == knowledge_base_id,
            Agent.owner_id == owner_id,
        )
    )

    return db.scalar(statement)


def list_knowledge_bases(
    db: Session,
    owner_id: int,
) -> list[KnowledgeBase]:
    statement = (
        select(KnowledgeBase)
        .join(Agent, Agent.id == KnowledgeBase.agent_id)
        .where(Agent.owner_id == owner_id)
        .order_by(KnowledgeBase.id.desc())
    )

    return list(db.scalars(statement).all())


def delete_knowledge_base(
    db: Session,
    knowledge_base: KnowledgeBase,
) -> None:
    document_ids = db.scalars(
        select(KnowledgeDocument.id).where(
            KnowledgeDocument.knowledge_base_id == knowledge_base.id
        )
    ).all()

    if document_ids:
        db.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.document_id.in_(document_ids)
            )
        )

    db.execute(
        delete(KnowledgeDocument).where(
            KnowledgeDocument.knowledge_base_id == knowledge_base.id
        )
    )
    db.delete(knowledge_base)
    db.commit()


def get_owned_document(
    db: Session,
    document_id: int,
    owner_id: int,
) -> KnowledgeDocument | None:
    statement = (
        select(KnowledgeDocument)
        .join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id)
        .join(Agent, Agent.id == KnowledgeBase.agent_id)
        .where(
            KnowledgeDocument.id == document_id,
            Agent.owner_id == owner_id,
        )
    )

    return db.scalar(statement)


def list_documents(
    db: Session,
    knowledge_base: KnowledgeBase,
) -> list[KnowledgeDocument]:
    statement = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.knowledge_base_id == knowledge_base.id)
        .order_by(KnowledgeDocument.id.desc())
    )

    return list(db.scalars(statement).all())


def delete_document(
    db: Session,
    document: KnowledgeDocument,
) -> None:
    db.execute(
        delete(KnowledgeChunk).where(
            KnowledgeChunk.document_id == document.id
        )
    )
    db.delete(document)
    db.commit()


def ingest_document(
    db: Session,
    knowledge_base: KnowledgeBase,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        knowledge_base_id=knowledge_base.id,
        filename=filename,
        content_type=content_type,
        source_type="txt",
        title=filename,
        status="processing",
    )

    try:
        source_type, text = extract_text(content, filename)
        chunks = split_text(text)

        if not chunks:
            raise DocumentProcessingError("Document produced no chunks")

        embeddings = get_embedding_provider().embed(chunks)

        document.source_type = source_type
        document.status = "completed"

        db.add(document)
        db.flush()

        for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            db.add(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index + 1,
                    content=chunk_text,
                    embedding=normalize_embedding(embedding),
                )
            )

    except DocumentProcessingError as e:
        document.source_type = _resolve_or_default(filename)
        document.status = "failed"
        document.error = str(e)
        db.add(document)

    db.commit()
    db.refresh(document)

    return document


def _resolve_or_default(filename: str) -> str:
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()

    return "txt"


def search_knowledge_base(
    db: Session,
    agent_id: int,
    query: str,
    limit: int | None = None,
    threshold: float | None = None,
) -> dict:
    limit = limit or settings.knowledge_search_limit
    threshold = (
        threshold
        if threshold is not None
        else settings.knowledge_relevance_threshold
    )

    knowledge_base = get_knowledge_base_for_agent(db, agent_id)

    if knowledge_base is None:
        return {
            "found": False,
            "query": query,
            "results": [],
            "message": "No knowledge base is configured for this agent.",
        }

    query_vector = normalize_embedding(
        get_embedding_provider().embed([query])[0]
    )

    statement = (
        select(KnowledgeChunk, KnowledgeDocument)
        .join(
            KnowledgeDocument,
            KnowledgeDocument.id == KnowledgeChunk.document_id,
        )
        .join(
            KnowledgeBase,
            KnowledgeBase.id == KnowledgeDocument.knowledge_base_id,
        )
        .where(KnowledgeBase.id == knowledge_base.id)
    )

    rows = db.execute(statement).all()

    scored = [
        {
            "chunk_id": chunk.id,
            "document_id": document.id,
            "document_filename": document.filename,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "score": round(
                cosine_similarity(query_vector, chunk.embedding),
                4,
            ),
        }
        for chunk, document in rows
    ]

    scored.sort(key=lambda item: item["score"], reverse=True)

    results = [
        item
        for item in scored
        if item["score"] >= threshold
    ][:limit]

    return {
        "found": len(results) > 0,
        "query": query,
        "results": results,
    }