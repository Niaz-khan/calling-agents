from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.agent import Agent
from app.models.knowledge import (
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeDocumentDetail,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge import (
    create_knowledge_base,
    delete_document,
    delete_knowledge_base,
    get_owned_document,
    get_owned_knowledge_base,
    ingest_document,
    list_documents,
    list_knowledge_bases,
    search_knowledge_base,
)


router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
)


def _get_owned_agent(
    db: Session,
    agent_id: int,
    owner_id: int,
) -> Agent:
    agent = db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.owner_id == owner_id,
        )
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return agent


def _get_owned_base_or_404(
    db: Session,
    knowledge_base_id: int,
    owner_id: int,
) -> KnowledgeBase:
    knowledge_base = get_owned_knowledge_base(
        db,
        knowledge_base_id,
        owner_id,
    )

    if knowledge_base is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    return knowledge_base


def _get_owned_document_or_404(
    db: Session,
    document_id: int,
    owner_id: int,
) -> KnowledgeDocument:
    document = get_owned_document(
        db,
        document_id,
        owner_id,
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.post(
    "/bases",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_base(
    base_data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_agent(db, base_data.agent_id, current_user.id)

    return create_knowledge_base(
        db=db,
        agent_id=base_data.agent_id,
        name=base_data.name,
        description=base_data.description,
    )


@router.get(
    "/bases",
    response_model=list[KnowledgeBaseResponse],
)
def list_bases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_knowledge_bases(db, current_user.id)


@router.get(
    "/bases/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
def get_base(
    knowledge_base_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_base_or_404(
        db,
        knowledge_base_id,
        current_user.id,
    )


@router.delete(
    "/bases/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_base(
    knowledge_base_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    knowledge_base = _get_owned_base_or_404(
        db,
        knowledge_base_id,
        current_user.id,
    )

    delete_knowledge_base(db, knowledge_base)

    return None


@router.post(
    "/bases/{knowledge_base_id}/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    knowledge_base_id: int,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    knowledge_base = _get_owned_base_or_404(
        db,
        knowledge_base_id,
        current_user.id,
    )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    return ingest_document(
        db=db,
        knowledge_base=knowledge_base,
        filename=file.filename or "document",
        content=content,
        content_type=file.content_type,
    )


@router.get(
    "/bases/{knowledge_base_id}/documents",
    response_model=list[KnowledgeDocumentResponse],
)
def get_base_documents(
    knowledge_base_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    knowledge_base = _get_owned_base_or_404(
        db,
        knowledge_base_id,
        current_user.id,
    )

    return list_documents(db, knowledge_base)


@router.get(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentDetail,
)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document_or_404(
        db,
        document_id,
        current_user.id,
    )

    chunks = db.scalars(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.document_id == document.id)
        .order_by(KnowledgeChunk.chunk_index.asc())
    ).all()

    data = KnowledgeDocumentDetail.model_validate(document)
    data.chunks = chunks

    return data


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document_endpoint(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = _get_owned_document_or_404(
        db,
        document_id,
        current_user.id,
    )

    delete_document(db, document)

    return None


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
)
def search(
    search_data: KnowledgeSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_agent(db, search_data.agent_id, current_user.id)

    return search_knowledge_base(
        db=db,
        agent_id=search_data.agent_id,
        query=search_data.query,
        limit=search_data.limit,
        threshold=search_data.threshold,
    )