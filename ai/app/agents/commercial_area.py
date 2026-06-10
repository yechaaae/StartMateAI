from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, CommercialAreaRequest, Source


class CommercialAreaAgent(BaseAgent):
    name = "CommercialAreaAgent"

    async def run(self, request: CommercialAreaRequest) -> AgentResponse:
        area = self._reference_area(request.context)
        reference_data_used = bool(area)

        if not area:
            data = self.agent_data(
                position="상권 데이터가 아직 연결되지 않아 경쟁점 수를 확정하기 어렵습니다.",
                evidence="backend.commercial_area reference missing",
                score=0,
                risks=["상권 CSV/import 데이터가 없으면 실제 경쟁점 판단이 제한됩니다."],
                assumptions=["AI가 임의로 점포 수를 추정하지 않습니다."],
                missing_inputs=["지역", "업종"],
                recommendation="백엔드에서 상권 CSV를 import한 뒤 같은 질문을 다시 확인하세요.",
                payload={
                    "reference_data_used": False,
                    "reference_sources": [],
                    "commercial_area": None,
                },
            )
            return AgentResponse(
                intent="commercial_area",
                agent=self.name,
                summary="상권 reference 데이터가 없어 경쟁점 수를 판단하지 않았습니다.",
                data=data,
                next_actions=["상가 CSV 데이터를 먼저 적재", "희망 지역과 업종을 구체화"],
                warnings=data["risks"],
            )

        direct_competitors = int(area.get("directCompetitors") or 0)
        competition_level = str(area.get("competitionLevel") or "unknown")
        area_label = str(area.get("areaLabel") or "선택 지역")
        industry_label = str(area.get("industryLabel") or "선택 업종")
        notes = [str(note) for note in area.get("notes", []) if note]

        position = (
            f"{area_label}의 {industry_label} 직접 경쟁점은 {direct_competitors}개이며 "
            f"경쟁 강도는 {competition_level}로 봅니다."
        )
        recommendation = self._recommendation(competition_level, direct_competitors)
        risks = notes or ["임대료, 유동인구, 매출 데이터는 별도 확인이 필요합니다."]
        data = self.agent_data(
            position=position,
            evidence=area,
            score=self._score(competition_level),
            risks=risks,
            assumptions=["백엔드 상권 CSV/import 데이터 기준의 단순 경쟁도입니다."],
            missing_inputs=[],
            recommendation=recommendation,
            payload={
                "reference_data_used": reference_data_used,
                "reference_sources": ["backend.commercial_area"],
                "commercial_area": area,
            },
        )
        summary = await self.polish_summary(
            task="commercial area competition analysis",
            data=data,
            fallback=f"{area_label} 기준 직접 경쟁점 {direct_competitors}개, 경쟁 강도 {competition_level}입니다.",
        )

        return AgentResponse(
            intent="commercial_area",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "직접 경쟁점 상호와 메뉴/가격대 확인",
                "임대료와 유동인구 데이터를 추가로 확인",
                "오픈 전 차별화 포인트 1개를 정해 검증",
            ],
            sources=[Source(title="백엔드 상권 분석 결과", note="backend.commercial_area")],
            warnings=risks,
        )

    def _reference_area(self, context: dict[str, Any]) -> dict[str, Any]:
        area = (
            context.get("reference", {})
            .get("externalData", {})
            .get("commercialArea")
        )
        return area if isinstance(area, dict) else {}

    def _score(self, competition_level: str) -> int:
        if competition_level == "low":
            return 78
        if competition_level == "medium":
            return 55
        if competition_level == "high":
            return 35
        return 0

    def _recommendation(self, competition_level: str, direct_competitors: int) -> str:
        if competition_level == "low":
            return "경쟁점 수만 보면 진입 여지는 있지만, 임대료와 유동인구를 같이 확인하세요."
        if competition_level == "medium":
            return "차별화 메뉴, 가격대, 방문 동선을 먼저 검증한 뒤 입지를 결정하세요."
        if competition_level == "high":
            return f"직접 경쟁점이 {direct_competitors}개라 동일 콘셉트 진입은 신중히 검토하세요."
        return "지역과 업종을 더 구체화한 뒤 다시 분석하세요."
