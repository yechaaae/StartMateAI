from __future__ import annotations

from copy import deepcopy
import random
from typing import Any
from uuid import uuid4

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, SimulationStartRequest


class SimulationAgent(BaseAgent):
    name = "SimulationAgent"

    def start(self, request: SimulationStartRequest) -> AgentResponse:
        seed = request.seed if request.seed is not None else random.randint(1, 999_999)
        state = {
            "session_id": str(uuid4()),
            "seed": seed,
            "day": 1,
            "max_day": 30,
            "difficulty": request.difficulty,
            "item_name": request.item_name,
            "business_type": request.business_type,
            "profile": request.profile.model_dump(),
            "metrics": self._initial_metrics(request),
            "history": [],
            "status": "running",
            "current_event": None,
        }
        state["current_event"] = self._event_for_day(state)
        return self._response(state, "30일 창업 시뮬레이션을 시작했습니다. 오늘의 이벤트에 대한 선택지를 골라주세요.")

    def choose(self, state: dict[str, Any], choice_id: str) -> AgentResponse:
        if state.get("status") == "finished":
            return self._response(state, "이미 종료된 시뮬레이션입니다.")

        event = state["current_event"]
        choice = self._find_choice(event, choice_id)
        if choice is None:
            return AgentResponse(
                intent="simulation",
                agent=self.name,
                summary="잘못된 선택지입니다. 현재 이벤트의 choice_id 중 하나를 보내주세요.",
                data={"state": state, "available_choices": event.get("choices", [])},
                warnings=["invalid_choice_id"],
            )

        day_result = self._apply_choice_and_settle_day(state, event, choice)
        state["history"].append(day_result)
        state["day"] += 1

        if state["day"] > state["max_day"]:
            state["status"] = "finished"
            state["current_event"] = None
            state["final_report"] = self._final_report(state)
            return self._response(state, "30일 시뮬레이션이 종료되었습니다. 최종 리포트를 확인하세요.")

        state["current_event"] = self._event_for_day(state)
        return self._response(
            state,
            f"{day_result['day']}일 차 선택 결과가 반영되었습니다. {state['day']}일 차 이벤트를 선택하세요.",
        )

    def _initial_metrics(self, request: SimulationStartRequest) -> dict[str, int]:
        budget = request.profile.budget_krw or 3_000_000
        difficulty_cost = {"easy": 70_000, "normal": 100_000, "hard": 140_000}[request.difficulty]
        return {
            "cash_krw": budget,
            "total_revenue_krw": 0,
            "daily_revenue_krw": 0,
            "inventory_units": 80 if request.business_type in {"cafe", "commerce", "popup"} else 30,
            "reputation": 50,
            "customers": 0,
            "fatigue": 20,
            "risk": 30,
            "marketing_power": 30,
            "daily_fixed_cost_krw": difficulty_cost,
        }

    def _event_for_day(self, state: dict[str, Any]) -> dict[str, Any]:
        day = state["day"]
        scheduled = {
            1: "opening_day",
            7: "first_promotion",
            15: "inventory_check",
            30: "final_push",
        }
        event_key = scheduled.get(day)
        if event_key is None:
            rng = random.Random(f"{state['seed']}:{day}:{state['metrics']['risk']}")
            event_key = rng.choice(
                [
                    "viral_reels",
                    "competitor_discount",
                    "supplier_delay",
                    "storm_warning",
                    "market_hype",
                    "bad_review",
                    "bulk_order",
                    "health_check",
                ]
            )

        event = deepcopy(self._events()[event_key])
        event["day"] = day
        event["event_id"] = f"day-{day}-{event_key}"
        return event

    def _events(self) -> dict[str, dict[str, Any]]:
        return {
            "opening_day": {
                "title": "오픈 첫날, 어디에 집중할까?",
                "story": "첫날부터 모든 걸 완벽하게 하기는 어렵습니다. 제한된 자원을 어디에 쓸지 정해야 합니다.",
                "choices": [
                    self._choice("A", "홍보에 집중", "SNS와 주변 지인에게 오픈 소식을 알린다.", cash=-120_000, marketing=18, fatigue=8),
                    self._choice("B", "품질에 집중", "상품/서비스 완성도를 높인다.", cash=-80_000, reputation=12, fatigue=6),
                    self._choice("C", "작게 테스트", "최소 비용으로 고객 반응만 본다.", cash=-30_000, risk=-8, reputation=3),
                ],
            },
            "first_promotion": {
                "title": "첫 프로모션 타이밍",
                "story": "7일 차가 되자 고객 반응 데이터가 조금 쌓였습니다. 첫 프로모션을 어떻게 운영할까요?",
                "choices": [
                    self._choice("A", "점심 시간 집중 할인", "유입이 많은 시간대에 할인 쿠폰을 뿌린다.", cash=-150_000, customers=18, reputation=6),
                    self._choice("B", "후기 이벤트", "리뷰 작성 고객에게 작은 보상을 준다.", cash=-80_000, reputation=15, marketing=8),
                    self._choice("C", "프로모션 보류", "데이터를 더 모으고 비용을 아낀다.", cash=0, risk=-4, fatigue=-3),
                ],
            },
            "inventory_check": {
                "title": "중간 재고 점검",
                "story": "인기 품목은 빠르게 줄고, 반응이 약한 품목은 남아 있습니다.",
                "choices": [
                    self._choice("A", "인기 품목 추가 발주", "잘 팔리는 품목에 재고를 집중한다.", cash=-300_000, inventory=55, risk=5),
                    self._choice("B", "남은 재고 번들 판매", "묶음 할인으로 현금을 회수한다.", cash=180_000, inventory=-25, reputation=3),
                    self._choice("C", "메뉴/상품 축소", "반응 좋은 것만 남기고 운영을 단순화한다.", risk=-10, fatigue=-8, reputation=4),
                ],
            },
            "final_push": {
                "title": "마지막 30일 차, 최종 승부",
                "story": "30일 실험의 마지막 날입니다. 어떤 결과를 남길지 선택해야 합니다.",
                "choices": [
                    self._choice("A", "대형 홍보전", "마지막 날 유입을 극대화한다.", cash=-250_000, customers=30, marketing=20, fatigue=12),
                    self._choice("B", "단골 확보", "방문 고객에게 다음 예약/재구매 혜택을 준다.", cash=-120_000, reputation=20, risk=-4),
                    self._choice("C", "운영 리포트 정리", "무리하지 않고 데이터를 정리한다.", fatigue=-12, risk=-8, reputation=5),
                ],
            },
            "viral_reels": {
                "title": "릴스가 갑자기 터졌다",
                "story": "짧은 홍보 영상이 예상보다 많이 공유되며 문의가 몰립니다.",
                "choices": [
                    self._choice("A", "바로 물량 확대", "기회를 잡기 위해 공급을 늘린다.", cash=-220_000, inventory=45, customers=24, risk=10, fatigue=10),
                    self._choice("B", "예약제로 전환", "감당 가능한 만큼만 받는다.", reputation=10, risk=-6, customers=10),
                    self._choice("C", "콘텐츠 추가 제작", "바이럴을 이어가기 위해 후속 영상을 만든다.", cash=-90_000, marketing=22, fatigue=7),
                ],
            },
            "competitor_discount": {
                "title": "경쟁 매장이 반값 이벤트를 시작했다",
                "story": "주변 경쟁자가 공격적인 할인으로 고객을 끌어갑니다.",
                "choices": [
                    self._choice("A", "맞불 할인", "가격 경쟁에 대응한다.", cash=-160_000, customers=18, risk=8),
                    self._choice("B", "차별화 메시지 강화", "품질과 스토리를 강조한다.", marketing=12, reputation=9, customers=6),
                    self._choice("C", "단골 고객 집중", "기존 고객에게 혜택을 준다.", cash=-80_000, reputation=14, risk=-3),
                ],
            },
            "supplier_delay": {
                "title": "거래처 배송이 지연됐다",
                "story": "원재료나 상품 입고가 늦어져 오늘 판매량에 영향이 생길 수 있습니다.",
                "choices": [
                    self._choice("A", "비싼 긴급 구매", "다른 거래처에서 급히 확보한다.", cash=-260_000, inventory=35, risk=-4),
                    self._choice("B", "대체 상품 운영", "가능한 상품으로 메뉴/서비스를 바꾼다.", reputation=-2, risk=4, fatigue=5),
                    self._choice("C", "솔직하게 공지", "고객에게 상황을 알리고 예약을 유도한다.", reputation=8, customers=-6, risk=-7),
                ],
            },
            "storm_warning": {
                "title": "폭우 예보가 떴다",
                "story": "자연재해성 악천후로 오프라인 방문 고객이 크게 줄 수 있습니다.",
                "choices": [
                    self._choice("A", "배달/온라인 전환", "오프라인 대신 온라인 주문을 받는다.", cash=-100_000, customers=12, marketing=8),
                    self._choice("B", "운영 시간 단축", "손실을 줄이고 안전을 우선한다.", cash=-20_000, fatigue=-8, risk=-10),
                    self._choice("C", "비 오는 날 이벤트", "날씨를 활용한 한정 혜택을 만든다.", cash=-120_000, customers=16, reputation=7, risk=6),
                ],
            },
            "market_hype": {
                "title": "관련 테마가 시장에서 급부상했다",
                "story": "관련 업종 주가와 뉴스가 급등하며 고객 관심이 갑자기 커졌습니다.",
                "choices": [
                    self._choice("A", "트렌드에 맞춰 메시지 변경", "지금 뜨는 키워드로 홍보 문구를 바꾼다.", marketing=18, customers=14, risk=3),
                    self._choice("B", "가격을 소폭 인상", "높아진 관심을 수익성으로 연결한다.", cash=80_000, reputation=-4, risk=5),
                    self._choice("C", "검증 전까지 유지", "과열된 흐름에 휩쓸리지 않는다.", risk=-8, reputation=4),
                ],
            },
            "bad_review": {
                "title": "첫 악성 리뷰가 올라왔다",
                "story": "작은 실수가 온라인 리뷰로 크게 보이기 시작했습니다.",
                "choices": [
                    self._choice("A", "즉시 보상", "고객에게 사과하고 보상 쿠폰을 제공한다.", cash=-70_000, reputation=10, risk=-8),
                    self._choice("B", "공개 답변", "리뷰에 차분하게 답하고 개선 계획을 밝힌다.", reputation=7, marketing=4, fatigue=3),
                    self._choice("C", "무시", "운영에 집중한다.", reputation=-10, risk=10),
                ],
            },
            "bulk_order": {
                "title": "단체 주문 문의가 들어왔다",
                "story": "큰 주문 기회지만, 무리하면 품질과 운영이 흔들릴 수 있습니다.",
                "choices": [
                    self._choice("A", "전량 수락", "큰 매출을 노린다.", cash=250_000, customers=20, inventory=-35, risk=12, fatigue=12),
                    self._choice("B", "절반만 수락", "가능한 범위에서 안정적으로 처리한다.", cash=120_000, reputation=8, risk=-2),
                    self._choice("C", "다음 일정으로 예약", "품질을 위해 일정을 조정한다.", reputation=5, risk=-6, customers=-3),
                ],
            },
            "health_check": {
                "title": "체력이 바닥나기 시작했다",
                "story": "연속 운영으로 집중력이 떨어지고 실수 가능성이 커졌습니다.",
                "choices": [
                    self._choice("A", "하루 쉬기", "매출 일부를 포기하고 컨디션을 회복한다.", customers=-10, fatigue=-20, risk=-8),
                    self._choice("B", "알바/외주 도움", "비용을 쓰고 운영 부담을 줄인다.", cash=-130_000, fatigue=-12, reputation=4),
                    self._choice("C", "그냥 밀어붙이기", "오늘 매출은 지키지만 피로가 누적된다.", customers=8, fatigue=15, risk=8),
                ],
            },
        }

    def _choice(self, choice_id: str, label: str, description: str, **effects: int) -> dict[str, Any]:
        return {
            "choice_id": choice_id,
            "label": label,
            "description": description,
            "effects_preview": self._preview(effects),
            "effects": effects,
        }

    def _preview(self, effects: dict[str, int]) -> list[str]:
        labels = {
            "cash": "현금",
            "inventory": "재고",
            "reputation": "평판",
            "customers": "고객",
            "fatigue": "피로도",
            "risk": "리스크",
            "marketing": "홍보력",
        }
        preview = []
        for key, value in effects.items():
            sign = "+" if value > 0 else ""
            preview.append(f"{labels.get(key, key)} {sign}{value}")
        return preview

    def _find_choice(self, event: dict[str, Any], choice_id: str) -> dict[str, Any] | None:
        normalized = choice_id.upper()
        for choice in event.get("choices", []):
            if choice["choice_id"].upper() == normalized:
                return choice
        return None

    def _apply_choice_and_settle_day(
        self,
        state: dict[str, Any],
        event: dict[str, Any],
        choice: dict[str, Any],
    ) -> dict[str, Any]:
        metrics = state["metrics"]
        before = deepcopy(metrics)
        effects = choice.get("effects", {})

        metrics["cash_krw"] += effects.get("cash", 0)
        metrics["inventory_units"] += effects.get("inventory", 0)
        metrics["reputation"] += effects.get("reputation", 0)
        metrics["fatigue"] += effects.get("fatigue", 0)
        metrics["risk"] += effects.get("risk", 0)
        metrics["marketing_power"] += effects.get("marketing", 0)

        rng = random.Random(f"{state['seed']}:{state['day']}:settle:{choice['choice_id']}")
        customer_boost = effects.get("customers", 0)
        base_customers = (
            12
            + metrics["reputation"] // 5
            + metrics["marketing_power"] // 6
            - metrics["risk"] // 12
            - metrics["fatigue"] // 15
        )
        customers = max(0, base_customers + customer_boost + rng.randint(-4, 7))
        served = max(0, min(customers, metrics["inventory_units"]))
        unit_price = self._unit_price(state["business_type"])
        revenue = served * unit_price

        metrics["customers"] = served
        metrics["daily_revenue_krw"] = revenue
        metrics["total_revenue_krw"] += revenue
        metrics["cash_krw"] += revenue - metrics["daily_fixed_cost_krw"]
        metrics["inventory_units"] -= served
        metrics["fatigue"] += 4
        metrics["risk"] -= 1

        if metrics["inventory_units"] < 10:
            metrics["risk"] += 6
        if metrics["cash_krw"] < 0:
            metrics["risk"] += 12

        self._clamp_metrics(metrics)

        return {
            "day": state["day"],
            "event_title": event["title"],
            "choice": {
                "choice_id": choice["choice_id"],
                "label": choice["label"],
            },
            "daily_customers": served,
            "daily_revenue_krw": revenue,
            "metrics_before": before,
            "metrics_after": deepcopy(metrics),
            "result_note": self._result_note(metrics, served, revenue),
        }

    def _unit_price(self, business_type: str) -> int:
        return {
            "cafe": 8_000,
            "commerce": 15_000,
            "content": 35_000,
            "popup": 12_000,
            "service": 50_000,
        }[business_type]

    def _clamp_metrics(self, metrics: dict[str, int]) -> None:
        for key in ["reputation", "fatigue", "risk", "marketing_power"]:
            metrics[key] = max(0, min(100, metrics[key]))
        metrics["inventory_units"] = max(0, metrics["inventory_units"])

    def _result_note(self, metrics: dict[str, int], customers: int, revenue: int) -> str:
        if metrics["cash_krw"] < 0:
            return "현금이 마이너스입니다. 다음 선택에서는 비용 절감이나 매출 회복이 필요합니다."
        if metrics["fatigue"] >= 80:
            return "피로도가 높습니다. 무리하면 운영 리스크가 커집니다."
        if metrics["risk"] >= 75:
            return "리스크가 높습니다. 안정적인 선택이 필요합니다."
        if customers >= 35:
            return "고객 반응이 좋습니다. 재고와 품질 관리가 다음 관건입니다."
        if revenue == 0:
            return "오늘 매출이 거의 없습니다. 홍보나 고객 접점을 다시 설계해야 합니다."
        return "선택 결과가 반영되었습니다. 다음 이벤트에서 균형을 맞춰야 합니다."

    def _final_report(self, state: dict[str, Any]) -> dict[str, Any]:
        metrics = state["metrics"]
        score = int(
            metrics["cash_krw"] / 50_000
            + metrics["total_revenue_krw"] / 35_000
            + metrics["reputation"] * 1.8
            + metrics["marketing_power"]
            - metrics["risk"] * 1.2
            - metrics["fatigue"]
        )
        if score >= 220:
            grade = "A"
            message = "30일 검증 성공입니다. 확장 전략을 검토할 수 있습니다."
        elif score >= 140:
            grade = "B"
            message = "가능성은 확인됐지만 비용/운영 리스크를 더 줄여야 합니다."
        else:
            grade = "C"
            message = "아이템 자체보다 실행 조건을 다시 설계해야 합니다."
        return {
            "score": max(score, 0),
            "grade": grade,
            "message": message,
            "total_revenue_krw": metrics["total_revenue_krw"],
            "ending_cash_krw": metrics["cash_krw"],
            "reputation": metrics["reputation"],
            "risk": metrics["risk"],
            "fatigue": metrics["fatigue"],
        }

    def _response(self, state: dict[str, Any], summary: str) -> AgentResponse:
        state_view = deepcopy(state)
        next_actions = []
        if state["status"] == "running":
            next_actions = [
                f"{choice['choice_id']}: {choice['label']}"
                for choice in state["current_event"].get("choices", [])
            ]
        else:
            next_actions = ["최종 리포트 기반으로 아이템 유지/수정/중단 여부 결정"]
        metrics = deepcopy(state["metrics"])
        final_report = state.get("final_report")
        risks = self._state_risks(metrics)
        score = self._state_score(metrics, final_report)
        data = self.agent_data(
            position="30일 동안 선택 결과를 누적해 창업 아이템의 생존 가능성을 검증합니다.",
            evidence={
                "day": state["day"],
                "metrics": metrics,
                "current_event": state.get("current_event", {}).get("title") if state.get("current_event") else None,
                "final_report": final_report,
            },
            score=score,
            risks=risks,
            assumptions=[
                "선택지 효과와 랜덤 이벤트는 룰 엔진으로 계산합니다.",
                "LLM은 현재 시뮬레이션 점수 계산에 관여하지 않습니다.",
            ],
            missing_inputs=[],
            recommendation=self._simulation_recommendation(state, risks),
            payload={
                "session_id": state["session_id"],
                "day": state["day"],
                "status": state["status"],
                "state": state_view,
                "current_event": state.get("current_event"),
                "metrics": metrics,
                "history_tail": state["history"][-3:],
                "final_report": final_report,
            },
        )

        return AgentResponse(
            intent="simulation",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=next_actions,
        )

    def _state_risks(self, metrics: dict[str, int]) -> list[str]:
        risks = []
        if metrics["cash_krw"] < 0:
            risks.append("현금 부족")
        if metrics["inventory_units"] < 10:
            risks.append("재고 부족")
        if metrics["fatigue"] >= 75:
            risks.append("피로도 과다")
        if metrics["risk"] >= 70:
            risks.append("운영 리스크 높음")
        if metrics["reputation"] <= 35:
            risks.append("평판 저하")
        return risks

    def _state_score(self, metrics: dict[str, int], final_report: dict[str, Any] | None) -> int:
        if final_report:
            return max(0, min(100, int(final_report["score"] / 3)))
        raw_score = (
            metrics["cash_krw"] / 80_000
            + metrics["total_revenue_krw"] / 60_000
            + metrics["reputation"]
            + metrics["marketing_power"] * 0.5
            - metrics["risk"] * 0.7
            - metrics["fatigue"] * 0.4
        )
        return max(0, min(100, int(raw_score)))

    def _simulation_recommendation(self, state: dict[str, Any], risks: list[str]) -> str:
        if state["status"] == "finished":
            report = state.get("final_report", {})
            return report.get("message", "최종 리포트를 기준으로 다음 전략을 결정하세요.")
        if "현금 부족" in risks:
            return "다음 선택에서는 비용 지출을 줄이고 현금 회복을 우선하세요."
        if "피로도 과다" in risks:
            return "휴식, 외주, 운영 단순화 선택지를 우선 고려하세요."
        if "재고 부족" in risks:
            return "수요가 유지된다면 재고 보충 또는 예약제로 전환하세요."
        return "다음 이벤트에서 매출, 평판, 리스크 균형을 맞추는 선택을 하세요."
