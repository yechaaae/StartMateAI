from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.core.backend_tools import BackendToolClient
from app.rag.retriever import SupportProgramRetriever
from app.schemas import AgentResponse, PolicyRequest, Source


class PolicyAgent(BaseAgent):
    name = "PolicyAgent"

    def __init__(self, llm, retriever: SupportProgramRetriever, backend_tools: BackendToolClient | None = None):
        super().__init__(llm)
        self.retriever = retriever
        self.backend_tools = backend_tools

    async def run(self, request: PolicyRequest) -> AgentResponse:
        reference_matches = self._reference_matches(request)
        tool_calls: list[dict[str, Any]] = []
        tool_warnings: list[str] = []
        tool_matches: list[dict[str, Any]] = []
        should_refresh = self._should_refresh(request)

        if self.backend_tools and (should_refresh or not reference_matches):
            tool_matches, tool_calls, tool_warnings = await self._fetch_backend_tool_matches(request)

        matches = tool_matches or reference_matches or self.retriever.search(
            profile=request.profile,
            query=request.query or "",
            limit=request.limit,
        )
        using_reference_data = bool(tool_matches or reference_matches)
        reference_sources = []
        if tool_matches:
            reference_sources.append("backend.tool.support_programs")
        elif reference_matches:
            reference_sources.append("backend.support_programs")

        top = matches[0] if matches else None
        documents = self._documents_to_prepare(matches)
        match_summary = self._match_summary(matches)
        checklist = [
            "사업자 등록 여부 확인",
            "나이/지역/창업단계 자격 확인",
            "사업계획서와 개인정보 동의서 준비",
            "마감일 기준 3일 전 제출 목표 설정",
        ]
        risks = list(tool_warnings)
        if not using_reference_data:
            risks.append("현재 데이터는 샘플입니다. 실제 최신 공고 RAG 인덱스로 교체해야 합니다.")
        if top and top.get("eligibility_gaps"):
            risks.extend(top["eligibility_gaps"][:2])
        missing_inputs = []
        if not request.profile.region:
            missing_inputs.append("지역")
        if not request.profile.startup_stage:
            missing_inputs.append("창업 단계")
        if not request.profile.interests:
            missing_inputs.append("관심 분야")

        position = (
            f"지원사업은 {top['title']}을 1순위로 검토하는 것이 좋습니다."
            if top
            else "현재 조건만으로는 확실한 지원사업 후보를 좁히기 어렵습니다."
        )
        recommendation = (
            f"{top['title']} 기준으로 자격 공백을 확인하고 사업계획서 초안을 준비하세요."
            if top
            else "지역, 단계, 관심 분야를 보강한 뒤 최신 공고 RAG로 다시 매칭하세요."
        )
        data = self.agent_data(
            position=position,
            evidence=self._policy_evidence(top),
            score=int(top.get("eligibility_score", 0)) if top else 0,
            risks=risks,
            assumptions=[
                "백엔드 정규화 추천 결과를 우선 사용했습니다." if using_reference_data else "지원사업 데이터는 샘플 JSON 기준입니다.",
                "마감일과 자격 요건은 실제 공고에서 재확인해야 합니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation=recommendation,
            payload={
                "matches": matches,
                "checklist": checklist,
                "top_policy": top,
                "match_summary": match_summary,
                "documents_to_prepare": documents,
                "application_strategy": top.get("application_strategy", []) if top else [],
                "reference_data_used": using_reference_data,
                "reference_sources": reference_sources,
                "tool_calls": tool_calls,
                "coverage": {
                    "total_matches": len(matches),
                    "high_fit_count": sum(1 for item in matches if item.get("fit_level") == "high"),
                    "medium_or_better_count": sum(
                        1 for item in matches if item.get("fit_level") in {"high", "medium"}
                    ),
                },
            },
        )
        fallback = f"사용자 조건에 맞는 지원사업 후보 {len(matches)}개를 찾았습니다."
        summary = await self.polish_summary(task="support program matching", data=data, fallback=fallback)

        sources = [
            Source(title=item["title"], url=item.get("url"), note=item.get("source_note"))
            for item in matches
        ]
        warnings = risks

        return AgentResponse(
            intent="policy",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "상위 1개 공고의 실제 모집요강 확인",
                "사업계획서에 30일 검증 계획과 예산 사용처 작성",
                "필수 서류와 마감일 체크리스트 등록",
            ],
            sources=sources,
            warnings=warnings,
        )

    def _reference_matches(self, request: PolicyRequest) -> list[dict]:
        support_programs = (
            request.context.get("reference", {})
            .get("externalData", {})
            .get("supportPrograms", {})
        )
        items = support_programs.get("items", [])
        if not isinstance(items, list) or not items:
            return []
        return [self._reference_item_to_match(item) for item in items[: request.limit] if isinstance(item, dict)]

    def _reference_item_to_match(self, item: dict) -> dict:
        return self._backend_item_to_match(item, source_note=item.get("source") or "backend.support_programs")

    def _backend_item_to_match(self, item: dict, *, source_note: str) -> dict:
        score = int(item.get("matchScore") or 0)
        caution_reasons = item.get("cautionReasons") or []
        match_reasons = item.get("matchReasons") or []
        return {
            "id": item.get("programId"),
            "title": item.get("title") or "지원사업 후보",
            "url": item.get("applyUrl"),
            "summary": item.get("summary"),
            "source_note": source_note,
            "eligibility_score": score,
            "fit_level": self._fit_level(score),
            "score_breakdown": {"backend_match_score": score},
            "matched_keywords": [],
            "why_matched": match_reasons,
            "eligibility_gaps": caution_reasons,
            "required_documents": [],
            "application_strategy": [
                "백엔드 추천 점수와 주의사항을 기준으로 실제 공고 원문을 확인하세요.",
                "마감일과 신청 URL을 먼저 확인한 뒤 제출 서류를 정리하세요.",
            ],
            "retrieval": {"source": "backend_reference"},
            "source_chunks": [item.get("summary")] if item.get("summary") else [],
        }

    async def _fetch_backend_tool_matches(
        self,
        request: PolicyRequest,
    ) -> tuple[list[dict], list[dict[str, Any]], list[str]]:
        if not self.backend_tools:
            return [], [], []

        tool_calls: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            if self._should_refresh(request):
                await self.backend_tools.sync_support_programs("all")
                tool_calls.append({"name": "support_programs.sync", "status": "success"})

            items = await self.backend_tools.recommend_support_programs(self._recommend_payload(request))
            tool_calls.append({"name": "support_programs.recommend", "status": "success", "count": len(items)})
            matches = [
                self._backend_item_to_match(item, source_note="backend.tool.support_programs")
                for item in items[: request.limit]
                if isinstance(item, dict)
            ]
            return matches, tool_calls, warnings
        except Exception as error:  # noqa: BLE001
            tool_calls.append({
                "name": "support_programs.tool",
                "status": "failed",
                "error": error.__class__.__name__,
            })
            warnings.append(f"백엔드 지원사업 도구 호출 실패: {str(error)[:160]}")
            return [], tool_calls, warnings

    def _recommend_payload(self, request: PolicyRequest) -> dict[str, Any]:
        query = request.query or ""
        region = request.profile.region or query
        industry_text = " ".join([*request.profile.interests, query])
        return {
            "age": request.profile.age or self._age_from(query) or 27,
            "residenceSido": self._sido_from(request.profile.region),
            "desiredSido": self._sido_from(region),
            "desiredSigungu": self._sigungu_from(region),
            "founderType": "pre_founder",
            "businessRegistered": False,
            "businessStartDate": None,
            "businessStage": self._business_stage(request.profile.startup_stage),
            "industryLarge": self._industry_large(industry_text),
            "industryMedium": self._industry_medium(industry_text),
            "industrySmall": self._industry_small(industry_text),
            "requiredFundingAmount": request.profile.budget_krw,
            "interestedSupportTypes": ["grant", "education", "mentoring", "space"],
        }

    def _should_refresh(self, request: PolicyRequest) -> bool:
        text = (request.query or "").lower()
        return any(keyword in text for keyword in ["최신", "새 공고", "새로운", "지금", "현재", "모집중", "모집 중"])

    def _business_stage(self, value: str | None) -> str:
        text = value or ""
        if "초기" in text:
            return "mvp"
        if "매출" in text:
            return "revenue"
        return "idea"

    def _industry_large(self, raw: str) -> str | None:
        return "음식점업" if self._contains_any(raw, ["카페", "커피", "음식", "식당", "디저트"]) else None

    def _industry_medium(self, raw: str) -> str | None:
        return "커피점/카페" if self._contains_any(raw, ["카페", "커피"]) else None

    def _industry_small(self, raw: str) -> str | None:
        return "카페" if self._contains_any(raw, ["카페", "커피"]) else None

    def _sido_from(self, raw: str | None) -> str | None:
        text = raw or ""
        for sido in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]:
            if sido in text:
                return sido
        return None

    def _sigungu_from(self, raw: str | None) -> str | None:
        text = raw or ""
        if "마포" in text:
            return "마포구"
        for token in text.replace(",", " ").split():
            if token.endswith(("구", "군")):
                return token
        return None

    def _age_from(self, raw: str) -> int | None:
        for token in raw.replace(",", " ").split():
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                age = int(digits)
                if 19 <= age <= 80:
                    return age
        return None

    def _contains_any(self, raw: str, keywords: list[str]) -> bool:
        return any(keyword in raw for keyword in keywords)

    def _fit_level(self, score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    def _policy_evidence(self, top: dict | None) -> dict | str:
        if not top:
            return "매칭 후보 없음"
        return {
            "title": top.get("title"),
            "eligibility_score": top.get("eligibility_score"),
            "fit_level": top.get("fit_level"),
            "score_breakdown": top.get("score_breakdown", {}),
            "retrieval": top.get("retrieval", {}),
            "source_chunks": top.get("source_chunks", []),
            "why_matched": top.get("why_matched", []),
            "eligibility_gaps": top.get("eligibility_gaps", []),
        }

    def _match_summary(self, matches: list[dict]) -> list[dict[str, object]]:
        return [
            {
                "title": item.get("title"),
                "eligibility_score": item.get("eligibility_score"),
                "fit_level": item.get("fit_level"),
                "matched_keywords": item.get("matched_keywords", []),
                "semantic_similarity": item.get("retrieval", {}).get("semantic_similarity"),
                "why_matched": item.get("why_matched", []),
                "eligibility_gaps": item.get("eligibility_gaps", []),
            }
            for item in matches
        ]

    def _documents_to_prepare(self, matches: list[dict]) -> list[str]:
        documents: list[str] = []
        seen = set()
        for item in matches[:3]:
            for document in item.get("required_documents", item.get("documents", [])):
                if document not in seen:
                    seen.add(document)
                    documents.append(document)
        return documents
