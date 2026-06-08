from __future__ import annotations

from statistics import mean

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, OperationRequest


class OperationAgent(BaseAgent):
    name = "OperationAgent"

    async def run(self, request: OperationRequest) -> AgentResponse:
        sales = request.weekly_sales_krw or [0]
        avg_sales = int(mean(sales))
        trend = "flat"
        if len(sales) >= 2 and sales[-1] > sales[0]:
            trend = "up"
        elif len(sales) >= 2 and sales[-1] < sales[0]:
            trend = "down"

        risks = []
        actions = []
        if trend == "down":
            risks.append("최근 매출 하락")
            actions.append("고객 유입 채널별 전환율 확인")
        if any("부족" in note or "품절" in note for note in request.inventory_notes):
            risks.append("인기 품목 재고 부족")
            actions.append("인기 품목 안전재고 기준 설정")
        if any("비싸" in note or "가격" in note for note in request.customer_feedback):
            risks.append("가격 민감도")
            actions.append("세트 구성 또는 시간대 할인 테스트")

        actions.extend(
            [
                "다음 주 핵심 지표를 매출, 재고, 리뷰 3개로 제한해 추적",
                "주간 운영 리포트를 저장하고 다음 추천에 반영",
            ]
        )

        data = {
            "business_name": request.business_name,
            "average_weekly_sales_krw": avg_sales,
            "sales_trend": trend,
            "risks": risks or ["입력 데이터 기준 주요 위험 신호 없음"],
            "recommended_actions": actions,
            "next_week_plan": [
                "월요일: 재고와 원가 점검",
                "수요일: 고객 피드백 반영 프로모션 실행",
                "금요일: 매출 구간별 리뷰와 다음 주 개선안 확정",
            ],
        }
        fallback = "운영 데이터를 바탕으로 위험 신호와 다음 주 실행 계획을 정리했습니다."
        summary = await self.polish_summary(task="operation feedback", data=data, fallback=fallback)

        return AgentResponse(
            intent="operation",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=actions[:4],
        )
