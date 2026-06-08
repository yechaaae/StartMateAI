from __future__ import annotations

from math import ceil

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, FinanceRequest


class FinanceAgent(BaseAgent):
    name = "FinanceAgent"

    async def run(self, request: FinanceRequest) -> AgentResponse:
        a = request.assumption
        monthly_revenue = a.price_per_unit_krw * a.expected_daily_customers * a.operating_days_per_month
        variable_cost = int(monthly_revenue * a.variable_cost_rate)
        fixed_cost = a.rent_krw_per_month + a.marketing_krw_per_month + a.other_fixed_cost_krw_per_month
        monthly_profit = monthly_revenue - variable_cost - fixed_cost
        contribution_margin = max(a.price_per_unit_krw * (1 - a.variable_cost_rate), 1)
        bep_units = ceil(fixed_cost / contribution_margin)
        initial_cash_needed = a.equipment_krw + a.initial_inventory_krw + fixed_cost
        payback_months = None if monthly_profit <= 0 else round(initial_cash_needed / monthly_profit, 1)
        risk_grade = self._risk_grade(monthly_profit, initial_cash_needed)
        risks = []
        if monthly_profit <= 0:
            risks.append("월 예상 이익이 0 이하입니다.")
        if initial_cash_needed > (request.profile.budget_krw or initial_cash_needed):
            risks.append("초기 필요 현금이 현재 예산보다 큽니다.")
        if ceil(fixed_cost / max(a.price_per_unit_krw * (1 - a.variable_cost_rate), 1)) / a.operating_days_per_month > 30:
            risks.append("일 손익분기 판매량이 높습니다.")
        what_if_scenarios = self._what_if_scenarios(a, fixed_cost)

        score = {"A": 88, "B": 68, "C": 40}[risk_grade]
        data = self.agent_data(
            position="고정비와 손익분기 판매량이 핵심 검증 포인트입니다.",
            evidence={
                "monthly_profit_krw": monthly_profit,
                "break_even_units_per_day": ceil(bep_units / a.operating_days_per_month),
                "initial_cash_needed_krw": initial_cash_needed,
                "risk_grade": risk_grade,
            },
            score=score,
            risks=risks,
            assumptions=[
                f"객단가 {a.price_per_unit_krw:,}원",
                f"예상 일 방문 고객 {a.expected_daily_customers}명",
                f"변동비율 {a.variable_cost_rate:.0%}",
                f"월 운영일 {a.operating_days_per_month}일",
            ],
            missing_inputs=["실제 임대료", "실제 상권 유동인구", "원가율"] if request.profile.region is None else ["실제 임대료", "원가율"],
            recommendation="손익분기 판매량을 낮추는 방향으로 임대료, 객단가, 원가율을 재검토하세요.",
            payload={
                "item_name": a.item_name,
                "monthly_revenue_krw": monthly_revenue,
                "monthly_variable_cost_krw": variable_cost,
                "monthly_fixed_cost_krw": fixed_cost,
                "monthly_profit_krw": monthly_profit,
                "break_even_units_per_month": bep_units,
                "break_even_units_per_day": ceil(bep_units / a.operating_days_per_month),
                "initial_cash_needed_krw": initial_cash_needed,
                "payback_months": payback_months,
                "risk_grade": risk_grade,
                "what_if_scenarios": what_if_scenarios,
                "thirty_day_timeline": [
                    {"day": 1, "task": "오픈 준비와 필수 비용 확정"},
                    {"day": 7, "task": "첫 프로모션 진행과 고객 반응 기록"},
                    {"day": 15, "task": "재고/원가 조정"},
                    {"day": 30, "task": "매출, 비용, 리뷰 기반 운영 리포트 작성"},
                ],
            },
        )
        fallback = "예상 매출, 비용, 손익분기점과 30일 실행 일정을 계산했습니다."
        summary = await self.polish_summary(task="financial simulation", data=data, fallback=fallback)

        return AgentResponse(
            intent="finance",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "임대료와 일 방문 고객 수를 실제 상권 데이터로 보정",
                "고정비를 낮추는 무점포/팝업 대안 비교",
                "지원사업 매칭으로 초기 현금 부담 완화",
            ],
        )

    def _risk_grade(self, monthly_profit: int, initial_cash_needed: int) -> str:
        if monthly_profit <= 0:
            return "C"
        if initial_cash_needed / monthly_profit > 8:
            return "B"
        return "A"

    def _what_if_scenarios(self, assumption, fixed_cost: int) -> list[dict[str, int | str]]:
        lower_rent_fixed_cost = max(0, fixed_cost - 500_000)
        higher_price = int(assumption.price_per_unit_krw * 1.1)
        lower_customers = max(1, int(assumption.expected_daily_customers * 0.8))
        return [
            {
                "scenario": "임대료 50만 원 절감",
                "monthly_fixed_cost_krw": lower_rent_fixed_cost,
                "note": "고정비 절감은 손익분기점을 직접 낮춥니다.",
            },
            {
                "scenario": "객단가 10% 상승",
                "price_per_unit_krw": higher_price,
                "note": "가격 인상은 평판 리스크와 함께 검토해야 합니다.",
            },
            {
                "scenario": "고객 수 20% 감소",
                "expected_daily_customers": lower_customers,
                "note": "보수적 매출 시나리오에서 현금 여유가 충분한지 확인해야 합니다.",
            },
        ]
