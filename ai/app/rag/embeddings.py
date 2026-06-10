from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Protocol

import httpx

from app.core.config import Settings, get_settings


class EmbeddingProvider(Protocol):
    dimensions: int

    def embed(self, text: str) -> list[float]:
        ...


class HashEmbeddingProvider:
    """Dependency-free embedding placeholder for local vector-store wiring.

    This keeps the RAG pipeline shaped like real embedding retrieval while the
    hackathon GMS embedding endpoint or external vector DB is not fixed yet.
    Swap this class with a GMS/Chroma/FAISS-backed provider later.
    """

    def __init__(self, dimensions: int = 384):
        if dimensions < 32:
            raise ValueError("Embedding dimensions must be at least 32.")
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokens(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _tokens(self, text: str) -> set[str]:
        normalized = re.sub(r"[,/|·\-\n\r\t]", " ", text.lower())
        raw_tokens = {token.strip() for token in normalized.split() if token.strip()}
        tokens = set(raw_tokens)

        aliases = {
            "디자인": {"브랜딩", "브랜드", "로고", "콘텐츠"},
            "브랜드": {"브랜딩"},
            "브랜딩": {"브랜드"},
            "sns": {"콘텐츠", "마케팅", "홍보"},
            "콘텐츠": {"sns", "마케팅", "홍보"},
            "카페": {"소상공인", "로컬", "매장"},
            "알바": {"매장", "운영", "소상공인"},
            "로컬": {"지역", "소상공인"},
            "예비창업": {"초기창업", "창업"},
            "초기창업": {"예비창업", "창업"},
            "청년": {"청년창업"},
        }
        for token in raw_tokens:
            for source, targets in aliases.items():
                if source in token:
                    tokens.update(targets)

        # Character n-grams make Korean compound nouns searchable even when
        # token boundaries differ between the query and source document.
        for token in raw_tokens:
            compact = re.sub(r"\s+", "", token)
            if len(compact) >= 3:
                tokens.update(compact[index : index + 2] for index in range(len(compact) - 1))
                tokens.update(compact[index : index + 3] for index in range(len(compact) - 2))

        return tokens


class OpenAIEmbeddingProvider:
    """GMS-proxied OpenAI embeddings provider with batch input support."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.dimensions = int(self.settings.rag_embedding_dimensions)

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str], *, batch_size: int = 64) -> list[list[float]]:
        if not texts:
            return []
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            embeddings.extend(self._embed_batch(texts[start : start + batch_size]))
        return embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.settings.gms_api_key:
            raise RuntimeError("GMS_API_KEY is required when RAG_EMBEDDING_PROVIDER=openai.")

        url = self.settings.openai_embedding_base_url.rstrip("/") + "/" + self.settings.openai_embedding_path.lstrip("/")
        payload = {
            "model": self.settings.openai_embedding_model,
            "input": texts,
        }
        with httpx.Client(timeout=self.settings.gms_timeout_seconds) as client:
            response = client.post(
                url,
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
        vectors = self._extract_embeddings(response.json())
        if len(vectors) != len(texts):
            raise RuntimeError(f"Expected {len(texts)} embeddings, got {len(vectors)}.")
        if vectors:
            self.dimensions = len(vectors[0])
        return [self._normalize(vector) for vector in vectors]

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.gms_api_key}",
        }

    def _extract_embeddings(self, payload: dict[str, Any]) -> list[list[float]]:
        data = payload.get("data")
        if not isinstance(data, list):
            return []
        ordered = sorted(data, key=lambda item: int(item.get("index", 0)) if isinstance(item, dict) else 0)
        vectors = []
        for item in ordered:
            if not isinstance(item, dict):
                continue
            embedding = item.get("embedding")
            if isinstance(embedding, list):
                vectors.append([float(value) for value in embedding])
        return vectors

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def get_embedding_provider(
    provider: str | None = None,
    *,
    dimensions: int | None = None,
    settings: Settings | None = None,
) -> EmbeddingProvider:
    settings = settings or get_settings()
    selected = (provider or settings.rag_embedding_provider or "hash").strip().lower()
    if selected in {"openai", "text-embedding-3-large", "gms-openai"}:
        return OpenAIEmbeddingProvider(settings=settings)
    if selected in {"hash", "local"}:
        return HashEmbeddingProvider(dimensions=dimensions or settings.rag_embedding_dimensions)
    raise ValueError(f"Unsupported embedding provider: {selected}")
