from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol


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
