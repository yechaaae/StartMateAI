from __future__ import annotations

from statistics import mean
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, OperationMetric, OperationRequest


class OperationAgent(BaseAgent):
    name = "OperationAgent"

    async def run(self, request: OperationRequest) -> AgentResponse:
        missing_inputs = self._missing_inputs(request)
        if self._needs_data_request(request, missing_inputs):
            return await self._data_request_response(request, missing_inputs)

        sales_series = self._sales_series(request)
        sales_analysis = self._sales_analysis(sales_series, request)
        order_analysis = self._order_analysis(request, sales_analysis)
        cost_analysis = self._cost_analysis(request, sales_analysis)
        marketing_efficiency = self._marketing_efficiency(request, order_analysis)
        inventory_analysis = self._inventory_analysis(request)
        customer_analysis = self._customer_feedback_analysis(request)
        product_mix = self._product_mix(request)

        risk_items = self._risk_items(
            sales_analysis=sales_analysis,
            order_analysis=order_analysis,
            cost_analysis=cost_analysis,
            marketing_efficiency=marketing_efficiency,
            inventory_analysis=inventory_analysis,
            customer_analysis=customer_analysis,
            product_mix=product_mix,
        )
        detected_risks = [item["risk"] for item in risk_items] or ["입력 데이터 기준 주요 위험 신호 없음"]
        root_causes = self._root_causes(risk_items)
        recommended_actions = self._recommended_actions(risk_items, request)
        next_week_plan = self._next_week_plan(recommended_actions)
        confidence = self._confidence(missing_inputs)
        score = self._score(risk_items, missing_inputs)
        handoff = self._handoff(risk_items)

        data = self.agent_data(
            position="운영 데이터는 매출, 주문, 비용, 재고, 고객 반응을 분리해서 봐야 개선 우선순위가 명확해집니다.",
            evidence={
                "sales_trend": sales_analysis["trend"],
                "average_sales_krw": sales_analysis["average_sales_krw"],
                "average_order_value_krw": order_analysis.get("average_order_value_krw"),
                "ad_cost_per_order_krw": marketing_efficiency.get("ad_cost_per_order_krw"),
                "detected_risks": detected_risks,
            },
            score=score,
            risks=detected_risks,
            assumptions=self._assumptions(request, confidence),
            missing_inputs=missing_inputs,
            recommendation=self._recommendation(risk_items, confidence),
            payload={
                "business_name": request.business_name,
                "period": request.period,
                "operation_score": score,
                "confidence": confidence,
                "kpi_summary": self._kpi_summary(
                    sales_analysis,
                    order_analysis,
                    cost_analysis,
                    marketing_efficiency,
                    inventory_analysis,
                    customer_analysis,
                ),
                "sales_analysis": sales_analysis,
                "order_analysis": order_analysis,
                "cost_analysis": cost_analysis,
                "inventory_analysis": inventory_analysis,
                "customer_feedback_analysis": customer_analysis,
                "marketing_efficiency": marketing_efficiency,
                "product_mix": product_mix,
                "detected_risks": detected_risks,
                "risk_items": risk_items,
                "root_causes": root_causes,
                "recommended_actions": recommended_actions,
                "next_week_plan": next_week_plan,
                "support_handoff": handoff,
                "data_limitations": self._data_limitations(missing_inputs, request),
                "average_weekly_sales_krw": sales_analysis["average_sales_krw"],
                "sales_trend": sales_analysis["trend"],
            },
        )

        fallback = self._summary_fallback(data)
        summary = await self.polish_summary(
            task="operation feedback",
            data=data,
            fallback=fallback,
            instructions=(
                "Write in Korean. Include the concrete evidence numbers or facts from the input "
                "(sales, orders, ad spend, inventory notes, customer feedback). "
                "Do not only state the conclusion. Explain why the top risk was selected and include one next action."
            ),
        )

        return AgentResponse(
            intent="operation",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=recommended_actions[:4],
            warnings=data["data_limitations"],
        )

    async def _data_request_response(self, request: OperationRequest, missing_inputs: list[str]) -> AgentResponse:
        questions = [
            "최근 1주 또는 이번 달 매출은 얼마였나요?",
            "주문 수와 평균 객단가는 어느 정도였나요?",
            "재고 부족/남는 상품, 고객 불만이나 리뷰 키워드가 있었나요?",
        ]
        actions = [
            "최근 1주 매출과 주문 수 입력",
            "품절/재고 과다 상품 메모",
            "고객 리뷰나 불만 키워드 3개 입력",
        ]
        data = self.agent_data(
            position="운영 피드백은 실제 운영 데이터가 있어야 의미 있게 판단할 수 있습니다.",
            evidence={
                "received_data": self._received_data_flags(request),
                "missing_inputs": missing_inputs,
            },
            score=0,
            risks=[],
            assumptions=["현재 요청에는 운영 판단에 필요한 정량/정성 데이터가 거의 없습니다."],
            missing_inputs=missing_inputs,
            recommendation="매출, 주문 수, 재고 메모, 고객 피드백 중 최소 2~3개를 알려주시면 운영 리스크와 다음 주 액션을 분석할 수 있습니다.",
            payload={
                "business_name": request.business_name,
                "period": request.period,
                "needs_more_data": True,
                "operation_score": None,
                "confidence": "insufficient_data",
                "questions": questions,
                "data_limitations": [f"누락 데이터: {', '.join(missing_inputs)}"],
                "recommended_actions": actions,
                "next_week_plan": [],
                "detected_risks": [],
            },
        )
        fallback = (
            "지금은 운영 데이터가 부족해서 점수를 매기기보다 먼저 확인이 필요합니다. "
            "최근 매출, 주문 수, 재고 이슈, 고객 피드백을 알려주시면 다음 주 개선 액션까지 정리해드릴게요."
        )
        summary = await self.polish_summary(
            task="operation data request",
            data=data,
            fallback=fallback,
            instructions="운영 점수를 단정하지 말고, 필요한 입력을 자연스럽게 질문하세요.",
        )
        return AgentResponse(
            intent="operation",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=actions,
            warnings=data["data_limitations"],
        )

    def _sales_series(self, request: OperationRequest) -> list[int]:
        if request.daily_sales_krw:
            return [value for value in request.daily_sales_krw if value >= 0]
        if request.weekly_sales_krw:
            return [value for value in request.weekly_sales_krw if value >= 0]
        if request.monthly_sales_krw is not None:
            return [request.monthly_sales_krw]
        metric_sales = self._metric_value(request.metrics, "매출", "sales", "revenue")
        return [int(metric_sales)] if metric_sales is not None else []

    def _sales_analysis(self, sales: list[int], request: OperationRequest) -> dict[str, Any]:
        if not sales:
            return {
                "trend": "unknown",
                "average_sales_krw": 0,
                "latest_sales_krw": None,
                "change_rate": None,
                "series_count": 0,
                "basis": "매출 데이터가 없어 추세를 계산하지 않았습니다.",
            }

        avg_sales = int(mean(sales))
        latest = sales[-1]
        change_rate = None
        trend = "flat"
        if len(sales) >= 2 and sales[0] > 0:
            change_rate = (sales[-1] - sales[0]) / sales[0]
            if change_rate >= 0.10:
                trend = "up"
            elif change_rate <= -0.10:
                trend = "down"
        elif len(sales) >= 2:
            trend = "up" if sales[-1] > sales[0] else "flat"

        return {
            "trend": trend,
            "average_sales_krw": avg_sales,
            "latest_sales_krw": latest,
            "change_rate": self._round_rate(change_rate),
            "series_count": len(sales),
            "basis": "일별 매출" if request.daily_sales_krw else "주간 매출" if request.weekly_sales_krw else "월 매출",
        }

    def _order_analysis(self, request: OperationRequest, sales_analysis: dict[str, Any]) -> dict[str, Any]:
        orders = request.orders
        if orders is None:
            metric_orders = self._metric_value(request.metrics, "주문", "order")
            orders = int(metric_orders) if metric_orders is not None else None

        sales = request.monthly_sales_krw or sales_analysis["latest_sales_krw"] or sales_analysis["average_sales_krw"]
        average_order_value = int(sales / orders) if orders and sales else None
        return {
            "orders": orders,
            "average_order_value_krw": average_order_value,
            "basis": "주문 수 입력 기준" if orders is not None else "주문 수 미입력",
        }

    def _cost_analysis(self, request: OperationRequest, sales_analysis: dict[str, Any]) -> dict[str, Any]:
        sales = request.monthly_sales_krw or sales_analysis["latest_sales_krw"] or sales_analysis["average_sales_krw"]
        costs = {
            "ad_spend_krw": request.ad_spend_krw or 0,
            "material_cost_krw": request.material_cost_krw or 0,
            "labor_cost_krw": request.labor_cost_krw or 0,
            "fixed_cost_krw": request.fixed_cost_krw or 0,
        }
        total_cost = sum(costs.values())
        cost_rate = total_cost / sales if sales else None
        return {
            **costs,
            "known_total_cost_krw": total_cost,
            "known_cost_rate": self._round_rate(cost_rate),
            "estimated_margin_krw": sales - total_cost if sales and total_cost else None,
            "basis": "입력된 비용 항목만 반영했습니다.",
        }

    def _marketing_efficiency(self, request: OperationRequest, order_analysis: dict[str, Any]) -> dict[str, Any]:
        impressions = request.impressions
        clicks = request.clicks
        orders = order_analysis.get("orders")
        click_rate = clicks / impressions if impressions and clicks is not None else None
        conversion_rate = request.conversion_rate
        if conversion_rate is None and clicks and orders is not None:
            conversion_rate = orders / clicks
        ad_cost_per_order = int(request.ad_spend_krw / orders) if request.ad_spend_krw and orders else None
        return {
            "impressions": impressions,
            "clicks": clicks,
            "click_rate": self._round_rate(click_rate),
            "conversion_rate": self._round_rate(conversion_rate),
            "ad_cost_per_order_krw": ad_cost_per_order,
            "channel_notes": request.channel_notes,
        }

    def _inventory_analysis(self, request: OperationRequest) -> dict[str, Any]:
        notes = [*request.inventory_notes, request.notes or ""]
        stockouts = list(request.stockout_items)
        slow_moving = list(request.slow_moving_items)
        for note in notes:
            normalized = note.lower()
            if any(keyword in normalized for keyword in ["부족", "품절", "재고 없음", "완판", "stockout", "shortage", "sold out"]):
                stockouts.append(note)
            if any(keyword in normalized for keyword in ["남음", "과잉", "안 팔", "재고 많", "leftover", "slow moving", "overstock"]):
                slow_moving.append(note)
        return {
            "stockout_items": self._unique(stockouts),
            "slow_moving_items": self._unique(slow_moving),
            "notes": request.inventory_notes,
            "status": "risk" if stockouts or slow_moving else "ok" if request.inventory_notes else "unknown",
        }

    def _customer_feedback_analysis(self, request: OperationRequest) -> dict[str, Any]:
        texts = [*request.customer_feedback, *request.review_keywords, *request.complaints, request.notes or ""]
        categories = {
            "price": ["비싸", "가격", "가성비", "할인", "expensive", "price", "discount"],
            "quality": ["맛", "품질", "상태", "불량", "위생", "quality", "taste", "hygiene"],
            "waiting": ["대기", "느려", "지연", "줄", "wait", "delay", "slow"],
            "service": ["불친절", "응대", "문의", "환불", "교환", "service", "refund", "exchange"],
            "repeat": ["재구매", "또", "단골", "추천", "repeat", "again", "recommend"],
        }
        hits = {
            category: self._unique([text for text in texts if any(keyword in text.lower() for keyword in keywords)])
            for category, keywords in categories.items()
        }
        sentiment = "positive" if hits["repeat"] and not any(hits[key] for key in ["price", "quality", "waiting", "service"]) else "mixed"
        if any(hits[key] for key in ["price", "quality", "waiting", "service"]):
            sentiment = "negative_signal"
        return {
            "sentiment": sentiment if any(texts) else "unknown",
            "categories": hits,
            "raw_feedback_count": len([text for text in texts if text]),
        }

    def _product_mix(self, request: OperationRequest) -> dict[str, Any]:
        products = [item for item in request.product_sales if isinstance(item, dict)]
        if not products:
            return {"products": [], "top_product": None, "concentration_rate": None, "status": "unknown"}

        normalized = []
        total = 0
        for item in products:
            name = str(item.get("name") or item.get("title") or item.get("product") or "상품")
            sales = self._to_number(item.get("sales_krw") or item.get("sales") or item.get("revenue") or 0) or 0
            units = self._to_number(item.get("units") or item.get("count") or 0) or 0
            total += sales
            normalized.append({"name": name, "sales_krw": int(sales), "units": int(units)})
        normalized.sort(key=lambda item: item["sales_krw"], reverse=True)
        top = normalized[0] if normalized else None
        concentration = top["sales_krw"] / total if top and total else None
        return {
            "products": normalized,
            "top_product": top,
            "concentration_rate": self._round_rate(concentration),
            "status": "concentrated" if concentration and concentration >= 0.60 else "balanced",
        }

    def _risk_items(
        self,
        *,
        sales_analysis: dict[str, Any],
        order_analysis: dict[str, Any],
        cost_analysis: dict[str, Any],
        marketing_efficiency: dict[str, Any],
        inventory_analysis: dict[str, Any],
        customer_analysis: dict[str, Any],
        product_mix: dict[str, Any],
    ) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        if sales_analysis["trend"] == "down":
            risks.append({
                "risk": "최근 매출 하락",
                "severity": "high",
                "basis": f"매출 변화율 {sales_analysis['change_rate']}",
                "action": "요일/채널별 매출을 분리해 하락 구간을 먼저 찾기",
            })
        if cost_analysis.get("known_cost_rate") is not None and cost_analysis["known_cost_rate"] >= 0.75:
            risks.append({
                "risk": "입력 비용 기준 마진 압박",
                "severity": "high",
                "basis": f"확인 비용률 {cost_analysis['known_cost_rate']}",
                "action": "원재료/광고/고정비 중 가장 큰 비용 항목부터 10% 절감안 만들기",
            })
        if marketing_efficiency.get("ad_cost_per_order_krw") and order_analysis.get("average_order_value_krw"):
            if marketing_efficiency["ad_cost_per_order_krw"] >= order_analysis["average_order_value_krw"] * 0.25:
                risks.append({
                    "risk": "광고비 대비 주문 효율 낮음",
                    "severity": "medium",
                    "basis": f"주문당 광고비 {marketing_efficiency['ad_cost_per_order_krw']}원",
                    "action": "광고 소재 2개만 남기고 클릭-주문 전환율을 비교",
                })
        if inventory_analysis["stockout_items"]:
            risks.append({
                "risk": "인기 품목 재고 부족",
                "severity": "medium",
                "basis": inventory_analysis["stockout_items"][:2],
                "action": "상위 판매 품목의 안전재고 기준 설정",
            })
        if inventory_analysis["slow_moving_items"]:
            risks.append({
                "risk": "저회전 재고 누적",
                "severity": "medium",
                "basis": inventory_analysis["slow_moving_items"][:2],
                "action": "묶음 구성이나 소량 할인으로 현금 회수",
            })
        if customer_analysis["sentiment"] == "negative_signal":
            risks.append({
                "risk": "고객 불만 신호",
                "severity": "medium",
                "basis": customer_analysis["categories"],
                "action": "가격/품질/대기/응대 중 반복 키워드 1개를 골라 즉시 개선",
            })
        if product_mix["status"] == "concentrated":
            risks.append({
                "risk": "특정 상품 매출 의존도 높음",
                "severity": "low",
                "basis": f"상위 상품 비중 {product_mix['concentration_rate']}",
                "action": "상위 상품은 유지하고 보조 상품 1개만 교차판매 테스트",
            })
        return risks

    def _root_causes(self, risk_items: list[dict[str, Any]]) -> list[str]:
        causes = []
        for item in risk_items:
            risk = item["risk"]
            if "매출" in risk:
                causes.append("방문/주문 전환 또는 영업일별 수요 변화 가능성")
            elif "마진" in risk:
                causes.append("비용 구조가 매출 규모보다 빠르게 커졌을 가능성")
            elif "광고" in risk:
                causes.append("광고 클릭 이후 구매 전환 설계가 약할 가능성")
            elif "재고" in risk:
                causes.append("수요 예측과 발주 기준이 아직 고정되지 않았을 가능성")
            elif "고객" in risk:
                causes.append("반복 불만이 상품/가격/응대 경험에 누적됐을 가능성")
            elif "상품" in risk:
                causes.append("매출원이 좁아 품절이나 유행 변화에 취약할 가능성")
        return self._unique(causes) or ["현재 입력만으로 뚜렷한 원인 단정은 어렵습니다."]

    def _recommended_actions(self, risk_items: list[dict[str, Any]], request: OperationRequest) -> list[str]:
        actions = [str(item["action"]) for item in risk_items]
        actions.extend(
            [
                "다음 주 핵심 지표를 매출, 주문 수, 고객 피드백 3개로 제한해 추적",
                "주간 운영 리포트를 저장하고 다음 추천에 반영",
            ]
        )
        if request.orders is None:
            actions.append("주문 수를 함께 기록해 객단가와 전환율을 계산")
        return self._unique(actions)

    def _next_week_plan(self, actions: list[str]) -> list[dict[str, str]]:
        focus = actions[0] if actions else "핵심 지표 3개 기록"
        return [
            {"day": "월요일", "task": "지난주 매출, 주문 수, 재고 메모를 한 표로 정리"},
            {"day": "수요일", "task": focus},
            {"day": "금요일", "task": "개선 전후 수치를 비교하고 다음 주 유지/중단 항목 결정"},
        ]

    def _missing_inputs(self, request: OperationRequest) -> list[str]:
        missing = []
        if not request.daily_sales_krw and not request.weekly_sales_krw and request.monthly_sales_krw is None:
            missing.append("매출 데이터")
        if request.orders is None and self._metric_value(request.metrics, "주문", "order") is None:
            missing.append("주문 수")
        if request.ad_spend_krw is None and request.impressions is None and request.clicks is None:
            missing.append("광고/유입 데이터")
        if not request.inventory_notes and not request.stockout_items and not request.slow_moving_items:
            missing.append("재고 메모")
        if not request.customer_feedback and not request.review_keywords and not request.complaints:
            missing.append("고객 피드백")
        if not request.product_sales:
            missing.append("상품별 판매")
        if request.material_cost_krw is None and request.fixed_cost_krw is None and request.labor_cost_krw is None:
            missing.append("비용 데이터")
        return missing

    def _needs_data_request(self, request: OperationRequest, missing_inputs: list[str]) -> bool:
        has_sales = bool(request.daily_sales_krw or request.weekly_sales_krw or request.monthly_sales_krw is not None)
        has_orders = request.orders is not None or self._metric_value(request.metrics, "주문", "order") is not None
        has_inventory = bool(request.inventory_notes or request.stockout_items or request.slow_moving_items)
        has_feedback = bool(request.customer_feedback or request.review_keywords or request.complaints)
        has_cost = any(
            value is not None
            for value in [request.ad_spend_krw, request.material_cost_krw, request.labor_cost_krw, request.fixed_cost_krw]
        )
        available_count = sum([has_sales, has_orders, has_inventory, has_feedback, has_cost, bool(request.product_sales)])
        return available_count < 2 and len(missing_inputs) >= 5

    def _received_data_flags(self, request: OperationRequest) -> dict[str, bool]:
        return {
            "sales": bool(request.daily_sales_krw or request.weekly_sales_krw or request.monthly_sales_krw is not None),
            "orders": request.orders is not None,
            "inventory": bool(request.inventory_notes or request.stockout_items or request.slow_moving_items),
            "customer_feedback": bool(request.customer_feedback or request.review_keywords or request.complaints),
            "costs": any(
                value is not None
                for value in [request.ad_spend_krw, request.material_cost_krw, request.labor_cost_krw, request.fixed_cost_krw]
            ),
            "product_sales": bool(request.product_sales),
        }

    def _confidence(self, missing_inputs: list[str]) -> str:
        if len(missing_inputs) <= 2:
            return "high"
        if len(missing_inputs) <= 4:
            return "medium"
        return "low"

    def _score(self, risk_items: list[dict[str, Any]], missing_inputs: list[str]) -> int:
        score = 88
        for item in risk_items:
            severity = item.get("severity")
            score -= 18 if severity == "high" else 10 if severity == "medium" else 5
        score -= min(20, len(missing_inputs) * 3)
        return max(35, min(95, score))

    def _handoff(self, risk_items: list[dict[str, Any]]) -> dict[str, list[str]]:
        agents = []
        reasons = []
        for item in risk_items:
            risk = item["risk"]
            if any(keyword in risk for keyword in ["마진", "비용", "매출"]):
                agents.append("FinanceAgent")
                reasons.append("손익 구조와 비용 절감 시나리오 확인")
            if "광고" in risk or "고객" in risk:
                agents.append("MarketingAgent")
                reasons.append("광고 소재, 고객 메시지, 전환율 개선")
            if "불만" in risk and any(keyword in str(item.get("basis")) for keyword in ["환불", "위생"]):
                agents.append("LegalAgent")
                reasons.append("환불, 표시, 위생 관련 체크 필요")
        return {"recommended_agents": self._unique(agents), "reasons": self._unique(reasons)}

    def _kpi_summary(self, *sections: dict[str, Any]) -> list[dict[str, Any]]:
        labels = [
            ("매출 추세", sections[0].get("trend")),
            ("평균 매출", sections[0].get("average_sales_krw")),
            ("객단가", sections[1].get("average_order_value_krw")),
            ("확인 비용률", sections[2].get("known_cost_rate")),
            ("주문당 광고비", sections[3].get("ad_cost_per_order_krw")),
            ("재고 상태", sections[4].get("status")),
            ("고객 반응", sections[5].get("sentiment")),
        ]
        return [{"label": label, "value": value} for label, value in labels]

    def _assumptions(self, request: OperationRequest, confidence: str) -> list[str]:
        assumptions = ["입력된 운영 데이터만 기준으로 분석했습니다."]
        if confidence != "high":
            assumptions.append("누락 데이터가 있어 원인과 개선 효과는 보수적으로 해석해야 합니다.")
        if request.monthly_sales_krw is None and request.weekly_sales_krw:
            assumptions.append("주간 매출은 같은 기준 기간의 순서형 데이터로 간주했습니다.")
        return assumptions

    def _recommendation(self, risk_items: list[dict[str, Any]], confidence: str) -> str:
        if risk_items:
            return f"{risk_items[0]['risk']}를 먼저 확인하고, 다음 주에는 {risk_items[0]['action']}를 실행하세요."
        if confidence == "low":
            return "운영 판단에 필요한 매출, 주문 수, 고객 피드백을 먼저 1주일만 같은 양식으로 기록하세요."
        return "현재 입력 기준 큰 위험 신호는 낮으니 핵심 지표 3개를 유지 추적하세요."

    def _data_limitations(self, missing_inputs: list[str], request: OperationRequest) -> list[str]:
        limitations = []
        if missing_inputs:
            limitations.append(f"누락 데이터: {', '.join(missing_inputs)}")
        if request.conversion_rate is None and (request.clicks is None or request.orders is None):
            limitations.append("광고 전환율은 클릭 수와 주문 수가 함께 있어야 정확히 계산됩니다.")
        if request.material_cost_krw is None:
            limitations.append("상품별 원가가 없어 실제 마진은 추정하지 않았습니다.")
        return limitations

    def _summary_fallback(self, data: dict[str, Any]) -> str:
        risks = data.get("risks") or []
        recommendation = data.get("recommendation")
        score = data.get("operation_score") or data.get("score")
        sales = data.get("sales_analysis") or {}
        orders = data.get("order_analysis") or {}
        marketing = data.get("marketing_efficiency") or {}
        inventory = data.get("inventory_analysis") or {}
        customer = data.get("customer_feedback_analysis") or {}
        top_risk = data.get("risk_items", [{}])[0] if data.get("risk_items") else {}

        evidence = []
        if sales.get("latest_sales_krw"):
            evidence.append(f"매출 {int(sales['latest_sales_krw']):,}원")
        if orders.get("orders"):
            evidence.append(f"주문 {orders['orders']}건")
        if marketing.get("ad_cost_per_order_krw"):
            evidence.append(f"주문당 광고비 {marketing['ad_cost_per_order_krw']:,}원")
        if inventory.get("stockout_items"):
            evidence.append(f"품절 신호 {inventory['stockout_items'][0]}")
        if inventory.get("slow_moving_items"):
            evidence.append(f"재고 누적 신호 {inventory['slow_moving_items'][0]}")
        price_feedback = (customer.get("categories") or {}).get("price") or []
        waiting_feedback = (customer.get("categories") or {}).get("waiting") or []
        if price_feedback or waiting_feedback:
            evidence.append("고객 피드백에 가격/대기 이슈 포함")

        basis = f"근거는 {', '.join(evidence)}입니다. " if evidence else ""
        risk_basis = f"특히 {top_risk.get('basis')} 때문에 " if top_risk.get("basis") else ""
        return (
            f"운영 점수는 {score}점이며, {basis}{risk_basis}"
            f"주요 위험은 {risks[0] if risks else '위험 낮음'}입니다. {recommendation}"
        )

    def _metric_value(self, metrics: list[OperationMetric], *keywords: str) -> float | None:
        lowered = [keyword.lower() for keyword in keywords]
        for metric in metrics:
            name = metric.name.lower()
            if any(keyword in name for keyword in lowered):
                return metric.value
        return None

    def _to_number(self, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(",", "").strip()
        if text.endswith("만원"):
            text = text[:-2].strip()
            multiplier = 10_000
        elif text.endswith("천원"):
            text = text[:-2].strip()
            multiplier = 1_000
        else:
            text = text.replace("원", "").strip()
            multiplier = 1
        try:
            return float(text) * multiplier
        except ValueError:
            return None

    def _round_rate(self, value: float | None) -> float | None:
        return round(value, 4) if value is not None else None

    def _unique(self, values: list[Any]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            item = str(value).strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result
