import hashlib
import math

from app.embeddings.base import EmbeddingProvider


class LocalDevEmbeddingProvider(EmbeddingProvider):
    """Deterministic placeholder embeddings for plumbing tests only."""

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimensions
        tokens = tokenize(text)
        if not tokens:
            return values

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign

        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return values
        return [value / norm for value in values]


def tokenize(text: str) -> list[str]:
    return [part.strip().lower() for part in text.replace("\n", " ").split(" ") if part.strip()]
