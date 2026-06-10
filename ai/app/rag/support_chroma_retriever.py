from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings

from app.core.config import get_settings
from app.rag.embeddings import get_embedding_provider
from app.schemas import StartupProfile


class SupportProgramChromaRetriever:
    def __init__(
        self,
        *,
        chroma_path: str | Path | None = None,
        collection_name: str = "support_programs",
        embedding_dimensions: int = 3072,
        embedding_provider: str | None = None,
    ):
        settings = get_settings()
        self.embedding_provider = get_embedding_provider(embedding_provider, dimensions=embedding_dimensions)
        selected_chroma_path = chroma_path or settings.support_rag_chroma_path
        self.client = chromadb.PersistentClient(
            path=str(selected_chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})
        self.retrieval_mode = "chroma"

    def search(self, *, profile: StartupProfile, query: str, limit: int) -> list[dict[str, Any]]:
        if self.count() == 0:
            return []

        query_text = self._retrieval_query(profile, query)
        query_embedding = self.embedding_provider.embed(query_text)
        raw = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(limit * 4, limit),
            include=["documents", "metadatas", "distances"],
        )
        results = self._flatten(raw)
        results.sort(key=lambda item: item.get("eligibility_score", 0), reverse=True)
        return results[:limit]

    def count(self) -> int:
        return int(self.collection.count())

    def _flatten(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        results = []
        for text, metadata, distance in zip(documents, metadatas, distances, strict=False):
            metadata = metadata or {}
            similarity = max(0.0, 1.0 - float(distance or 0.0))
            score = int(max(0, min(100, round(similarity * 100))))
            item = {
                "id": metadata.get("program_id"),
                "title": metadata.get("title") or "지원사업 후보",
                "url": metadata.get("apply_url") or metadata.get("detail_url") or metadata.get("source_url"),
                "summary": metadata.get("summary"),
                "source_note": f"support_chroma:{metadata.get('source', '-')}",
                "eligibility_score": score,
                "fit_level": self._fit_level(score),
                "score_breakdown": {"semantic_similarity": round(similarity, 4)},
                "matched_keywords": self._csv(metadata.get("tags")),
                "why_matched": ["질문/프로필과 지원사업 공고 내용의 의미 유사도가 높습니다."],
                "eligibility_gaps": [],
                "required_documents": self._csv(metadata.get("required_documents")),
                "application_strategy": [
                    "공고 상세 페이지에서 신청 기간과 자격 요건을 먼저 확인하세요.",
                    "사업계획서에는 현재 아이템의 30일 검증 계획과 예산 사용처를 연결하세요.",
                ],
                "retrieval": {
                    "source": "support_chroma",
                    "semantic_similarity": round(similarity, 4),
                    "chunk": text,
                },
                "source_chunks": [text] if text else [],
                "application_end_date": metadata.get("application_end_date"),
                "support_type": metadata.get("support_type"),
                "support_amount": metadata.get("support_amount"),
                "organization": metadata.get("organization"),
                "region_condition": metadata.get("region_condition"),
                "business_stage_condition": metadata.get("business_stage_condition"),
                "industry_condition": metadata.get("industry_condition"),
            }
            results.append(item)
        return results

    def _retrieval_query(self, profile: StartupProfile, query: str) -> str:
        return " ".join(
            [
                query or "",
                profile.region or "",
                profile.startup_stage or "",
                profile.major or "",
                " ".join(profile.interests),
                " ".join(profile.experiences),
                " ".join(profile.preferred_channels),
                profile.memo or "",
            ]
        )

    def _csv(self, value: Any) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in str(value).split(",") if item.strip()]

    def _fit_level(self, score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 50:
            return "medium"
        return "low"
