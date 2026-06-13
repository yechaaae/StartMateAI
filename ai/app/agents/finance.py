from __future__ import annotations

import json
from math import ceil
import re
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, FinanceAssumption, FinanceRequest, StartupProfile


DEFAULT_ASSUMPTION = FinanceAssumption()


BUSINESS_TYPE_ALIASES = {
    "cafe": "offline_store",
    "commerce": "ecommerce",
    "content": "sns_service",
    "food": "reservation_food",
    "restaurant": "reservation_food",
    "service": "local_service",
}


FINANCE_TEMPLATES: dict[str, dict[str, Any]] = {
    "generic_bootstrap": {
        "label": "범용 소자본 검증",
        "sales_channel": "direct",
        "unit_label": "건",
        "aliases": [],
        "values": {
            "rent_krw_per_month": 0,
            "equipment_krw": 500_000,
            "initial_inventory_krw": 300_000,
            "marketing_krw_per_month": 150_000,
            "other_fixed_cost_krw_per_month": 100_000,
            "price_per_unit_krw": 30_000,
            "expected_daily_customers": 3,
            "variable_cost_rate": 0.30,
            "platform_fee_rate": 0.0,
            "payment_fee_rate": 0.03,
            "operating_days_per_month": 20,
            "cash_reserve_months": 1,
        },
    },
    "reservation_food": {
        "label": "소량 예약 판매",
        "sales_channel": "reservation",
        "unit_label": "주문",
        "aliases": ["한식", "소량", "예약", "반찬", "도시락", "푸드", "공유주방", "식품", "요식"],
        "values": {
            "rent_krw_per_month": 300_000,
            "equipment_krw": 800_000,
            "initial_inventory_krw": 600_000,
            "marketing_krw_per_month": 200_000,
            "other_fixed_cost_krw_per_month": 150_000,
            "price_per_unit_krw": 12_000,
            "expected_daily_customers": 12,
            "variable_cost_rate": 0.42,
            "platform_fee_rate": 0.02,
            "payment_fee_rate": 0.025,
            "packaging_cost_krw_per_unit": 800,
            "operating_days_per_month": 20,
            "cash_reserve_months": 1,
        },
    },
    "sns_service": {
        "label": "SNS/브랜딩 대행",
        "sales_channel": "service",
        "unit_label": "프로젝트",
        "aliases": ["sns", "홍보", "콘텐츠", "디자인", "브랜딩", "대행", "마케팅"],
        "values": {
            "rent_krw_per_month": 0,
            "equipment_krw": 700_000,
            "initial_inventory_krw": 0,
            "marketing_krw_per_month": 150_000,
            "other_fixed_cost_krw_per_month": 120_000,
            "price_per_unit_krw": 180_000,
            "expected_daily_customers": 1,
            "variable_cost_rate": 0.12,
            "platform_fee_rate": 0.0,
            "payment_fee_rate": 0.02,
            "packaging_cost_krw_per_unit": 0,
            "operating_days_per_month": 18,
            "cash_reserve_months": 1,
        },
    },
    "local_service": {
        "label": "로컬 운영 점검 서비스",
        "sales_channel": "service",
        "unit_label": "건",
        "aliases": ["점검", "운영", "컨설팅", "소상공인", "스마트", "서비스"],
        "values": {
            "rent_krw_per_month": 0,
            "equipment_krw": 500_000,
            "initial_inventory_krw": 0,
            "marketing_krw_per_month": 180_000,
            "other_fixed_cost_krw_per_month": 100_000,
            "price_per_unit_krw": 250_000,
            "expected_daily_customers": 1,
            "variable_cost_rate": 0.10,
            "platform_fee_rate": 0.0,
            "payment_fee_rate": 0.02,
            "operating_days_per_month": 16,
            "cash_reserve_months": 1,
        },
    },
    "popup": {
        "label": "팝업/플리마켓",
        "sales_channel": "offline",
        "unit_label": "판매",
        "aliases": ["팝업", "플리마켓", "오프라인", "공유매장"],
        "values": {
            "rent_krw_per_month": 700_000,
            "equipment_krw": 1_000_000,
            "initial_inventory_krw": 700_000,
            "marketing_krw_per_month": 300_000,
            "other_fixed_cost_krw_per_month": 200_000,
            "price_per_unit_krw": 10_000,
            "expected_daily_customers": 25,
            "variable_cost_rate": 0.45,
            "payment_fee_rate": 0.03,
            "packaging_cost_krw_per_unit": 500,
            "operating_days_per_month": 12,
            "cash_reserve_months": 1,
        },
    },
    "ecommerce": {
        "label": "온라인 판매",
        "sales_channel": "online",
        "unit_label": "주문",
        "aliases": ["온라인", "커머스", "쇼핑", "굿즈", "판매", "스토어"],
        "values": {
            "rent_krw_per_month": 0,
            "equipment_krw": 500_000,
            "initial_inventory_krw": 1_000_000,
            "marketing_krw_per_month": 300_000,
            "other_fixed_cost_krw_per_month": 150_000,
            "price_per_unit_krw": 18_000,
            "expected_daily_customers": 8,
            "variable_cost_rate": 0.50,
            "platform_fee_rate": 0.08,
            "payment_fee_rate": 0.03,
            "packaging_cost_krw_per_unit": 900,
            "delivery_cost_krw_per_unit": 0,
            "operating_days_per_month": 26,
            "cash_reserve_months": 1,
        },
    },
    "offline_store": {
        "label": "오프라인 매장",
        "sales_channel": "offline",
        "unit_label": "판매",
        "aliases": ["카페", "매장", "디저트", "상권", "오프라인"],
        "values": {
            "rent_krw_per_month": 2_000_000,
            "equipment_krw": 3_000_000,
            "initial_inventory_krw": 1_200_000,
            "marketing_krw_per_month": 400_000,
            "labor_cost_krw_per_month": 0,
            "other_fixed_cost_krw_per_month": 500_000,
            "price_per_unit_krw": 8_000,
            "expected_daily_customers": 40,
            "variable_cost_rate": 0.35,
            "payment_fee_rate": 0.03,
            "operating_days_per_month": 26,
            "cash_reserve_months": 2,
        },
    },
}


class FinanceAgent(BaseAgent):
    name = "FinanceAgent"

    async def suggest_simulation_assumption(
        self,
        *,
        profile: StartupProfile,
        item_name: str,
        business_type: str = "",
        monthly_rent: int | None = None,
    ) -> dict[str, Any]:
        """시뮬레이션 가정값 단계용으로 LLM이 3가지 시나리오(보수적/보통/공격적)를 제안한다(룰 폴백)."""
        budget = profile.budget_krw or 10_000_000
        rent = int(monthly_rent or 0)
        fallback = self._fallback_scenarios(business_type, int(budget), rent)
        if not self.llm.is_enabled:
            return {"scenarios": fallback}
        prompt = (
            "너는 창업 재무 시뮬레이션 가정값을 제안하는 에이전트다.\n"
            "주어진 아이템/지역/프로필로 첫 30일 시뮬레이션에 쓸 가정값을 '보수적/보통/공격적' 3가지 시나리오로 제안해라.\n"
            "반드시 JSON object 하나만 출력해라. 설명/주석/markdown 금지.\n"
            "출력 schema(원 단위 정수, variableCostRate만 0~1 소수):\n"
            "{\n"
            '  "scenarios": [\n'
            "    {\n"
            '      "key": "conservative"|"normal"|"aggressive",\n'
            '      "label": string,        // 짧은 한글 라벨 (예: 보수적/보통/공격적)\n'
            '      "description": string,  // 한 줄 설명\n'
            '      "pricePerOrder": number,\n'
            '      "expectedDailyOrders": number,\n'
            '      "operatingDays": number,\n'
            '      "monthlyRent": number,\n'
            '      "laborCost": number,\n'
            '      "marketingCost": number,\n'
            '      "otherFixedCost": number,\n'
            '      "variableCostRate": number,\n'
            '      "initialBudget": number\n'
            "    }\n"
            "  ]   // 정확히 3개, 보수적 -> 보통 -> 공격적 순서\n"
            "}\n\n"
            f"item: {item_name}\n"
            f"business_type: {business_type}\n"
            f"monthly_rent_hint: {rent}\n"
            f"profile: {json.dumps(profile.model_dump(), ensure_ascii=False)}"
        )
        try:
            raw = await self.llm.complete(
                system_prompt="You are a strict JSON startup finance assumption engine.",
                user_prompt=prompt,
                temperature=0.3,
                fallback="{}",
            )
            parsed = self._parse_assumption_json(raw)
        except Exception:
            parsed = {}
        raw_scenarios = parsed.get("scenarios") if isinstance(parsed, dict) else None
        if not isinstance(raw_scenarios, list) or not raw_scenarios:
            return {"scenarios": fallback}
        scenarios: list[dict[str, Any]] = []
        for index, item in enumerate(raw_scenarios[:3]):
            if not isinstance(item, dict):
                continue
            base_fb = fallback[min(index, len(fallback) - 1)]
            norm = self._normalize_assumption(item, base_fb, rent)
            norm["key"] = str(item.get("key") or base_fb["key"])
            norm["label"] = str(item.get("label") or base_fb["label"])
            norm["description"] = str(item.get("description") or base_fb["description"])
            scenarios.append(norm)
        return {"scenarios": scenarios or fallback}

    def _fallback_assumption(self, business_type: str, budget: int, rent: int) -> dict[str, Any]:
        bt = str(business_type or "").lower()
        price = {"cafe": 8000, "commerce": 15000, "content": 35000, "popup": 12000, "service": 50000, "food": 12000}.get(bt, 15000)
        daily = {"cafe": 40, "commerce": 20, "content": 4, "popup": 35, "service": 6, "food": 30}.get(bt, 25)
        return {
            "pricePerOrder": price,
            "expectedDailyOrders": daily,
            "operatingDays": 24,
            "monthlyRent": rent or 2_000_000,
            "laborCost": 1_500_000,
            "marketingCost": 500_000,
            "otherFixedCost": 500_000,
            "variableCostRate": 0.35,
            "initialBudget": max(3_000_000, int(budget)),
        }

    def _fallback_scenarios(self, business_type: str, budget: int, rent: int) -> list[dict[str, Any]]:
        base = self._fallback_assumption(business_type, budget, rent)
        daily = base["expectedDailyOrders"]
        return [
            {
                **base,
                "key": "conservative",
                "label": "보수적",
                "description": "비용을 아끼고 작게 시작하는 가정",
                "expectedDailyOrders": max(1, round(daily * 0.7)),
                "laborCost": 800_000,
                "marketingCost": 200_000,
                "otherFixedCost": 300_000,
                "variableCostRate": 0.32,
            },
            {
                **base,
                "key": "normal",
                "label": "보통",
                "description": "기본 인건비와 홍보비를 반영한 가정",
            },
            {
                **base,
                "key": "aggressive",
                "label": "공격적",
                "description": "초기 홍보·운영비를 넉넉히 잡은 가정",
                "expectedDailyOrders": round(daily * 1.3),
                "laborCost": 2_200_000,
                "marketingCost": 900_000,
                "otherFixedCost": 800_000,
                "variableCostRate": 0.4,
            },
        ]

    def _parse_assumption_json(self, raw: str) -> dict[str, Any]:
        text = str(raw or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end < start:
                return {}
            try:
                parsed = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return parsed if isinstance(parsed, dict) else {}

    def _normalize_assumption(self, parsed: dict[str, Any], fallback: dict[str, Any], rent: int) -> dict[str, Any]:
        def as_int(value: Any, default: int) -> int:
            try:
                return max(0, int(round(float(value))))
            except (TypeError, ValueError):
                return default

        def as_rate(value: Any, default: float) -> float:
            try:
                rate = float(value)
            except (TypeError, ValueError):
                return default
            if rate > 1:
                rate = rate / 100
            return round(max(0.05, min(0.9, rate)), 2)

        return {
            "pricePerOrder": as_int(parsed.get("pricePerOrder"), fallback["pricePerOrder"]),
            "expectedDailyOrders": as_int(parsed.get("expectedDailyOrders"), fallback["expectedDailyOrders"]),
            "operatingDays": min(31, max(1, as_int(parsed.get("operatingDays"), fallback["operatingDays"]))),
            "monthlyRent": as_int(parsed.get("monthlyRent"), rent or fallback["monthlyRent"]),
            "laborCost": as_int(parsed.get("laborCost"), fallback["laborCost"]),
            "marketingCost": as_int(parsed.get("marketingCost"), fallback["marketingCost"]),
            "otherFixedCost": as_int(parsed.get("otherFixedCost"), fallback["otherFixedCost"]),
            "variableCostRate": as_rate(parsed.get("variableCostRate"), fallback["variableCostRate"]),
            "initialBudget": as_int(parsed.get("initialBudget"), fallback["initialBudget"]),
        }

    async def run(self, request: FinanceRequest) -> AgentResponse:
        assumption, template_key, assumption_meta, warnings = await self._resolve_assumption(
            request.assumption,
            request.profile,
        )
        metrics = self._calculate(assumption)
        budget = request.profile.budget_krw
        budget_analysis = self._budget_analysis(
            budget=budget,
            initial_cash_needed=metrics["initial_cash_needed_krw"],
            monthly_profit=metrics["monthly_profit_krw"],
        )
        scenario_table = self._scenario_table(assumption)
        cash_flow_projection = self._cash_flow_projection(
            budget=budget,
            initial_cash_needed=metrics["initial_cash_needed_krw"],
            monthly_profit=metrics["monthly_profit_krw"],
        )
        support_handoff = self._support_handoff(assumption, metrics, budget_analysis)
        risks = self._risks(request.profile, assumption, metrics, budget_analysis)
        missing_inputs = self._missing_inputs(request.profile, assumption)
        score = self._score(request.profile, assumption, metrics, budget_analysis)
        risk_grade = self._risk_grade(score)
        recommendation = self._recommendation(metrics, budget_analysis)

        data = self.agent_data(
            position="초기 현금, 월 손익, 손익분기 판매량을 함께 봐야 실행 가능성을 판단할 수 있습니다.",
            evidence={
                "assumption_source": assumption_meta["source"],
                "template_confidence": assumption_meta["confidence"],
                "budget_status": budget_analysis["status"],
                "monthly_profit_krw": metrics["monthly_profit_krw"],
                "break_even_units_per_day": metrics["break_even_units_per_day"],
                "initial_cash_needed_krw": metrics["initial_cash_needed_krw"],
                "funding_gap_krw": budget_analysis["funding_gap_krw"],
                "risk_grade": risk_grade,
            },
            score=score,
            risks=risks,
            assumptions=self._assumption_notes(assumption, template_key),
            missing_inputs=missing_inputs,
            recommendation=recommendation,
            payload={
                "item_name": assumption.item_name,
                "business_type": assumption.business_type,
                "finance_template": template_key,
                "assumption_source": assumption_meta["source"],
                "template_confidence": assumption_meta["confidence"],
                "template_selection_reason": assumption_meta["reason"],
                "llm_assumption_diagnostics": assumption_meta.get("llm_diagnostics"),
                "sales_channel": assumption.sales_channel,
                "unit_label": assumption.unit_label,
                "price_per_unit_krw": assumption.price_per_unit_krw,
                "expected_daily_customers": assumption.expected_daily_customers,
                "operating_days_per_month": assumption.operating_days_per_month,
                "variable_cost_rate": assumption.variable_cost_rate,
                "platform_fee_rate": assumption.platform_fee_rate,
                "payment_fee_rate": assumption.payment_fee_rate,
                "monthly_revenue_krw": metrics["monthly_revenue_krw"],
                "monthly_variable_cost_krw": metrics["monthly_variable_cost_krw"],
                "monthly_platform_fee_krw": metrics["monthly_platform_fee_krw"],
                "monthly_payment_fee_krw": metrics["monthly_payment_fee_krw"],
                "monthly_tax_buffer_krw": metrics["monthly_tax_buffer_krw"],
                "monthly_fixed_cost_krw": metrics["monthly_fixed_cost_krw"],
                "monthly_total_cost_krw": metrics["monthly_total_cost_krw"],
                "monthly_profit_krw": metrics["monthly_profit_krw"],
                "gross_margin_rate": metrics["gross_margin_rate"],
                "contribution_margin_per_unit_krw": metrics["contribution_margin_per_unit_krw"],
                "break_even_units_per_month": metrics["break_even_units_per_month"],
                "break_even_units_per_day": metrics["break_even_units_per_day"],
                "initial_cash_needed_krw": metrics["initial_cash_needed_krw"],
                "startup_cost_breakdown": metrics["startup_cost_breakdown"],
                "payback_months": metrics["payback_months"],
                "risk_grade": risk_grade,
                "budget_analysis": budget_analysis,
                "cash_flow_projection": cash_flow_projection,
                "scenario_table": scenario_table,
                "support_handoff": support_handoff,
                "calculation_basis": self._calculation_basis(assumption, metrics),
                "thirty_day_timeline": self._thirty_day_timeline(budget_analysis),
            },
        )
        fallback = (
            f"{assumption.item_name} 기준 초기 필요 현금은 {metrics['initial_cash_needed_krw']:,}원, "
            f"일 손익분기점은 {metrics['break_even_units_per_day']} {assumption.unit_label}입니다."
        )
        summary = await self.polish_summary(
            task="financial simulation",
            data=data,
            fallback=fallback,
            instructions="숫자 근거를 1개 이상 포함하고, 과도하게 확정적으로 말하지 마세요.",
        )

        return AgentResponse(
            intent="finance",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "실제 임대료, 원가율, 판매 가능 수량을 입력해 가정을 보정",
                "가장 보수적인 시나리오에서도 30일 테스트가 가능한지 확인",
                "부족 금액이 있으면 PolicyAgent에 지원 유형을 넘겨 매칭",
            ],
            warnings=warnings,
        )

    async def _resolve_assumption(
        self,
        assumption: FinanceAssumption,
        profile: StartupProfile,
    ) -> tuple[FinanceAssumption, str, dict[str, Any], list[str]]:
        template_key, confidence, reason = self._pick_template(assumption, profile)
        warnings: list[str] = []
        template = FINANCE_TEMPLATES.get(template_key, {})
        updates: dict[str, Any] = {}
        llm_diagnostics: dict[str, Any] | None = None

        if template_key == "generic_bootstrap" and self.llm.is_enabled:
            llm_updates, llm_diagnostics = await self._generate_assumption_with_llm(assumption, profile)
            if llm_updates:
                updates.update(llm_updates)
                template_key = "llm_custom"
                confidence = "medium"
                reason = "템플릿 매칭이 없어 LLM이 업종 설명에서 재무 가정을 추출했습니다."
            else:
                warnings.extend(llm_diagnostics.get("warnings", []) if llm_diagnostics else [])

        if template_key == "generic_bootstrap":
            warnings.append("finance_template_generic_fallback_used")

        explicit_fields = assumption.model_fields_set
        for field, value in template.get("values", {}).items():
            if field in explicit_fields:
                continue
            current = getattr(assumption, field)
            default = getattr(DEFAULT_ASSUMPTION, field)
            if current == default and field not in updates:
                updates[field] = value

        if assumption.business_type == "auto":
            updates.setdefault("business_type", template_key)
        if assumption.sales_channel == "auto":
            updates.setdefault("sales_channel", template.get("sales_channel", "direct"))
        if assumption.unit_label == DEFAULT_ASSUMPTION.unit_label:
            updates.setdefault("unit_label", template.get("unit_label", assumption.unit_label))

        meta = {
            "source": "llm_generated" if template_key == "llm_custom" else "template",
            "confidence": confidence,
            "reason": reason,
            "llm_diagnostics": llm_diagnostics,
        }
        return assumption.model_copy(update=updates), template_key, meta, warnings

    def _pick_template(self, assumption: FinanceAssumption, profile: StartupProfile) -> tuple[str, str, str]:
        if assumption.business_type != "auto":
            if assumption.business_type in FINANCE_TEMPLATES:
                return assumption.business_type, "high", "명시된 business_type과 재정 템플릿이 일치했습니다."
            if assumption.business_type in BUSINESS_TYPE_ALIASES:
                return BUSINESS_TYPE_ALIASES[assumption.business_type], "high", "명시된 business_type을 내부 재정 템플릿으로 매핑했습니다."

        item_text = assumption.item_name.lower()
        for key, template in FINANCE_TEMPLATES.items():
            if any(alias.lower() in item_text for alias in template["aliases"]):
                return key, "high", "아이템명 키워드가 재정 템플릿과 직접 일치했습니다."

        profile_text = " ".join(
            [
                " ".join(profile.interests),
                " ".join(profile.preferred_business_types),
                " ".join(profile.preferred_channels),
            ]
        ).lower()
        for key, template in FINANCE_TEMPLATES.items():
            if any(alias.lower() in profile_text for alias in template["aliases"]):
                return key, "low", "아이템명 매칭은 없고 프로필 관심사로 보조 추론했습니다."
        return "generic_bootstrap", "low", "일치하는 업종 템플릿이 없어 범용 소자본 검증 가정을 사용했습니다."

    async def _generate_assumption_with_llm(
        self,
        assumption: FinanceAssumption,
        profile: StartupProfile,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        diagnostics: dict[str, Any] = {
            "attempted": True,
            "warnings": [],
        }
        prompt = (
            "너는 창업 재무 가정 추출기다. 사용자의 아이템 설명을 보고 30일 검증용 재무 가정을 JSON object로만 출력해라.\n"
            "정확한 시장 평균을 아는 척하지 말고, 소자본 예비창업자가 첫 테스트를 할 때의 보수적 기본값을 잡아라.\n"
            "사용자가 이미 명시한 숫자는 바꾸지 말고, 알 수 없는 값은 낮은 고정비 기준으로 둬라.\n\n"
            "출력 schema:\n"
            "{\n"
            '  "business_type": string,\n'
            '  "sales_channel": "direct"|"online"|"offline"|"reservation"|"service",\n'
            '  "unit_label": string,\n'
            '  "rent_krw_per_month": number,\n'
            '  "equipment_krw": number,\n'
            '  "initial_inventory_krw": number,\n'
            '  "marketing_krw_per_month": number,\n'
            '  "labor_cost_krw_per_month": number,\n'
            '  "other_fixed_cost_krw_per_month": number,\n'
            '  "price_per_unit_krw": number,\n'
            '  "expected_daily_customers": number,\n'
            '  "variable_cost_rate": number,\n'
            '  "platform_fee_rate": number,\n'
            '  "payment_fee_rate": number,\n'
            '  "packaging_cost_krw_per_unit": number,\n'
            '  "delivery_cost_krw_per_unit": number,\n'
            '  "operating_days_per_month": number,\n'
            '  "cash_reserve_months": number,\n'
            '  "reason": string\n'
            "}\n\n"
            f"assumption: {json.dumps(assumption.model_dump(), ensure_ascii=False)}\n"
            f"profile: {json.dumps(profile.model_dump(), ensure_ascii=False)}"
        )
        try:
            raw = await self.llm.complete(
                system_prompt="You are a strict JSON financial assumption extraction engine.",
                user_prompt=prompt,
                temperature=0.15,
                fallback="{}",
            )
            diagnostics["raw_preview"] = self._debug_preview(raw)
            parsed = self._parse_json_object(raw)
            diagnostics["parsed_keys"] = sorted(parsed) if isinstance(parsed, dict) else []
            updates = self._sanitize_llm_assumption(parsed, assumption)
            diagnostics["sanitized_fields"] = sorted(updates)
            if not updates:
                diagnostics["warnings"].append("finance_llm_assumption_no_valid_fields")
            if isinstance(parsed, dict) and parsed.get("reason"):
                diagnostics["reason"] = self._debug_preview(parsed.get("reason"), limit=300)
            return updates, diagnostics
        except Exception as error:
            diagnostics["error_type"] = error.__class__.__name__
            diagnostics["error_message"] = self._debug_preview(str(error), limit=1000)
            diagnostics["warnings"].append(f"finance_llm_assumption_error:{error.__class__.__name__}")
            return {}, diagnostics

    def _sanitize_llm_assumption(
        self,
        parsed: dict[str, Any],
        original: FinanceAssumption,
    ) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            return {}

        updates: dict[str, Any] = {}
        int_ranges = {
            "rent_krw_per_month": (0, 10_000_000),
            "equipment_krw": (0, 20_000_000),
            "initial_inventory_krw": (0, 20_000_000),
            "marketing_krw_per_month": (0, 5_000_000),
            "labor_cost_krw_per_month": (0, 10_000_000),
            "other_fixed_cost_krw_per_month": (0, 5_000_000),
            "price_per_unit_krw": (100, 5_000_000),
            "expected_daily_customers": (1, 1_000),
            "packaging_cost_krw_per_unit": (0, 100_000),
            "delivery_cost_krw_per_unit": (0, 100_000),
            "operating_days_per_month": (1, 31),
            "cash_reserve_months": (0, 12),
        }
        rate_ranges = {
            "variable_cost_rate": (0.0, 0.95),
            "platform_fee_rate": (0.0, 0.50),
            "payment_fee_rate": (0.0, 0.20),
            "tax_buffer_rate": (0.0, 0.40),
            "startup_buffer_rate": (0.0, 0.50),
        }

        for field, (minimum, maximum) in int_ranges.items():
            if getattr(original, field) != getattr(DEFAULT_ASSUMPTION, field):
                continue
            value = self._coerce_int(parsed.get(field))
            if value is not None:
                updates[field] = max(minimum, min(maximum, value))

        for field, (minimum, maximum) in rate_ranges.items():
            if getattr(original, field) != getattr(DEFAULT_ASSUMPTION, field):
                continue
            value = self._coerce_rate(parsed.get(field))
            if value is not None:
                updates[field] = max(minimum, min(maximum, value))

        if original.business_type == "auto":
            business_type = self._safe_text(parsed.get("business_type"), limit=40)
            if business_type:
                updates["business_type"] = business_type
        if original.sales_channel == "auto":
            sales_channel = self._safe_text(parsed.get("sales_channel"), limit=20)
            if sales_channel in {"direct", "online", "offline", "reservation", "service"}:
                updates["sales_channel"] = sales_channel
        if original.unit_label == DEFAULT_ASSUMPTION.unit_label:
            unit_label = self._safe_text(parsed.get("unit_label"), limit=12)
            if unit_label:
                updates["unit_label"] = unit_label
        return updates

    def _parse_json_object(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < start:
                return {}
            parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else {}

    def _coerce_int(self, value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value).replace(",", "").strip()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)?", text)
        if not match:
            return None
        amount = float(match.group(1))
        unit = match.group(2)
        if unit == "억":
            return int(amount * 100_000_000)
        if unit == "천만":
            return int(amount * 10_000_000)
        if unit == "백만":
            return int(amount * 1_000_000)
        if unit in {"만원", "만"}:
            return int(amount * 10_000)
        return int(amount)

    def _coerce_rate(self, value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            number = float(value)
        else:
            text = str(value).strip()
            match = re.search(r"(\d+(?:\.\d+)?)", text)
            if not match:
                return None
            number = float(match.group(1))
            if "%" in text:
                number = number / 100
        if number > 1:
            number = number / 100
        return number

    def _safe_text(self, value: Any, *, limit: int) -> str:
        text = str(value or "").strip()
        text = re.sub(r"[\r\n\t]+", " ", text)
        return text[:limit]

    def _debug_preview(self, value: Any, *, limit: int = 800) -> str:
        text = str(value).replace("\r", "\\r").replace("\n", "\\n")
        if len(text) <= limit:
            return text
        return text[:limit] + "...<truncated>"

    def _calculate(self, assumption: FinanceAssumption) -> dict[str, Any]:
        monthly_units = assumption.expected_daily_customers * assumption.operating_days_per_month
        monthly_revenue = assumption.price_per_unit_krw * monthly_units
        material_cost_per_unit = int(assumption.price_per_unit_krw * assumption.variable_cost_rate)
        extra_unit_cost = assumption.packaging_cost_krw_per_unit + assumption.delivery_cost_krw_per_unit
        variable_cost_per_unit = material_cost_per_unit + extra_unit_cost
        monthly_variable_cost = variable_cost_per_unit * monthly_units
        monthly_platform_fee = int(monthly_revenue * assumption.platform_fee_rate)
        monthly_payment_fee = int(monthly_revenue * assumption.payment_fee_rate)
        monthly_fixed_cost = (
            assumption.rent_krw_per_month
            + assumption.marketing_krw_per_month
            + assumption.labor_cost_krw_per_month
            + assumption.other_fixed_cost_krw_per_month
        )
        profit_before_tax_buffer = (
            monthly_revenue
            - monthly_variable_cost
            - monthly_platform_fee
            - monthly_payment_fee
            - monthly_fixed_cost
        )
        monthly_tax_buffer = int(max(profit_before_tax_buffer, 0) * assumption.tax_buffer_rate)
        monthly_total_cost = (
            monthly_variable_cost
            + monthly_platform_fee
            + monthly_payment_fee
            + monthly_fixed_cost
            + monthly_tax_buffer
        )
        monthly_profit = monthly_revenue - monthly_total_cost
        contribution_margin = (
            assumption.price_per_unit_krw
            - variable_cost_per_unit
            - int(assumption.price_per_unit_krw * (assumption.platform_fee_rate + assumption.payment_fee_rate))
        )
        contribution_margin = max(contribution_margin, 0)
        break_even_units_per_month = (
            None if contribution_margin <= 0 else ceil(monthly_fixed_cost / contribution_margin)
        )
        break_even_units_per_day = (
            None
            if break_even_units_per_month is None
            else ceil(break_even_units_per_month / assumption.operating_days_per_month)
        )
        startup_base = assumption.equipment_krw + assumption.initial_inventory_krw
        reserve_cash = monthly_fixed_cost * assumption.cash_reserve_months
        startup_buffer = int((startup_base + reserve_cash) * assumption.startup_buffer_rate)
        initial_cash_needed = startup_base + reserve_cash + startup_buffer
        payback_months = None if monthly_profit <= 0 else round(initial_cash_needed / monthly_profit, 1)
        gross_margin_rate = 0.0 if monthly_revenue <= 0 else round((monthly_revenue - monthly_variable_cost) / monthly_revenue, 3)

        return {
            "monthly_units": monthly_units,
            "monthly_revenue_krw": monthly_revenue,
            "monthly_variable_cost_krw": monthly_variable_cost,
            "monthly_platform_fee_krw": monthly_platform_fee,
            "monthly_payment_fee_krw": monthly_payment_fee,
            "monthly_tax_buffer_krw": monthly_tax_buffer,
            "monthly_fixed_cost_krw": monthly_fixed_cost,
            "monthly_total_cost_krw": monthly_total_cost,
            "monthly_profit_krw": monthly_profit,
            "gross_margin_rate": gross_margin_rate,
            "contribution_margin_per_unit_krw": contribution_margin,
            "break_even_units_per_month": break_even_units_per_month,
            "break_even_units_per_day": break_even_units_per_day,
            "initial_cash_needed_krw": initial_cash_needed,
            "startup_cost_breakdown": {
                "equipment_krw": assumption.equipment_krw,
                "initial_inventory_krw": assumption.initial_inventory_krw,
                "reserve_cash_krw": reserve_cash,
                "startup_buffer_krw": startup_buffer,
            },
            "payback_months": payback_months,
        }

    def _budget_analysis(
        self,
        *,
        budget: int | None,
        initial_cash_needed: int,
        monthly_profit: int,
    ) -> dict[str, Any]:
        if budget is None:
            return {
                "status": "budget_missing",
                "budget_krw": None,
                "remaining_cash_after_startup_krw": None,
                "funding_gap_krw": None,
                "runway_months_after_startup": None,
                "message": "현재 예산이 없어 예산 적합도는 보류했습니다.",
            }

        remaining = budget - initial_cash_needed
        funding_gap = max(0, -remaining)
        runway = None
        if remaining > 0 and monthly_profit < 0:
            runway = round(remaining / abs(monthly_profit), 1)

        if funding_gap > 0:
            status = "funding_gap"
            message = f"초기 필요 현금이 예산보다 {funding_gap:,}원 큽니다."
        elif remaining < budget * 0.15:
            status = "tight"
            message = "시작은 가능하지만 예비 현금이 얇습니다."
        else:
            status = "feasible"
            message = "현재 예산 안에서 1차 실행이 가능합니다."

        return {
            "status": status,
            "budget_krw": budget,
            "remaining_cash_after_startup_krw": remaining,
            "funding_gap_krw": funding_gap,
            "runway_months_after_startup": runway,
            "message": message,
        }

    def _scenario_table(self, assumption: FinanceAssumption) -> list[dict[str, Any]]:
        scenarios = [
            {
                "scenario": "base",
                "label": "기본 가정",
                "assumption": assumption,
                "note": "현재 입력값 기준입니다.",
            },
            {
                "scenario": "conservative_sales",
                "label": "고객 수 20% 감소",
                "assumption": assumption.model_copy(
                    update={"expected_daily_customers": max(1, int(assumption.expected_daily_customers * 0.8))}
                ),
                "note": "초기 홍보 반응이 기대보다 낮은 경우입니다.",
            },
            {
                "scenario": "cost_pressure",
                "label": "원가율 10%p 상승",
                "assumption": assumption.model_copy(
                    update={"variable_cost_rate": min(0.95, assumption.variable_cost_rate + 0.10)}
                ),
                "note": "재료비, 외주비, 수수료 압박이 생기는 경우입니다.",
            },
            {
                "scenario": "lean_start",
                "label": "저고정비 시작",
                "assumption": assumption.model_copy(
                    update={
                        "rent_krw_per_month": max(0, int(assumption.rent_krw_per_month * 0.3)),
                        "equipment_krw": max(0, int(assumption.equipment_krw * 0.6)),
                        "marketing_krw_per_month": max(50_000, int(assumption.marketing_krw_per_month * 0.6)),
                    }
                ),
                "note": "공유공간, 중고 장비, 작은 테스트로 시작하는 경우입니다.",
            },
        ]

        result = []
        for item in scenarios:
            metrics = self._calculate(item["assumption"])
            result.append(
                {
                    "scenario": item["scenario"],
                    "label": item["label"],
                    "monthly_revenue_krw": metrics["monthly_revenue_krw"],
                    "monthly_profit_krw": metrics["monthly_profit_krw"],
                    "break_even_units_per_day": metrics["break_even_units_per_day"],
                    "initial_cash_needed_krw": metrics["initial_cash_needed_krw"],
                    "note": item["note"],
                }
            )
        return result

    def _cash_flow_projection(
        self,
        *,
        budget: int | None,
        initial_cash_needed: int,
        monthly_profit: int,
    ) -> list[dict[str, Any]]:
        opening_cash = None if budget is None else budget - initial_cash_needed
        rows = []
        running_cash = opening_cash
        for month in range(1, 4):
            if running_cash is not None:
                running_cash += monthly_profit
            rows.append(
                {
                    "month": month,
                    "monthly_profit_krw": monthly_profit,
                    "cash_balance_krw": running_cash,
                    "status": self._cash_status(running_cash),
                }
            )
        return rows

    def _cash_status(self, cash_balance: int | None) -> str:
        if cash_balance is None:
            return "unknown"
        if cash_balance < 0:
            return "shortage"
        if cash_balance < 500_000:
            return "thin"
        return "ok"

    def _support_handoff(
        self,
        assumption: FinanceAssumption,
        metrics: dict[str, Any],
        budget_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        needed_support_types: list[str] = []
        if (budget_analysis.get("funding_gap_krw") or 0) > 0:
            needed_support_types.extend(["loan", "grant"])
        if assumption.rent_krw_per_month > 500_000:
            needed_support_types.append("space")
        if assumption.marketing_krw_per_month >= 300_000:
            needed_support_types.append("marketing")
        if metrics["monthly_profit_krw"] <= 0:
            needed_support_types.append("mentoring")
        if assumption.equipment_krw >= 1_000_000:
            needed_support_types.append("equipment")

        return {
            "funding_gap_krw": budget_analysis.get("funding_gap_krw"),
            "needed_support_types": self._unique(needed_support_types),
            "policy_query_keywords": self._unique(
                [
                    assumption.business_type,
                    assumption.sales_channel,
                    "초기자금",
                    "창업지원",
                    "공간지원" if assumption.rent_krw_per_month > 0 else "",
                    "마케팅지원" if assumption.marketing_krw_per_month >= 300_000 else "",
                ]
            ),
        }

    def _risks(
        self,
        profile: StartupProfile,
        assumption: FinanceAssumption,
        metrics: dict[str, Any],
        budget_analysis: dict[str, Any],
    ) -> list[str]:
        risks = []
        if metrics["monthly_profit_krw"] <= 0:
            risks.append("월 예상 이익이 0 이하라 가격, 판매량, 고정비 재조정이 필요합니다.")
        if budget_analysis["status"] == "funding_gap":
            risks.append("초기 필요 현금이 현재 예산을 초과합니다.")
        if budget_analysis["status"] == "tight":
            risks.append("시작 후 예비 현금이 적어 작은 비용 변동에도 흔들릴 수 있습니다.")
        break_even_day = metrics["break_even_units_per_day"]
        if break_even_day is not None and break_even_day > assumption.expected_daily_customers:
            risks.append("손익분기 판매량이 현재 예상 판매량보다 높습니다.")
        if assumption.rent_krw_per_month > 0 and profile.risk_tolerance == "low":
            risks.append("낮은 위험 선호도에 비해 월 임대료 부담이 있습니다.")
        if assumption.variable_cost_rate >= 0.55:
            risks.append("변동비율이 높아 할인이나 폐기 발생 시 이익이 빠르게 줄 수 있습니다.")
        return risks

    def _missing_inputs(self, profile: StartupProfile, assumption: FinanceAssumption) -> list[str]:
        missing = ["실제 원가율", "실제 판매 가능 수량", "결제/플랫폼 수수료"]
        if assumption.business_type in {"generic_bootstrap", "llm_custom"}:
            missing.append("업종별 실제 비용 구조")
        if assumption.rent_krw_per_month > 0:
            missing.append("실제 임대료")
        if profile.region is None:
            missing.append("상권별 유동인구와 임대료")
        if assumption.sales_channel in {"reservation", "online"}:
            missing.append("배송/포장 단가")
        return missing

    def _score(
        self,
        profile: StartupProfile,
        assumption: FinanceAssumption,
        metrics: dict[str, Any],
        budget_analysis: dict[str, Any],
    ) -> int:
        score = 100
        if budget_analysis["status"] == "budget_missing":
            score -= 5
        elif budget_analysis["status"] == "tight":
            score -= 15
        elif budget_analysis["status"] == "funding_gap":
            score -= 30

        if metrics["monthly_profit_krw"] <= 0:
            score -= 25

        break_even_day = metrics["break_even_units_per_day"]
        if break_even_day is None:
            score -= 30
        elif break_even_day > assumption.expected_daily_customers:
            score -= 25
        elif break_even_day > assumption.expected_daily_customers * 0.8:
            score -= 12

        revenue = max(metrics["monthly_revenue_krw"], 1)
        fixed_cost_ratio = metrics["monthly_fixed_cost_krw"] / revenue
        if fixed_cost_ratio > 0.45:
            score -= 10
        if profile.risk_tolerance == "low" and assumption.rent_krw_per_month > 0:
            score -= 8
        return max(0, min(100, score))

    def _risk_grade(self, score: int) -> str:
        if score >= 80:
            return "A"
        if score >= 60:
            return "B"
        return "C"

    def _recommendation(self, metrics: dict[str, Any], budget_analysis: dict[str, Any]) -> str:
        if budget_analysis["status"] == "funding_gap":
            return "초기 비용을 줄이는 실행안으로 축소하거나 지원사업/공간지원을 먼저 매칭하세요."
        if metrics["monthly_profit_krw"] <= 0:
            return "객단가, 판매량, 원가율 중 최소 하나를 조정한 뒤 30일 테스트를 시작하세요."
        if budget_analysis["status"] == "tight":
            return "가능은 하지만 예비 현금이 얇으니 재고와 마케팅비를 작은 단위로 쪼개 집행하세요."
        return "현재 가정에서는 30일 테스트를 시작할 수 있으니 실제 판매량과 원가율을 우선 검증하세요."

    def _assumption_notes(self, assumption: FinanceAssumption, template_key: str) -> list[str]:
        template_label = "LLM 맞춤 가정" if template_key == "llm_custom" else FINANCE_TEMPLATES.get(template_key, {}).get("label", template_key)
        return [
            f"템플릿: {template_label}",
            f"객단가 {assumption.price_per_unit_krw:,}원",
            f"예상 일 {assumption.expected_daily_customers} {assumption.unit_label}",
            f"변동비율 {assumption.variable_cost_rate:.0%}",
            f"월 운영일 {assumption.operating_days_per_month}일",
            f"예비 고정비 {assumption.cash_reserve_months}개월분 반영",
        ]

    def _calculation_basis(self, assumption: FinanceAssumption, metrics: dict[str, Any]) -> dict[str, Any]:
        return {
            "revenue_formula": "price_per_unit_krw * expected_daily_customers * operating_days_per_month",
            "monthly_units": metrics["monthly_units"],
            "variable_cost_per_unit_krw": (
                int(assumption.price_per_unit_krw * assumption.variable_cost_rate)
                + assumption.packaging_cost_krw_per_unit
                + assumption.delivery_cost_krw_per_unit
            ),
            "fixed_cost_items": {
                "rent_krw_per_month": assumption.rent_krw_per_month,
                "marketing_krw_per_month": assumption.marketing_krw_per_month,
                "labor_cost_krw_per_month": assumption.labor_cost_krw_per_month,
                "other_fixed_cost_krw_per_month": assumption.other_fixed_cost_krw_per_month,
            },
            "fee_rates": {
                "platform_fee_rate": assumption.platform_fee_rate,
                "payment_fee_rate": assumption.payment_fee_rate,
                "tax_buffer_rate": assumption.tax_buffer_rate,
            },
        }

    def _thirty_day_timeline(self, budget_analysis: dict[str, Any]) -> list[dict[str, Any]]:
        if budget_analysis["status"] == "funding_gap":
            return [
                {"day": 1, "task": "초기 비용 중 줄일 수 있는 항목과 지원사업 후보를 분리"},
                {"day": 7, "task": "무점포/공유공간/선주문 방식으로 비용 축소안 재계산"},
                {"day": 15, "task": "지원사업 또는 대체 자금 신청 가능성 확인"},
                {"day": 30, "task": "축소안 기준으로 1차 판매 테스트 여부 결정"},
            ]
        return [
            {"day": 1, "task": "필수 비용과 선택 비용을 분리하고 지출 한도 확정"},
            {"day": 7, "task": "첫 판매/문의 데이터를 기록해 예상 판매량 보정"},
            {"day": 15, "task": "원가율, 포장비, 수수료를 실제값으로 교체"},
            {"day": 30, "task": "매출, 비용, 현금잔액 기준으로 지속/축소/중단 결정"},
        ]

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            item = value.strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result
