from __future__ import annotations

from app.agents.base import BaseAgent
from app.rag.retriever import SupportProgramRetriever
from app.schemas import AgentResponse, PolicyRequest, Source


class PolicyAgent(BaseAgent):
    name = "PolicyAgent"

    def __init__(self, llm, retriever: SupportProgramRetriever):
        super().__init__(llm)
        self.retriever = retriever

    async def run(self, request: PolicyRequest) -> AgentResponse:
        matches = self.retriever.search(
            profile=request.profile,
            query=request.query or "",
            limit=request.limit,
        )
        top = matches[0] if matches else None
        documents = self._documents_to_prepare(matches)
        match_summary = self._match_summary(matches)
        checklist = [
            "사업자 등록 여부 확인",
            "나이/지역/창업단계 자격 확인",
            "사업계획서와 개인정보 동의서 준비",
            "마감일 기준 3일 전 제출 목표 설정",
        ]
        risks = ["현재 데이터는 샘플입니다. 실제 최신 공고 RAG 인덱스로 교체해야 합니다."]
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
            assumptions=["지원사업 데이터는 샘플 JSON 기준입니다.", "마감일과 자격 요건은 실제 공고에서 재확인해야 합니다."],
            missing_inputs=missing_inputs,
            recommendation=recommendation,
            payload={
                "matches": matches,
                "checklist": checklist,
                "top_policy": top,
                "match_summary": match_summary,
                "documents_to_prepare": documents,
                "application_strategy": top.get("application_strategy", []) if top else [],
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
