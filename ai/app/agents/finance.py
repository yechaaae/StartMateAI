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

        data = {
            "item_name": a.item_name,
            "monthly_revenue_krw": monthly_revenue,
            "monthly_variable_cost_krw": variable_cost,
            "monthly_fixed_cost_krw": fixed_cost,
            "monthly_profit_krw": monthly_profit,
            "break_even_units_per_month": bep_units,
            "break_even_units_per_day": ceil(bep_units / a.operating_days_per_month),
            "initial_cash_needed_krw": initial_cash_needed,
            "payback_months": payback_months,
            "risk_grade": self._risk_grade(monthly_profit, initial_cash_needed),
            "thirty_day_timeline": [
                {"day": 1, "task": "오픈 준비와 필수 비용 확정"},
                {"day": 7, "task": "첫 프로모션 진행과 고객 반응 기록"},
                {"day": 15, "task": "재고/원가 조정"},
                {"day": 30, "task": "매출, 비용, 리뷰 기반 운영 리포트 작성"},
            ],
        }
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
