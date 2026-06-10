from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import chromadb
from chromadb.config import Settings

from app.core.config import get_settings
from app.rag.embeddings import get_embedding_provider


@dataclass
class LegalSearchResult:
    id: str
    text: str
    metadata: dict[str, Any]
    distance: float
    score: float


class LegalRetriever:
    def __init__(
        self,
        *,
        chroma_path: str | Path | None = None,
        collection_name: str = "legal_sources",
        embedding_dimensions: int = 384,
        embedding_provider: str | None = None,
    ):
        settings = get_settings()
        self.embedding_provider = get_embedding_provider(embedding_provider, dimensions=embedding_dimensions)
        selected_chroma_path = chroma_path or settings.rag_chroma_path
        self.client = chromadb.PersistentClient(
            path=str(selected_chroma_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        domains: list[str] | None = None,
        source_type: str | None = None,
    ) -> list[LegalSearchResult]:
        query_embedding = self.embedding_provider.embed(query)
        raw = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k * 20, 50),
            include=["documents", "metadatas", "distances"],
        )
        results = self._flatten(raw, query=query)
        results.extend(self._keyword_results(query))
        results = self._dedupe_results(results)
        filtered = [
            result
            for result in results
            if self._domain_match(result.metadata, domains) and self._source_type_match(result.metadata, source_type)
        ]
        filtered.sort(key=lambda result: result.score, reverse=True)
        return filtered[:top_k]

    def count(self) -> int:
        return int(self.collection.count())

    def _flatten(self, raw: dict[str, Any], *, query: str) -> list[LegalSearchResult]:
        ids = raw.get("ids", [[]])[0]
        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]

        results = []
        for doc_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            score = self._score(float(distance), metadata or {}, text or "", query)
            results.append(
                LegalSearchResult(
                    id=doc_id,
                    text=text or "",
                    metadata=metadata or {},
                    distance=float(distance),
                    score=score,
                )
            )
        return results

    def _score(self, distance: float, metadata: dict[str, Any], text: str, query: str) -> float:
        similarity = 1.0 / (1.0 + max(distance, 0.0))
        priority = float(metadata.get("priority") or 0) / 100.0
        lexical = self._lexical_score(metadata, text, query)
        return round((similarity * 0.4) + (priority * 0.1) + lexical, 4)

    def _lexical_score(self, metadata: dict[str, Any], text: str, query: str) -> float:
        query_terms = self._terms(query)
        title_terms = self._terms(" ".join([str(metadata.get("article_title", "")), str(metadata.get("law_name", ""))]))
        text_terms = self._terms(text)
        title_overlap = len(query_terms & title_terms)
        text_overlap = len(query_terms & text_terms)
        phrase = self._phrase_boost(query, metadata, text)
        penalty = self._penalty(query, metadata, text)
        return max(0.0, min((title_overlap * 0.04) + (text_overlap * 0.015) + phrase - penalty, 0.65))

    def _keyword_results(self, query: str) -> list[LegalSearchResult]:
        raw = self.collection.get(include=["documents", "metadatas"])
        results = []
        for doc_id, text, metadata in zip(
            raw.get("ids", []),
            raw.get("documents", []),
            raw.get("metadatas", []),
            strict=False,
        ):
            metadata = metadata or {}
            lexical = self._lexical_score(metadata, text or "", query)
            if lexical < 0.12:
                continue
            priority = float(metadata.get("priority") or 0) / 100.0
            results.append(
                LegalSearchResult(
                    id=doc_id,
                    text=text or "",
                    metadata=metadata,
                    distance=1.0,
                    score=round((priority * 0.1) + lexical, 4),
                )
            )
        return results

    def _dedupe_results(self, results: list[LegalSearchResult]) -> list[LegalSearchResult]:
        by_id: dict[str, LegalSearchResult] = {}
        for result in results:
            existing = by_id.get(result.id)
            if existing is None or result.score > existing.score:
                by_id[result.id] = result
        return list(by_id.values())

    def _phrase_boost(self, query: str, metadata: dict[str, Any], text: str) -> float:
        haystack = " ".join([str(metadata.get("law_name", "")), str(metadata.get("article_title", "")), text])
        boost = 0.0
        phrase_groups = [
            (["영업신고", "영업 신고"], ["영업신고", "영업의 신고", "영업신고를 하여야"]),
            (["시설기준", "시설 기준", "위생 기준"], ["시설기준", "업종별 시설기준"]),
            (["통신판매", "온라인 판매"], ["통신판매업", "통신판매"]),
            (["개인정보", "전화번호", "예약자"], ["개인정보", "개인정보처리자"]),
            (["상표", "브랜드명"], ["상표", "상표등록"]),
            (["아르바이트", "고용", "근로"], ["근로계약", "근로자", "최저임금"]),
        ]
        for query_phrases, document_phrases in phrase_groups:
            if any(phrase in query for phrase in query_phrases) and any(phrase in haystack for phrase in document_phrases):
                boost += 0.18
        return min(boost, 0.45)

    def _penalty(self, query: str, metadata: dict[str, Any], text: str) -> float:
        haystack = " ".join([str(metadata.get("article_title", "")), text])
        penalty_terms = ["지위승계", "해촉", "위원", "교육", "지원", "인증기준"]
        if "폐업" not in query and "폐업신고" in haystack:
            return 0.3
        if any(term in query for term in penalty_terms):
            return 0.0
        return 0.12 if any(term in haystack for term in penalty_terms) else 0.0

    def _domain_match(self, metadata: dict[str, Any], domains: list[str] | None) -> bool:
        if not domains:
            return True
        haystack = f",{metadata.get('domains', '')},"
        return any(f",{domain}," in haystack for domain in domains)

    def _source_type_match(self, metadata: dict[str, Any], source_type: str | None) -> bool:
        if not source_type:
            return True
        return metadata.get("source_type") == source_type

    def _terms(self, text: str) -> set[str]:
        raw_tokens = {token for token in re.split(r"[\s,./|()ㆍ·<>\"']+", text.lower()) if len(token) >= 2}
        terms = set(raw_tokens)
        for token in raw_tokens:
            compact = re.sub(r"[^0-9a-z가-힣]+", "", token)
            if len(compact) >= 3:
                terms.update(compact[index : index + 2] for index in range(len(compact) - 1))
                terms.update(compact[index : index + 3] for index in range(len(compact) - 2))
        return terms
