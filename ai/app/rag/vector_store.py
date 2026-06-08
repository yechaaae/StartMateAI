from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from app.rag.embeddings import EmbeddingProvider


@dataclass
class VectorDocument:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class VectorSearchResult:
    document: VectorDocument
    similarity: float


class LocalVectorStore:
    """Small local vector store used until an external vector DB is attached."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        documents: list[VectorDocument] | None = None,
        persist_path: Path | None = None,
    ):
        self.embedding_provider = embedding_provider
        self.documents = documents or []
        self.persist_path = persist_path

    @classmethod
    def from_documents(
        cls,
        *,
        documents: list[VectorDocument],
        embedding_provider: EmbeddingProvider,
        persist_path: Path | None = None,
        rebuild: bool = False,
    ) -> "LocalVectorStore":
        if persist_path and persist_path.exists() and not rebuild:
            store = cls.load(persist_path=persist_path, embedding_provider=embedding_provider)
            if store._has_same_document_ids(documents):
                return store

        indexed = []
        for document in documents:
            indexed.append(
                VectorDocument(
                    id=document.id,
                    text=document.text,
                    metadata=document.metadata,
                    embedding=embedding_provider.embed(document.text),
                )
            )

        store = cls(
            embedding_provider=embedding_provider,
            documents=indexed,
            persist_path=persist_path,
        )
        if persist_path:
            store.persist()
        return store

    @classmethod
    def load(cls, *, persist_path: Path, embedding_provider: EmbeddingProvider) -> "LocalVectorStore":
        raw = json.loads(persist_path.read_text(encoding="utf-8"))
        documents = [
            VectorDocument(
                id=item["id"],
                text=item["text"],
                metadata=item.get("metadata", {}),
                embedding=item.get("embedding", []),
            )
            for item in raw.get("documents", [])
        ]
        return cls(embedding_provider=embedding_provider, documents=documents, persist_path=persist_path)

    def persist(self) -> None:
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "embedding_provider": self.embedding_provider.__class__.__name__,
            "dimensions": self.embedding_provider.dimensions,
            "documents": [
                {
                    "id": document.id,
                    "text": document.text,
                    "metadata": document.metadata,
                    "embedding": document.embedding,
                }
                for document in self.documents
            ],
        }
        self.persist_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def search(self, query: str, *, top_k: int) -> list[VectorSearchResult]:
        query_vector = self.embedding_provider.embed(query)
        results = [
            VectorSearchResult(
                document=document,
                similarity=self._cosine(query_vector, document.embedding or []),
            )
            for document in self.documents
        ]
        results.sort(key=lambda result: result.similarity, reverse=True)
        return results[:top_k]

    def _has_same_document_ids(self, documents: list[VectorDocument]) -> bool:
        indexed_ids = {document.id for document in self.documents}
        source_ids = {document.id for document in documents}
        return indexed_ids == source_ids

    def _cosine(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return sum(a * b for a, b in zip(left, right))
