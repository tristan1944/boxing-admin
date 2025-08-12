from __future__ import annotations

"""
EMBED_SUMMARY: Embedding providers (fake and OpenAI) and cosine similarity helpers.
EMBED_TAGS: embeddings, vectors, cosine, openai, provider
"""

import hashlib
import math
import random
from typing import Iterable, List, Dict

import httpx

from .config import get_settings


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class EmbeddingProvider:
    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:  # pragma: no cover - interface
        raise NotImplementedError


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions
        self._cache: Dict[str, List[float]] = {}

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            h_bytes = hashlib.sha256(text.encode("utf-8")).digest()
            h_key = h_bytes.hex()
            cached = self._cache.get(h_key)
            if cached is not None:
                vectors.append(cached)
                continue
            seed = int.from_bytes(h_bytes[:8], byteorder="big", signed=False)
            rng = random.Random(seed)
            vec = [rng.uniform(-1.0, 1.0) for _ in range(self.dimensions)]
            normed = _l2_normalize(vec)
            self._cache[h_key] = normed
            vectors.append(normed)
        return vectors


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": list(texts)}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=30) as client:
            resp = client.post("https://api.openai.com/v1/embeddings", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embeddings_provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI API key not configured")
        return OpenAIEmbeddingProvider(api_key=settings.openai_api_key, model=settings.openai_embeddings_model)
    return FakeEmbeddingProvider(dimensions=settings.embeddings_dimensions)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    # Inputs expected to be L2 normalized; safe-guard anyway
    if not a or not b or len(a) != len(b):
        return 0.0
    # No need to renormalize if upstream normalized
    return sum(x * y for x, y in zip(a, b))


