from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.rag.embeddings import HashEmbeddingProvider
from app.rag.vector_store import LocalVectorStore, VectorDocument, VectorSearchResult
from app.schemas import StartupProfile


class SupportProgramRetriever:
    def __init__(
        self,
        programs: list[dict[str, Any]],
        *,
        vector_store: LocalVectorStore | None = None,
        retrieval_mode: str = "hybrid",
    ):
        self.programs = programs
        self.vector_store = vector_store
        self.retrieval_mode = self._normalize_mode(retrieval_mode)

    @classmethod
    def from_default(
        cls,
        *,
        retrieval_mode: str = "hybrid",
        vector_store_path: str | None = None,
        embedding_dimensions: int = 384,
    ) -> "SupportProgramRetriever":
        return cls(programs=[], retrieval_mode=retrieval_mode)

    @classmethod
    def from_sample(
        cls,
        *,
        retrieval_mode: str = "hybrid",
        vector_store_path: str | None = None,
        embedding_dimensions: int = 384,
    ) -> "SupportProgramRetriever":
        data_path = Path(__file__).resolve().parents[1] / "data" / "support_programs.sample.json"
        programs = json.loads(data_path.read_text(encoding="utf-8"))
        retrieval_mode = cls._normalize_mode(retrieval_mode)
        vector_store = None
        if retrieval_mode in {"vector", "hybrid"}:
            embedding_provider = HashEmbeddingProvider(dimensions=embedding_dimensions)
            persist_path = Path(vector_store_path) if vector_store_path else None
            if persist_path and not persist_path.is_absolute():
                persist_path = Path.cwd() / persist_path
            vector_store = LocalVectorStore.from_documents(
                documents=cls._program_documents(programs),
                embedding_provider=embedding_provider,
                persist_path=persist_path,
            )
        return cls(programs, vector_store=vector_store, retrieval_mode=retrieval_mode)

    @staticmethod
    def _normalize_mode(retrieval_mode: str) -> str:
        normalized = (retrieval_mode or "hybrid").strip().lower()
        if normalized not in {"keyword", "vector", "hybrid"}:
            return "hybrid"
        return normalized

    def search(self, *, profile: StartupProfile, query: str, limit: int) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        vector_hits = self._vector_hits(profile=profile, query=query, limit=limit)
        candidate_indices = self._candidate_indices(vector_hits)
        query_terms = self._terms(query)
        interest_terms = self._terms(" ".join(profile.interests))
        skill_terms = self._terms(" ".join([profile.major or "", *profile.experiences]))
        profile_terms = self._terms(
            " ".join(
                [
                    profile.region or "",
                    profile.startup_stage,
                    profile.major or "",
                    " ".join(profile.interests),
                    " ".join(profile.experiences),
                ]
            )
        )
        terms = query_terms | profile_terms

        for index, program in enumerate(self.programs):
            if candidate_indices is not None and index not in candidate_indices:
                continue
            hit = vector_hits.get(index, {})
            semantic_similarity = float(hit.get("similarity", 0.0))
            program_terms = self._terms(
                " ".join(
                    [
                        program.get("title", ""),
                        program.get("region", ""),
                        program.get("stage", ""),
                        " ".join(program.get("keywords", [])),
                        " ".join(program.get("documents", [])),
                        program.get("summary", ""),
                    ]
                )
            )
            keyword_terms = self._terms(" ".join(program.get("keywords", [])))
            matched_terms = sorted(terms & program_terms)
            matched_keywords = sorted((interest_terms | skill_terms | query_terms) & keyword_terms)
            score_breakdown = {
                "region_fit": self._region_score(profile, program),
                "stage_fit": self._stage_score(profile, program),
                "keyword_fit": self._keyword_score(matched_terms, matched_keywords),
                "query_fit": self._query_score(query_terms, program_terms),
                "budget_support_fit": self._budget_support_score(profile, program_terms),
                "document_readiness": self._document_readiness_score(profile, program),
                "semantic_similarity": self._semantic_score(semantic_similarity),
            }
            score = self._weighted_score(score_breakdown)

            item = dict(program)
            item["eligibility_score"] = score
            item["fit_level"] = self._fit_level(score)
            item["score_breakdown"] = score_breakdown
            item["matched_terms"] = matched_terms
            item["matched_keywords"] = matched_keywords
            item["why_matched"] = self._why(profile, program, matched_keywords, semantic_similarity)
            item["eligibility_gaps"] = self._eligibility_gaps(profile, program)
            item["required_documents"] = program.get("documents", [])
            item["application_strategy"] = self._application_strategy(profile, program, matched_keywords)
            item["retrieval"] = {
                "mode": self.retrieval_mode,
                "semantic_similarity": round(semantic_similarity, 4),
                "semantic_score": score_breakdown["semantic_similarity"],
                "vector_hits": hit.get("chunks", []),
            }
            item["source_chunks"] = hit.get("chunks", [])
            scored.append(item)

        scored.sort(key=lambda item: item["eligibility_score"], reverse=True)
        return scored[:limit]

    @staticmethod
    def _program_documents(programs: list[dict[str, Any]]) -> list[VectorDocument]:
        documents: list[VectorDocument] = []
        for index, program in enumerate(programs):
            base_metadata = {
                "program_index": index,
                "title": program.get("title"),
                "region": program.get("region"),
                "stage": program.get("stage"),
                "url": program.get("url"),
            }
            overview_text = " ".join(
                [
                    f"지원사업명: {program.get('title', '')}",
                    f"지역: {program.get('region', '')}",
                    f"대상 단계: {program.get('stage', '')}",
                    f"요약: {program.get('summary', '')}",
                    "키워드: " + ", ".join(program.get("keywords", [])),
                ]
            )
            documents.append(
                VectorDocument(
                    id=f"support-program:{index}:overview",
                    text=overview_text,
                    metadata={**base_metadata, "chunk_type": "overview"},
                )
            )
            requirement_text = " ".join(
                [
                    f"지원사업명: {program.get('title', '')}",
                    "필수 서류: " + ", ".join(program.get("documents", [])),
                    f"마감일: {program.get('deadline', '')}",
                    f"출처: {program.get('source_note', '')}",
                ]
            )
            documents.append(
                VectorDocument(
                    id=f"support-program:{index}:requirements",
                    text=requirement_text,
                    metadata={**base_metadata, "chunk_type": "requirements"},
                )
            )
        return documents

    def _vector_hits(
        self,
        *,
        profile: StartupProfile,
        query: str,
        limit: int,
    ) -> dict[int, dict[str, Any]]:
        if not self.vector_store or self.retrieval_mode not in {"vector", "hybrid"}:
            return {}

        query_text = self._retrieval_query(profile, query)
        results = self.vector_store.search(query_text, top_k=max(limit * 4, limit))
        hits: dict[int, dict[str, Any]] = {}
        for result in results:
            program_index = result.document.metadata.get("program_index")
            if program_index is None:
                continue
            index = int(program_index)
            current = hits.setdefault(index, {"similarity": 0.0, "chunks": []})
            current["similarity"] = max(float(current["similarity"]), result.similarity)
            current["chunks"].append(self._chunk_view(result))
        return hits

    def _retrieval_query(self, profile: StartupProfile, query: str) -> str:
        return " ".join(
            [
                query or "",
                profile.region or "",
                profile.startup_stage,
                profile.major or "",
                " ".join(profile.interests),
                " ".join(profile.experiences),
                " ".join(profile.preferred_channels),
                profile.memo or "",
            ]
        )

    def _candidate_indices(self, vector_hits: dict[int, dict[str, Any]]) -> set[int] | None:
        if self.retrieval_mode != "vector":
            return None
        if not vector_hits:
            return set()
        return set(vector_hits)

    def _chunk_view(self, result: VectorSearchResult) -> dict[str, Any]:
        return {
            "document_id": result.document.id,
            "chunk_type": result.document.metadata.get("chunk_type"),
            "title": result.document.metadata.get("title"),
            "similarity": round(result.similarity, 4),
            "text": result.document.text,
            "url": result.document.metadata.get("url"),
        }

    def _terms(self, text: str) -> set[str]:
        normalized = (
            text.replace(",", " ")
            .replace("/", " ")
            .replace("|", " ")
            .replace("·", " ")
            .replace("-", " ")
            .lower()
        )
        terms = {term.strip() for term in normalized.split() if term.strip()}
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
        expanded = set(terms)
        for term in terms:
            for source, targets in aliases.items():
                if source in term:
                    expanded.update(targets)
        return expanded

    def _region_score(self, profile: StartupProfile, program: dict[str, Any]) -> int:
        program_region = program.get("region")
        if not profile.region:
            return 60
        if program_region == profile.region:
            return 100
        if program_region == "전국":
            return 90
        return 20

    def _stage_score(self, profile: StartupProfile, program: dict[str, Any]) -> int:
        stage = program.get("stage", "")
        if not profile.startup_stage:
            return 60
        if profile.startup_stage in stage:
            return 100
        if profile.startup_stage == "예비창업" and "초기창업" in stage:
            return 75
        if profile.startup_stage == "초기창업" and "예비창업" in stage:
            return 75
        return 25

    def _keyword_score(self, matched_terms: list[str], matched_keywords: list[str]) -> int:
        if not matched_terms and not matched_keywords:
            return 25
        return min(100, 35 + len(matched_terms) * 8 + len(matched_keywords) * 12)

    def _query_score(self, query_terms: set[str], program_terms: set[str]) -> int:
        if not query_terms:
            return 60
        return min(100, 35 + len(query_terms & program_terms) * 12)

    def _budget_support_score(self, profile: StartupProfile, program_terms: set[str]) -> int:
        if profile.budget_krw is None:
            return 60
        if profile.budget_krw <= 3_000_000:
            if {"사업화", "시제품", "공간"} & program_terms:
                return 90
            if {"멘토링", "교육", "컨설팅"} & program_terms:
                return 76
            return 70
        return 68

    def _document_readiness_score(self, profile: StartupProfile, program: dict[str, Any]) -> int:
        score = 60
        documents = " ".join(program.get("documents", []))
        if profile.experiences:
            score += 15
        if profile.major:
            score += 10
        if profile.region:
            score += 10
        if "포트폴리오" in documents and not profile.experiences:
            score -= 15
        if "지역" in documents and not profile.region:
            score -= 15
        return max(20, min(100, score))

    def _semantic_score(self, similarity: float) -> int:
        if self.vector_store is None:
            return 60
        # Hash embeddings usually produce smaller cosine ranges than dense
        # semantic models, so map the useful local range into a 0-100 score.
        return max(0, min(100, int(50 + similarity * 180)))

    def _weighted_score(self, score_breakdown: dict[str, int]) -> int:
        weights = {
            "region_fit": 0.18,
            "stage_fit": 0.18,
            "keyword_fit": 0.17,
            "query_fit": 0.06,
            "budget_support_fit": 0.10,
            "document_readiness": 0.11,
            "semantic_similarity": 0.20,
        }
        return max(
            0,
            min(
                100,
                int(sum(score_breakdown[key] * weight for key, weight in weights.items())),
            ),
        )

    def _fit_level(self, score: int) -> str:
        if score >= 85:
            return "high"
        if score >= 65:
            return "medium"
        return "low"

    def _why(
        self,
        profile: StartupProfile,
        program: dict[str, Any],
        matched_keywords: list[str],
        semantic_similarity: float,
    ) -> list[str]:
        reasons: list[str] = []
        if profile.region and program.get("region") in {profile.region, "전국"}:
            reasons.append("지역 조건 적합")
        if profile.startup_stage and profile.startup_stage in program.get("stage", ""):
            reasons.append("창업 단계 적합")
        if matched_keywords:
            reasons.append("관심/경험 키워드 일치: " + ", ".join(matched_keywords))
        if self.vector_store is not None:
            reasons.append(f"벡터 검색 유사도 {semantic_similarity:.2f}")
        if profile.budget_krw is not None and profile.budget_krw <= 3_000_000:
            reasons.append("소자본 창업자의 초기 비용 부담 완화 후보")
        return reasons or ["기본 조건 검토 필요"]

    def _eligibility_gaps(self, profile: StartupProfile, program: dict[str, Any]) -> list[str]:
        gaps: list[str] = []
        region = program.get("region")
        stage = program.get("stage", "")
        documents = " ".join(program.get("documents", []))
        if not profile.region:
            gaps.append("지역 정보를 입력해야 지역 제한 여부를 판단할 수 있습니다.")
        elif region not in {profile.region, "전국"}:
            gaps.append(f"{region} 지역 공고라서 {profile.region} 사용자에게는 부적합할 수 있습니다.")
        if profile.startup_stage and profile.startup_stage not in stage:
            gaps.append(f"공고 단계({stage})와 사용자 단계({profile.startup_stage})가 다를 수 있습니다.")
        if "포트폴리오" in documents and not profile.experiences:
            gaps.append("포트폴리오 또는 활동 증빙을 준비해야 합니다.")
        if "사업계획서" in documents:
            gaps.append("사업계획서 초안이 필요합니다.")
        return gaps

    def _application_strategy(
        self,
        profile: StartupProfile,
        program: dict[str, Any],
        matched_keywords: list[str],
    ) -> list[str]:
        title = program.get("title", "지원사업")
        keywords = matched_keywords or program.get("keywords", [])[:2]
        strategy = [
            f"{title}에는 사용자 경험과 아이템을 '{', '.join(keywords)}' 키워드로 연결해 설명합니다.",
            "사업계획서에는 30일 검증 계획, 예상 고객, 초기 비용 사용처를 먼저 적습니다.",
        ]
        if profile.region and program.get("region") == profile.region:
            strategy.append(f"{profile.region} 활동 근거와 로컬 고객 접점을 강조합니다.")
        if program.get("documents"):
            strategy.append("필수 서류: " + ", ".join(program.get("documents", [])))
        return strategy
