from __future__ import annotations

import re
from typing import Any

from app.agents.base import BaseAgent
from app.core.backend_tools import BackendToolClient
from app.schemas import AgentResponse, CommercialAreaRequest, Source


REGION_HINTS: dict[str, tuple[str, str | None]] = {
    "구미": ("경북", "구미시"),
    "김천": ("경북", "김천시"),
    "경산": ("경북", "경산시"),
    "포항": ("경북", "포항시"),
    "대구": ("대구", None),
    "서울": ("서울", None),
    "마포": ("서울", "마포구"),
    "홍대": ("서울", "마포구"),
    "연남": ("서울", "마포구"),
    "강남": ("서울", "강남구"),
    "성수": ("서울", "성동구"),
    "부산": ("부산", None),
    "대전": ("대전", None),
    "광주": ("광주", None),
    "인천": ("인천", None),
}

SIDO_ALIASES: dict[str, str] = {
    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",
    "경기도": "경기",
    "강원특별자치도": "강원",
    "충청북도": "충북",
    "충청남도": "충남",
    "전북특별자치도": "전북",
    "전라북도": "전북",
    "전라남도": "전남",
    "경상북도": "경북",
    "경상남도": "경남",
    "제주특별자치도": "제주",
}


class CommercialAreaAgent(BaseAgent):
    name = "CommercialAreaAgent"

    def __init__(self, llm, backend_tools: BackendToolClient | None = None):
        super().__init__(llm)
        self.backend_tools = backend_tools

    async def run(self, request: CommercialAreaRequest) -> AgentResponse:
        payload = self._analyze_payload(request)
        area = self._reference_area(request.context, payload)
        rent = self._reference_rent(request.context)
        rent_payload = self._rent_payload(request, payload)
        tool_calls: list[dict[str, Any]] = []
        tool_warnings: list[str] = []

        if not area and self.backend_tools:
            area, tool_calls, tool_warnings = await self._fetch_backend_area(payload)
        if not rent and self.backend_tools:
            rent, rent_tool_calls, rent_warnings = await self._fetch_backend_rent(rent_payload)
            tool_calls.extend(rent_tool_calls)
            tool_warnings.extend(rent_warnings)

        if not area:
            missing_inputs = self._missing_inputs(payload)
            data = self.agent_data(
                position="상권 분석에 필요한 백엔드 데이터가 연결되지 않아 경쟁점 수를 확정하지 않았습니다.",
                evidence={"requested_payload": payload, "tool_warnings": tool_warnings},
                score=0,
                risks=[
                    *tool_warnings,
                    "상가 CSV/import 데이터가 없으면 실제 경쟁점 판단이 제한됩니다.",
                ],
                assumptions=["AI가 임의로 점포 수를 추정하지 않고, 확인된 백엔드 결과만 사용합니다."],
                missing_inputs=missing_inputs,
                recommendation="상가 CSV를 먼저 적재하거나 지역/업종을 더 구체화한 뒤 다시 분석하세요.",
                payload={
                    "reference_data_used": False,
                    "reference_sources": [],
                    "tool_calls": tool_calls,
                    "commercial_area": None,
                    "rent_estimate": rent or None,
                    "requested_payload": payload,
                    "rent_payload": rent_payload,
                },
            )
            return AgentResponse(
                intent="commercial_area",
                agent=self.name,
                summary=self._missing_summary(missing_inputs, payload),
                data=data,
                next_actions=[
                    "상가 API 권한과 CSV 데이터 적재 상태 확인",
                    "시/군/구, 동, 업종 대분류/중분류를 구체화",
                    "같은 지역의 임대료, 유동인구, 객단가 데이터를 추가 확인",
                ],
                warnings=data["risks"],
            )

        metrics = self._metrics(area)
        rent_metrics = self._rent_metrics(rent)
        score = self._score(metrics["competition_level"], metrics["total_stores"])
        risk_factors = self._risk_factors(metrics, area)
        risk_factors.extend(self._rent_risks(rent_metrics))
        risk_factors = list(dict.fromkeys(risk_factors))
        opportunities = self._opportunities(metrics)
        recommendation = self._recommendation(metrics)
        data = self.agent_data(
            position=self._position(metrics),
            evidence={
                "area_label": metrics["area_label"],
                "industry_label": metrics["industry_label"],
                "total_stores": metrics["total_stores"],
                "direct_competitors": metrics["direct_competitors"],
                "similar_competitors": metrics["similar_competitors"],
                "competition_level": metrics["competition_level"],
                "rent_estimate": rent_metrics,
            },
            score=score,
            risks=risk_factors,
            assumptions=[
                "백엔드 상가 CSV/import 데이터 기준의 단순 경쟁도 분석입니다.",
                "유동인구, 매출, 임대료, 배달 수요는 별도 데이터가 연결되기 전까지 직접 확인이 필요합니다.",
            ],
            missing_inputs=[],
            recommendation=recommendation,
            payload={
                "reference_data_used": True,
                "reference_sources": ["backend.tool.commercial_area"] if tool_calls else ["backend.commercial_area"],
                "tool_calls": tool_calls,
                "commercial_area": area,
                "rent_estimate": rent or None,
                "requested_payload": payload,
                "rent_payload": rent_payload,
                "area": metrics["area_label"],
                "industry": metrics["industry_label"],
                "total_stores": metrics["total_stores"],
                "direct_competitors": metrics["direct_competitors"],
                "similar_competitors": metrics["similar_competitors"],
                "competition_level": metrics["competition_level"],
                "estimated_monthly_rent": rent_metrics.get("estimated_monthly_rent"),
                "rent_per_m2_thousand": rent_metrics.get("rent_per_m2_thousand"),
                "rent_match_level": rent_metrics.get("match_level"),
                "risk_factors": risk_factors,
                "opportunities": opportunities,
                "entry_strategy": self._entry_strategy(metrics, rent_metrics),
                "additional_checks": self._additional_checks(metrics, rent_metrics),
            },
        )

        return AgentResponse(
            intent="commercial_area",
            agent=self.name,
            summary=self._summary(metrics, rent_metrics, recommendation, risk_factors, opportunities),
            data=data,
            next_actions=[
                "직접 경쟁점 상호, 메뉴, 가격대, 리뷰 키워드 확인",
                "후보지 2~3곳의 임대료와 평일/주말 유동인구 비교",
                "경쟁점과 다른 대표 메뉴, 운영 시간, 주문 방식 1개씩 정해 테스트",
            ],
            sources=[Source(title="백엔드 상권 분석 결과", note="backend.commercial_area")],
            warnings=risk_factors,
        )

    def _reference_area(self, context: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        area = (
            context.get("reference", {})
            .get("externalData", {})
            .get("commercialArea")
        )
        if isinstance(area, dict) and self._area_matches_payload(area, payload):
            return area
        direct = context.get("commercialArea") or context.get("commercial_area")
        return direct if isinstance(direct, dict) and self._area_matches_payload(direct, payload) else {}

    def _area_matches_payload(self, area: dict[str, Any], payload: dict[str, Any] | None) -> bool:
        if not payload:
            return True
        area_label = str(area.get("areaLabel") or area.get("area") or "")
        industry_label = str(area.get("industryLabel") or area.get("industry") or "")
        expected_area_parts = [
            str(payload.get(key)).strip()
            for key in ("sido", "sigungu", "dong")
            if payload.get(key)
        ]
        if area_label and any(part not in area_label for part in expected_area_parts):
            return False
        if not area_label and expected_area_parts:
            return False

        expected_industry_parts = [
            str(payload.get(key)).strip()
            for key in ("industryLarge", "industryMedium", "industrySmall")
            if payload.get(key)
        ]
        if expected_industry_parts:
            if not industry_label or industry_label == "선택 업종":
                return False
            if not any(part in industry_label for part in expected_industry_parts):
                return False
        return True

    def _reference_rent(self, context: dict[str, Any]) -> dict[str, Any]:
        rent = (
            context.get("reference", {})
            .get("externalData", {})
            .get("rentEstimate")
        )
        if isinstance(rent, dict):
            return rent
        direct = context.get("rentEstimate") or context.get("rent_estimate")
        return direct if isinstance(direct, dict) else {}

    async def _fetch_backend_area(
        self,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        if not self.backend_tools:
            return {}, [], []
        try:
            area = await self.backend_tools.analyze_commercial_area(payload)
            return area, [{"name": "commercial_areas.analyze", "status": "success", "payload": payload}], []
        except Exception as error:  # noqa: BLE001
            return {}, [
                {
                    "name": "commercial_areas.analyze",
                    "status": "failed",
                    "payload": payload,
                    "error": error.__class__.__name__,
                }
            ], [f"백엔드 상권 도구 호출 실패: {str(error)[:160]}"]

    async def _fetch_backend_rent(
        self,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
        if not self.backend_tools:
            return {}, [], []
        try:
            rent = await self.backend_tools.estimate_commercial_rent(payload)
            return rent, [{"name": "commercial_areas.rent_estimate", "status": "success", "payload": payload}], []
        except Exception as error:  # noqa: BLE001
            return {}, [
                {
                    "name": "commercial_areas.rent_estimate",
                    "status": "failed",
                    "payload": payload,
                    "error": error.__class__.__name__,
                }
            ], [f"백엔드 임대료 도구 호출 실패: {str(error)[:160]}"]

    def _analyze_payload(self, request: CommercialAreaRequest) -> dict[str, Any]:
        context = request.context or {}
        query = request.query or ""
        region_text = " ".join(
            str(value)
            for value in [
                context.get("area"),
                context.get("region"),
                context.get("location"),
                request.profile.region,
                query,
            ]
            if value
        )
        industry_text = " ".join(
            str(value)
            for value in [
                context.get("industry"),
                context.get("industry_label"),
                context.get("business_type"),
                context.get("item_name"),
                context.get("product_name"),
                " ".join(request.profile.interests),
                query,
            ]
            if value
        )
        inferred_region = self._infer_region(region_text)
        inferred_industry = self._infer_industry(industry_text)
        return {
            "sido": self._first_text(context, "sido", "시도") or inferred_region["sido"],
            "sigungu": self._first_text(context, "sigungu", "시군구") or inferred_region["sigungu"],
            "dong": self._first_text(context, "dong", "행정동", "법정동") or inferred_region["dong"],
            "latitude": self._number(context.get("latitude")),
            "longitude": self._number(context.get("longitude")),
            "radiusMeters": self._integer(context.get("radiusMeters") or context.get("radius_meters")),
            "industryLarge": self._first_text(context, "industryLarge", "industry_large") or inferred_industry["large"],
            "industryMedium": self._first_text(context, "industryMedium", "industry_medium") or inferred_industry["medium"],
            "industrySmall": self._first_text(context, "industrySmall", "industry_small") or inferred_industry["small"],
        }

    def _rent_payload(self, request: CommercialAreaRequest, area_payload: dict[str, Any]) -> dict[str, Any]:
        context = request.context or {}
        return {
            "sido": area_payload.get("sido"),
            "sigungu": area_payload.get("sigungu"),
            "dong": area_payload.get("dong"),
            "address": self._first_text(context, "address", "road_address", "jibun_address"),
            "areaM2": self._number(context.get("areaM2") or context.get("area_m2") or context.get("area")),
            "commercialType": self._first_text(context, "commercialType", "commercial_type"),
        }

    def _infer_region(self, raw: str) -> dict[str, str | None]:
        text = raw or ""
        result: dict[str, str | None] = {"sido": None, "sigungu": None, "dong": None}
        for alias, normalized in SIDO_ALIASES.items():
            if alias in text:
                result["sido"] = normalized
                break
        for hint, (sido, sigungu) in REGION_HINTS.items():
            if hint in text:
                result["sido"] = result["sido"] or sido
                result["sigungu"] = result["sigungu"] or sigungu
        sigungu_match = re.search(r"([가-힣]{2,12}(?:시|군|구))", text)
        if sigungu_match:
            result["sigungu"] = sigungu_match.group(1)
        dong_match = re.search(r"([가-힣0-9]{1,12}(?:동|읍|면|리))", text)
        if dong_match:
            result["dong"] = dong_match.group(1)
        if "인동" in text and not result["dong"]:
            result["dong"] = "인동동"
        if "연남" in text and not result["dong"]:
            result["dong"] = "연남동"
        if "성수" in text and not result["dong"]:
            result["dong"] = "성수동"
        return result

    def _infer_industry(self, raw: str) -> dict[str, str | None]:
        text = raw or ""
        if self._contains_any(text, ["카페", "커피", "음료", "디저트", "쿠키", "베이커리", "제과"]):
            if self._contains_any(text, ["디저트", "쿠키", "베이커리", "제과", "빵"]):
                return {"large": "음식", "medium": "제과", "small": "제과"}
            return {"large": "음식", "medium": None, "small": "카페"}
        if self._contains_any(text, ["한식", "백반", "국밥", "식당", "요식", "음식점"]):
            return {"large": "음식", "medium": "한식", "small": None}
        if self._contains_any(text, ["분식", "떡볶이", "김밥"]):
            return {"large": "음식", "medium": "분식", "small": None}
        if self._contains_any(text, ["술집", "주점", "호프", "맥주"]):
            return {"large": "음식", "medium": "주점", "small": None}
        if self._contains_any(text, ["미용", "네일", "헤어"]):
            return {"large": "서비스", "medium": "미용", "small": None}
        if self._contains_any(text, ["소매", "편집샵", "잡화", "의류"]):
            return {"large": "소매", "medium": None, "small": None}
        return {"large": None, "medium": None, "small": None}

    def _metrics(self, area: dict[str, Any]) -> dict[str, Any]:
        return {
            "area_label": str(area.get("areaLabel") or area.get("area") or "선택 지역"),
            "industry_label": str(area.get("industryLabel") or area.get("industry") or "선택 업종"),
            "total_stores": self._integer(area.get("totalStores")) or 0,
            "direct_competitors": self._integer(area.get("directCompetitors")) or 0,
            "similar_competitors": self._integer(area.get("similarCompetitors")) or 0,
            "competition_level": str(area.get("competitionLevel") or "unknown"),
            "notes": [str(note) for note in area.get("notes", []) if note] if isinstance(area.get("notes"), list) else [],
        }

    def _rent_metrics(self, rent: dict[str, Any]) -> dict[str, Any]:
        if not rent:
            return {
                "available": False,
                "estimated_monthly_rent": None,
                "rent_per_m2_thousand": None,
                "area_m2": None,
                "match_level": None,
                "source": None,
            }
        return {
            "available": True,
            "sido": rent.get("sido"),
            "region_depth2": rent.get("regionDepth2"),
            "region_depth3": rent.get("regionDepth3"),
            "commercial_type": rent.get("commercialType"),
            "base_year": self._integer(rent.get("baseYear")),
            "base_quarter": self._integer(rent.get("baseQuarter")),
            "rent_per_m2_thousand": self._number(rent.get("rentPerM2Thousand")),
            "area_m2": self._number(rent.get("areaM2")),
            "estimated_monthly_rent": self._integer(rent.get("estimatedMonthlyRent")),
            "match_level": rent.get("matchLevel"),
            "source": rent.get("source"),
        }

    def _position(self, metrics: dict[str, Any]) -> str:
        return (
            f"{metrics['area_label']}의 {metrics['industry_label']} 직접 경쟁점은 "
            f"{metrics['direct_competitors']}개이고 경쟁 강도는 {self._level_label(metrics['competition_level'])}입니다."
        )

    def _summary(
        self,
        metrics: dict[str, Any],
        rent_metrics: dict[str, Any],
        recommendation: str,
        risks: list[str],
        opportunities: list[str],
    ) -> str:
        risk_lines = "\n".join(f"- {risk}" for risk in risks[:4])
        opportunity_lines = "\n".join(f"- {item}" for item in opportunities[:3])
        rent_section = self._rent_summary(rent_metrics)
        return (
            f"상권 분석 결과\n\n"
            f"지역: {metrics['area_label']}\n"
            f"업종: {metrics['industry_label']}\n"
            f"전체 점포: {metrics['total_stores']}개\n"
            f"직접 경쟁점: {metrics['direct_competitors']}개\n"
            f"유사 경쟁점: {metrics['similar_competitors']}개\n"
            f"경쟁 강도: {self._level_label(metrics['competition_level'])} ({metrics['competition_level']})\n\n"
            f"{rent_section}\n\n"
            f"판단:\n{recommendation}\n\n"
            f"주의할 점:\n{risk_lines}\n\n"
            f"기회/실행 방향:\n{opportunity_lines}"
        )

    def _rent_summary(self, rent_metrics: dict[str, Any]) -> str:
        if not rent_metrics.get("available"):
            return "임대료 추정: 연결된 임대료 기준 데이터가 없어 확인하지 못했습니다."
        rent = rent_metrics.get("estimated_monthly_rent")
        rent_text = f"{rent:,}원/월" if isinstance(rent, int) else "-"
        rent_per_m2 = rent_metrics.get("rent_per_m2_thousand")
        rent_per_m2_text = f"{rent_per_m2:,.2f}천원/㎡" if isinstance(rent_per_m2, (int, float)) else "-"
        area = rent_metrics.get("area_m2")
        area_text = f"{area:g}㎡" if isinstance(area, (int, float)) else "-"
        period = ""
        if rent_metrics.get("base_year") and rent_metrics.get("base_quarter"):
            period = f" ({rent_metrics['base_year']}년 {rent_metrics['base_quarter']}분기 기준)"
        return (
            "임대료 추정:\n"
            f"- 예상 월 임대료: {rent_text}\n"
            f"- 기준 면적: {area_text}\n"
            f"- ㎡당 임대료: {rent_per_m2_text}{period}\n"
            f"- 매칭 수준: {rent_metrics.get('match_level') or '-'}"
        )

    def _missing_summary(self, missing_inputs: list[str], payload: dict[str, Any]) -> str:
        missing = ", ".join(missing_inputs) if missing_inputs else "백엔드 상권 데이터"
        return (
            "상권 reference 데이터가 없어 경쟁점 수를 판단하지 않았습니다.\n\n"
            f"부족한 정보: {missing}\n"
            f"요청 payload: {payload}\n\n"
            "상가 CSV를 적재한 뒤 지역과 업종을 구체화해서 다시 분석하세요."
        )

    def _risk_factors(self, metrics: dict[str, Any], area: dict[str, Any]) -> list[str]:
        risks = list(metrics["notes"])
        if metrics["total_stores"] == 0:
            risks.append("해당 지역의 점포 수가 0으로 계산되어 CSV 미적재 또는 지역명 불일치 가능성이 있습니다.")
        if metrics["competition_level"] == "high":
            risks.append("직접 경쟁점이 많아 동일 메뉴/가격으로 진입하면 차별화가 어렵습니다.")
        elif metrics["competition_level"] == "medium":
            risks.append("경쟁점이 일정 수준 있어 메뉴, 가격, 운영 시간 차별화 검증이 필요합니다.")
        else:
            risks.append("경쟁점 수만으로 입지 매력을 판단하기 어렵고 유동인구/임대료 확인이 필요합니다.")
        if metrics["similar_competitors"] > metrics["direct_competitors"]:
            risks.append("유사 업종이 많아 고객 지출을 나눠 가질 가능성이 있습니다.")
        return list(dict.fromkeys(risks))

    def _rent_risks(self, rent_metrics: dict[str, Any]) -> list[str]:
        if not rent_metrics.get("available"):
            return ["임대료 기준 데이터가 연결되지 않아 월세 부담을 확정하지 못했습니다."]
        risks: list[str] = []
        rent = rent_metrics.get("estimated_monthly_rent")
        if isinstance(rent, int):
            if rent >= 2_000_000:
                risks.append("예상 월 임대료가 높아 초기 매출이 흔들리면 손익분기점이 빠르게 올라갈 수 있습니다.")
            elif rent >= 1_000_000:
                risks.append("예상 월 임대료가 중간 이상이라 30일 테스트 후 고정 매장 계약을 검토하는 편이 안전합니다.")
            else:
                risks.append("예상 월 임대료는 비교적 낮지만 보증금, 관리비, 권리금은 별도 확인이 필요합니다.")
        match_level = str(rent_metrics.get("match_level") or "")
        if match_level in {"NATIONAL_AVERAGE", "SIDO_AVERAGE"}:
            risks.append("임대료 매칭이 세부 상권 평균이 아닐 수 있어 실제 매물 월세와 차이가 날 수 있습니다.")
        return risks

    def _opportunities(self, metrics: dict[str, Any]) -> list[str]:
        if metrics["competition_level"] == "high":
            return [
                "대표 메뉴, 가격대, 운영 시간 중 최소 1개는 주변 경쟁점과 다르게 설계",
                "기존 경쟁점 리뷰의 불만 키워드를 모아 차별화 포인트로 사용",
                "정식 매장보다 팝업/예약 판매로 수요를 먼저 검증",
            ]
        if metrics["competition_level"] == "medium":
            return [
                "경쟁점이 증명한 수요를 활용하되 메뉴와 구매 동선을 좁게 테스트",
                "점심/퇴근/주말 중 비어 있는 시간대를 찾아 운영",
                "리뷰 이벤트와 재방문 쿠폰으로 초기 단골을 확보",
            ]
        return [
            "경쟁 밀도가 낮다면 수요 자체가 충분한지 먼저 검증",
            "소규모 팝업 또는 배달/예약 판매로 반응 확인",
            "주변 집객 시설과 제휴하거나 SNS 지역 키워드로 유입 확보",
        ]

    def _entry_strategy(self, metrics: dict[str, Any], rent_metrics: dict[str, Any]) -> list[str]:
        if metrics["total_stores"] == 0:
            return ["CSV 데이터와 지역명 매칭을 먼저 확인", "현장 조사로 실제 경쟁점 5곳 이상 직접 기록"]
        rent = rent_metrics.get("estimated_monthly_rent")
        rent_check = (
            f"예상 월세 {rent:,}원을 FinanceAgent에 넣어 손익분기점을 재계산"
            if isinstance(rent, int)
            else "후보 매물 월세를 확보해 FinanceAgent로 손익분기점을 재계산"
        )
        return [
            "직접 경쟁점 5곳의 가격, 대표 메뉴, 리뷰 불만을 표로 정리",
            "경쟁점보다 좁은 타깃과 대표 상품 1개로 첫 테스트 설계",
            rent_check,
        ]

    def _additional_checks(self, metrics: dict[str, Any], rent_metrics: dict[str, Any]) -> list[str]:
        checks = ["임대료", "평일/주말 유동인구", "주차/접근성", "경쟁점 리뷰 키워드", "시간대별 수요"]
        if metrics["competition_level"] == "high":
            checks.append("경쟁점과 겹치지 않는 대표 메뉴")
        if rent_metrics.get("available"):
            checks.extend(["보증금", "관리비", "권리금", "계약 기간"])
        return checks

    def _recommendation(self, metrics: dict[str, Any]) -> str:
        direct = metrics["direct_competitors"]
        if metrics["total_stores"] == 0:
            return "현재 결과만으로는 진입 판단을 하지 말고, CSV 적재/지역명 매칭과 현장 경쟁점 수를 먼저 확인하세요."
        if metrics["competition_level"] == "low":
            return f"직접 경쟁점이 {direct}개라 경쟁만 보면 진입 여지는 있지만, 수요 부족 가능성도 함께 확인해야 합니다."
        if metrics["competition_level"] == "medium":
            return f"직접 경쟁점이 {direct}개라 수요는 확인되지만, 메뉴/가격/운영 시간 차별화가 필요합니다."
        if metrics["competition_level"] == "high":
            return f"직접 경쟁점이 {direct}개로 높아 동일 콘셉트 진입은 신중해야 하며, 팝업/예약 판매로 먼저 검증하세요."
        return "경쟁 강도를 해석하기 어려우므로 지역과 업종 조건을 더 구체화해 다시 분석하세요."

    def _score(self, competition_level: str, total_stores: int) -> int:
        if total_stores == 0:
            return 20
        if competition_level == "low":
            return 72
        if competition_level == "medium":
            return 58
        if competition_level == "high":
            return 38
        return 45

    def _missing_inputs(self, payload: dict[str, Any]) -> list[str]:
        missing = []
        if not payload.get("sido") and not payload.get("sigungu") and not payload.get("dong"):
            missing.append("지역")
        if not payload.get("industryLarge") and not payload.get("industryMedium") and not payload.get("industrySmall"):
            missing.append("업종")
        return missing

    def _level_label(self, level: str) -> str:
        return {"low": "낮음", "medium": "보통", "high": "높음"}.get(level, level or "unknown")

    def _first_text(self, values: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = values.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return None

    def _number(self, value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
        return float(match.group(0)) if match else None

    def _integer(self, value: Any) -> int | None:
        number = self._number(value)
        return int(number) if number is not None else None

    def _contains_any(self, raw: str, keywords: list[str]) -> bool:
        return any(keyword in raw for keyword in keywords)
