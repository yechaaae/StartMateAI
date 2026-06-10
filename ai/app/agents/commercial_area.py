from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.core.backend_tools import BackendToolClient
from app.schemas import AgentResponse, CommercialAreaRequest, Source


class CommercialAreaAgent(BaseAgent):
    name = "CommercialAreaAgent"

    def __init__(self, llm, backend_tools: BackendToolClient | None = None):
        super().__init__(llm)
        self.backend_tools = backend_tools

    async def run(self, request: CommercialAreaRequest) -> AgentResponse:
        area = self._reference_area(request.context)
        tool_calls: list[dict[str, Any]] = []
        tool_warnings: list[str] = []
        if not area and self.backend_tools:
            area, tool_calls, tool_warnings = await self._fetch_backend_area(request)
        reference_data_used = bool(area)

        if not area:
            data = self.agent_data(
                position="상권 데이터가 아직 연결되지 않아 경쟁점 수를 확정하기 어렵습니다.",
                evidence="backend.commercial_area reference missing",
                score=0,
                risks=[*tool_warnings, "상권 CSV/import 데이터가 없으면 실제 경쟁점 판단이 제한됩니다."],
                assumptions=["AI가 임의로 점포 수를 추정하지 않습니다."],
                missing_inputs=["지역", "업종"],
                recommendation="백엔드에서 상권 CSV를 import한 뒤 같은 질문을 다시 확인하세요.",
                payload={
                    "reference_data_used": False,
                    "reference_sources": [],
                    "tool_calls": tool_calls,
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
                "reference_sources": ["backend.tool.commercial_area"] if tool_calls else ["backend.commercial_area"],
                "tool_calls": tool_calls,
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

    async def _fetch_backend_area(
        self,
        request: CommercialAreaRequest,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        if not self.backend_tools:
            return {}, [], []
        try:
            area = await self.backend_tools.analyze_commercial_area(self._analyze_payload(request))
            return area, [{"name": "commercial_areas.analyze", "status": "success"}], []
        except Exception as error:  # noqa: BLE001
            return {}, [
                {
                    "name": "commercial_areas.analyze",
                    "status": "failed",
                    "error": error.__class__.__name__,
                }
            ], [f"백엔드 상권 도구 호출 실패: {str(error)[:160]}"]

    def _analyze_payload(self, request: CommercialAreaRequest) -> dict[str, Any]:
        query = request.query or ""
        region = request.profile.region or query
        industry_text = " ".join([*request.profile.interests, query])
        return {
            "sido": self._sido_from(region) or "서울",
            "sigungu": self._sigungu_from(region),
            "dong": self._dong_from(region),
            "latitude": None,
            "longitude": None,
            "radiusMeters": None,
            "industryLarge": self._industry_large(industry_text),
            "industryMedium": self._industry_medium(industry_text),
            "industrySmall": self._industry_small(industry_text),
        }

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

    def _sido_from(self, raw: str) -> str | None:
        for sido in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]:
            if sido in raw:
                return sido
        return None

    def _sigungu_from(self, raw: str) -> str | None:
        if "마포" in raw:
            return "마포구"
        for token in raw.replace(",", " ").split():
            if token.endswith(("구", "군")):
                return token
        return None

    def _dong_from(self, raw: str) -> str | None:
        if "연남" in raw:
            return "연남동"
        for token in raw.replace(",", " ").split():
            if token.endswith(("동", "읍", "면")):
                return token
        return None

    def _industry_large(self, raw: str) -> str | None:
        return "음식점업" if self._contains_any(raw, ["카페", "커피", "음식", "식당", "디저트"]) else None

    def _industry_medium(self, raw: str) -> str | None:
        return "커피점/카페" if self._contains_any(raw, ["카페", "커피"]) else None

    def _industry_small(self, raw: str) -> str | None:
        return "카페" if self._contains_any(raw, ["카페", "커피"]) else None

    def _contains_any(self, raw: str, keywords: list[str]) -> bool:
        return any(keyword in raw for keyword in keywords)
