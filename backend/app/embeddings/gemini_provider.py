import math
import os

from google import genai
from google.genai import types

from app.embeddings.base import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dimensions: int = 1536) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        return self._embed_with_task_type(text, task_type="SEMANTIC_SIMILARITY")

    def embed_document(self, text: str) -> list[float]:
        return self._embed_with_task_type(text, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed_with_task_type(text, task_type="RETRIEVAL_QUERY")

    def _embed_with_task_type(self, text: str, task_type: str) -> list[float]:
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimensions,
            ),
        )
        [embedding] = response.embeddings
        values = list(embedding.values)
        if self.model == "gemini-embedding-001" and self.dimensions != 3072:
            return normalize(values)
        return values


def normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return values
    return [value / norm for value in values]
