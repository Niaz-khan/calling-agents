"""Org-scoped knowledge base business logic."""

from django.conf import settings

from .document_processing import (
    DocumentProcessingError,
    extract_text,
    split_text,
)
from .embeddings import (
    EmbeddingError,
    cosine_similarity,
    get_embedding_provider,
    normalize_embedding,
)
from .models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument


def create_knowledge_base(organization, agent, name, description=None):
    return KnowledgeBase.objects.create(
        organization=organization, agent=agent, name=name, description=description
    )


def delete_knowledge_base(knowledge_base):
    knowledge_base.delete()


def get_owned_knowledge_base(organization, knowledge_base_id):
    return (
        KnowledgeBase.objects.filter(
            organization=organization, id=knowledge_base_id
        )
        .select_related("agent")
        .first()
    )


def list_documents(knowledge_base):
    return KnowledgeDocument.objects.filter(knowledge_base=knowledge_base).order_by(
        "-created_at"
    )


def delete_document(document):
    document.delete()


def ingest_document(organization, knowledge_base, filename, content, content_type=None):
    document = KnowledgeDocument.objects.create(
        knowledge_base=knowledge_base,
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
        try:
            embeddings = get_embedding_provider().embed(chunks)
        except EmbeddingError as exc:
            raise DocumentProcessingError(f"Embedding failed: {exc}") from exc

        document.source_type = source_type
        document.status = "completed"
        document.save(update_fields=["source_type", "status"])

        KnowledgeChunk.objects.bulk_create(
            KnowledgeChunk(
                document=document,
                chunk_index=index + 1,
                content=chunk_text,
                embedding=normalize_embedding(embedding),
            )
            for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings))
        )
    except DocumentProcessingError as exc:
        document.source_type = _resolve_or_default(filename)
        document.status = "failed"
        document.error = str(exc)
        document.save(update_fields=["source_type", "status", "error"])

    return document


def _resolve_or_default(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else "txt"


def search_knowledge_base(organization, agent_id, query, limit=None, threshold=None):
    limit = limit or settings.KNOWLEDGE_SEARCH_LIMIT
    threshold = (
        threshold
        if threshold is not None
        else settings.KNOWLEDGE_RELEVANCE_THRESHOLD
    )

    knowledge_base = KnowledgeBase.objects.filter(
        organization=organization, agent_id=agent_id
    ).first()

    if knowledge_base is None:
        return {
            "found": False,
            "query": query,
            "results": [],
            "message": "No knowledge base is configured for this agent.",
        }

    try:
        query_vector = normalize_embedding(
            get_embedding_provider().embed([query])[0]
        )
    except EmbeddingError as exc:
        return {
            "found": False,
            "query": query,
            "results": [],
            "message": str(exc),
        }

    chunks = (
        KnowledgeChunk.objects.filter(document__knowledge_base=knowledge_base)
        .select_related("document")
        .order_by("chunk_index")
    )

    scored = [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document_id,
            "document_filename": chunk.document.filename,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "score": round(cosine_similarity(query_vector, chunk.embedding), 4),
        }
        for chunk in chunks
    ]

    scored.sort(key=lambda item: item["score"], reverse=True)

    results = [item for item in scored if item["score"] >= threshold][:limit]

    return {"found": len(results) > 0, "query": query, "results": results}