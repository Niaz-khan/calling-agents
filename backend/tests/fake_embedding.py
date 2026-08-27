import re
import zlib

from app.ai.embeddings import normalize_embedding
from app.config import settings


class FakeEmbeddingProvider:
    """Deterministic keyword-based embeddings for tests.

    Similar texts (sharing words) produce similar normalized vectors,
    so cosine similarity is meaningful without calling an embedding API.
    """

    def __init__(self, dimensions: int | None = None) -> None:
        self.dimensions = dimensions or settings.embedding_dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-z0-9]+", text.lower())

        for token in tokens:
            bucket = zlib.crc32(token.encode("utf-8")) % self.dimensions
            vector[bucket] += 1.0

        return normalize_embedding(vector)