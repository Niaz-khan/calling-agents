from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    agent_id: int

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    knowledge_base_id: int
    filename: str
    content_type: str | None
    source_type: str
    title: str | None
    status: str
    error: str | None
    created_at: datetime


class KnowledgeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk_index: int
    content: str


class KnowledgeDocumentDetail(KnowledgeDocumentResponse):
    chunks: list[KnowledgeChunkResponse] = Field(
        default_factory=list,
    )


class KnowledgeSearchRequest(BaseModel):
    agent_id: int

    query: str = Field(
        min_length=1,
    )

    limit: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )

    threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )


class KnowledgeSearchResultItem(BaseModel):
    chunk_id: int
    document_id: int
    document_filename: str
    chunk_index: int
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    found: bool
    query: str
    results: list[KnowledgeSearchResultItem]