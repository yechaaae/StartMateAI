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
        data = {
            "matches": matches,
            "checklist": [
                "사업자 등록 여부 확인",
                "나이/지역/창업단계 자격 확인",
                "사업계획서와 개인정보 동의서 준비",
                "마감일 기준 3일 전 제출 목표 설정",
            ],
        }
        fallback = f"사용자 조건에 맞는 지원사업 후보 {len(matches)}개를 찾았습니다."
        summary = await self.polish_summary(task="support program matching", data=data, fallback=fallback)

        sources = [
            Source(title=item["title"], url=item.get("url"), note=item.get("source_note"))
            for item in matches
        ]
        warnings = ["현재 데이터는 샘플입니다. 실제 서비스에서는 최신 공고 RAG 인덱스로 교체해야 합니다."]

        return AgentResponse(
            intent="policy",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "최신 공고 데이터 수집/색인",
                "상위 1개 공고 기준 사업계획서 초안 생성",
                "마감일 알림 등록",
            ],
            sources=sources,
            warnings=warnings,
        )
