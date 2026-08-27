from typing import Protocol

from openai import OpenAI

from app.config import settings


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into normalized vectors."""
        ...


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.model = model or settings.embedding_model
        self.dimensions = dimensions or settings.embedding_dimensions
        self._client = OpenAI(api_key=settings.llm_api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self.dimensions,
        )

        return [
            normalize_embedding(item.embedding)
            for item in response.data
        ]


_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider

    if _provider is None:
        if settings.embedding_provider == "openai":
            _provider = OpenAIEmbeddingProvider()
        else:
            raise RuntimeError(
                f"Unsupported embedding provider: {settings.embedding_provider}"
            )

    return _provider


def set_embedding_provider(provider: EmbeddingProvider | None) -> None:
    global _provider

    _provider = provider


def normalize_embedding(vector: list[float]) -> list[float]:
    magnitude = sum(value * value for value in vector) ** 0.5

    if magnitude == 0:
        return vector

    return [value / magnitude for value in vector]


def cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:
    return sum(
        a * b
        for a, b in zip(vector_a, vector_b)
    )