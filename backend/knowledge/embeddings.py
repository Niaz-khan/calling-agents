"""Embedding providers for knowledge-base semantic search."""

from typing import Protocol

from django.conf import settings


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class OpenAIEmbeddingProvider:
    def __init__(self, model, dimensions, api_key):
        if not api_key:
            raise EmbeddingError("LLM_API_KEY is not configured")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise EmbeddingError("The openai package is not installed") from exc
        self.model = model
        self.dimensions = dimensions
        self._client = OpenAI(api_key=api_key)

    def embed(self, texts):
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
            )
        except Exception as exc:
            raise EmbeddingError(f"Embedding request failed: {exc}") from exc
        return [normalize_embedding(item.embedding) for item in response.data]


_provider = None


def get_embedding_provider():
    global _provider
    if _provider is None:
        provider_type = settings.EMBEDDING_PROVIDER
        if provider_type == "openai":
            _provider = OpenAIEmbeddingProvider(
                settings.EMBEDDING_MODEL,
                settings.EMBEDDING_DIMENSIONS,
                settings.LLM_API_KEY,
            )
        else:
            raise EmbeddingError(f"Unsupported embedding provider: {provider_type}")
    return _provider


def set_embedding_provider(provider=None):
    global _provider
    _provider = provider


def normalize_embedding(vector):
    magnitude = sum(value * value for value in vector) ** 0.5
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def cosine_similarity(vector_a, vector_b):
    return sum(a * b for a, b in zip(vector_a, vector_b))