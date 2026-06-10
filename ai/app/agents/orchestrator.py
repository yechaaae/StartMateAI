from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from app.agents.finance import FinanceAgent
from app.agents.idea import IdeaAgent
from app.agents.marketing import MarketingAgent
from app.agents.operation import OperationAgent
from app.agents.policy import PolicyAgent
from app.agents.profile import ProfileAgent
from app.agents.simulation import SimulationAgent
from app.schemas import (
    AgentResponse,
    FinanceAssumption,
    ChatRequest,
    FinanceRequest,
    IdeaRequest,
    MarketingRequest,
    OperationRequest,
    PolicyRequest,
    ProfileRequest,
    SimulationStartRequest,
)


class OrchestratorAgent:
    name = "OrchestratorAgent"

    def __init__(
        self,
        *,
        profile_agent: ProfileAgent,
        idea_agent: IdeaAgent,
        policy_agent: PolicyAgent,
        finance_agent: FinanceAgent,
        operation_agent: OperationAgent,
        marketing_agent: MarketingAgent,
        simulation_agent: SimulationAgent,
    ):
        self.profile_agent = profile_agent
        self.idea_agent = idea_agent
        self.policy_agent = policy_agent
        self.finance_agent = finance_agent
        self.operation_agent = operation_agent
        self.marketing_agent = marketing_agent
        self.simulation_agent = simulation_agent

    async def run(self, request: ChatRequest) -> AgentResponse:
        state = await self._build_orchestration_state(request)
        if state["mode"] == "collaboration":
            result = await self._collaborative_consultation(request)
            return self._annotate_response(result, state)

        await self._run_agents(state, state["plan"])
        followups = await self._plan_followups(state)
        if followups:
            state["followups"] = followups
            await self._run_agents(state, followups)

        if len(state["results"]) == 1 and not followups:
            result = next(iter(state["results"].values()))
        else:
            result = self._synthesize_selective_response(state)
        return self._annotate_response(result, state)

    def _effective_profile_from_response(
        self,
        response: AgentResponse,
        fallback_profile,
    ):
        if isinstance(response.data.get("effective_profile"), dict):
            return type(fallback_profile).model_validate(response.data["effective_profile"])
        profile_data = response.data.get("profile")
        if isinstance(profile_data, dict) and isinstance(profile_data.get("effective_profile"), dict):
            return type(fallback_profile).model_validate(profile_data["effective_profile"])
        return fallback_profile

    async def _build_orchestration_state(self, request: ChatRequest) -> dict[str, Any]:
        if request.intent == "auto":
            plan, plan_meta = await self.plan_agents(request)
        else:
            plan = ["collaboration"] if request.intent == "roadmap" else [request.intent]
            plan_meta = {"source": "explicit_intent"}

        mode = "collaboration" if plan == ["collaboration"] else "selective"
        effective_profile = None
        if mode == "selective":
            effective_profile = await self.profile_agent.build_effective_profile_async(request.profile, request.message)

        return {
            "request": request,
            "mode": mode,
            "plan": plan,
            "plan_meta": plan_meta,
            "effective_profile": effective_profile,
            "results": {},
            "followups": [],
            "followup_meta": {},
        }

    async def _run_agents(self, state: dict[str, Any], intents: list[str]) -> None:
        pending = [intent for intent in intents if intent not in state["results"]]
        if not pending:
            return
        pairs = await asyncio.gather(*(self._run_agent(state, intent) for intent in pending))
        for intent, response in pairs:
            state["results"][intent] = response

    async def _run_agent(self, state: dict[str, Any], intent: str) -> tuple[str, AgentResponse]:
        request: ChatRequest = state["request"]
        effective_profile = state["effective_profile"] or request.profile

        if intent == "profile":
            response = await self.profile_agent.run(
                ProfileRequest(profile=effective_profile, question=request.message, use_llm_extraction=False)
            )
            return intent, response
        if intent == "idea":
            return intent, await self.idea_agent.run(IdeaRequest(profile=effective_profile))
        if intent == "policy":
            query = state.get("policy_query") or request.message
            return intent, await self.policy_agent.run(
                PolicyRequest(profile=effective_profile, query=query, limit=3)
            )
        if intent == "finance":
            finance_assumption, finance_extraction = await self._finance_assumption_from_request(request)
            response = await self.finance_agent.run(
                FinanceRequest(profile=effective_profile, assumption=finance_assumption)
            )
            response.data["finance_input_extraction"] = finance_extraction
            return intent, response
        if intent == "operation":
            return intent, await self.operation_agent.run(
                OperationRequest(
                    profile=effective_profile,
                    business_name=request.context.get(
                        "business_name",
                        request.context.get("item_name", request.context.get("product_name", "테스트 매장")),
                    ),
                )
            )
        if intent == "marketing":
            return intent, await self.marketing_agent.run(
                MarketingRequest(
                    profile=effective_profile,
                    product_name=request.context.get("product_name", request.context.get("item_name", "창업 상품")),
                    event_date=request.context.get("event_date"),
                    target_customer=request.context.get("target_customer"),
                    place=request.context.get("place"),
                    brand_tone=request.context.get("brand_tone", "친근하고 실행력 있는"),
                    goal=request.message,
                )
            )
        if intent == "simulation":
            return intent, self.simulation_agent.start(self._simulation_start_request(request, effective_profile))
        return intent, await self._collaborative_consultation(request)

    async def _plan_followups(self, state: dict[str, Any]) -> list[str]:
        results: dict[str, AgentResponse] = state["results"]
        followups: list[str] = []
        finance = results.get("finance")
        if finance and "policy" not in results and self._should_follow_up_policy(finance):
            state["policy_query"] = self._policy_query_from_finance(state["request"].message, finance)
            state["followup_meta"]["policy"] = self._finance_policy_trigger_reason(finance)
            followups.append("policy")
        return self._unique(followups)

    def _synthesize_selective_response(self, state: dict[str, Any]) -> AgentResponse:
        request: ChatRequest = state["request"]
        results: dict[str, AgentResponse] = state["results"]
        selected_intents = self._unique([*state["plan"], *state.get("followups", [])])
        agent_names = [response.agent for response in results.values()]
        contracts = [self._contract_summary(response) for response in results.values()]

        data: dict[str, Any] = {
            "collaboration_mode": "selective_dynamic_agents",
            "selected_intents": selected_intents,
            "selected_agents": agent_names,
            "selection_reason": self._agent_plan_reason(
                request.message,
                selected_intents,
                state.get("plan_meta"),
                state.get("followup_meta"),
            ),
            "agent_results": {intent: response.data for intent, response in results.items()},
            "agent_contracts": contracts,
        }
        if state.get("effective_profile") is not None:
            data["effective_profile"] = state["effective_profile"].model_dump()
        for intent, response in results.items():
            data[intent] = response.data

        return AgentResponse(
            intent="selective_collaboration",
            agent=self.name,
            summary=f"{', '.join(agent_names)}만 선택해 이 질문에 필요한 범위로 검토했습니다.",
            data=data,
            next_actions=self._unique(
                [
                    action
                    for response in results.values()
                    for action in response.next_actions[:2]
                ]
            ),
            sources=[source for response in results.values() for source in response.sources],
            warnings=self._unique([warning for response in results.values() for warning in response.warnings]),
        )

    def _annotate_response(self, response: AgentResponse, state: dict[str, Any]) -> AgentResponse:
        request: ChatRequest = state["request"]
        effective_profile = state.get("effective_profile")
        if effective_profile is None:
            effective_profile = self._effective_profile_from_response(response, request.profile)
        response.data.setdefault("effective_profile", effective_profile.model_dump())
        response.data["agent_plan"] = {
            "selected_intents": state["plan"],
            "followups": state.get("followups", []),
            "planner": state.get("plan_meta"),
            "followup_meta": state.get("followup_meta", {}),
        }
        response.data["routed_by"] = self.name
        response.data["user_message"] = request.message
        return response

    def _detect_intent(self, message: str) -> str:
        return self._heuristic_agent_plan(message)[0]

    async def plan_agents(self, request: ChatRequest) -> tuple[list[str], dict[str, Any]]:
        heuristic_plan = self._heuristic_agent_plan(request.message)
        if not self.finance_agent.llm.is_enabled:
            return heuristic_plan, {
                "source": "heuristic_fallback",
                "reason": "llm_disabled",
                "heuristic_plan": heuristic_plan,
            }

        prompt = (
            "You are an agent planner for a Korean startup assistant. "
            "Choose the minimal set of agents needed to answer the user's message. "
            "Return JSON only. Do not include agents that are merely nice-to-have.\n\n"
            "Available agents:\n"
            "- profile: user constraints, strengths, readiness, missing profile info\n"
            "- idea: business idea discovery or recommendation\n"
            "- policy: government support programs, applications, permits, legal/regulatory/tax checklist until a LegalAgent exists\n"
            "- finance: budget, price, revenue, cost, margin, BEP, cash flow, feasibility\n"
            "- operation: inventory, staffing, store operations, reviews, execution process\n"
            "- marketing: SNS, reels, captions, promotion, customer acquisition\n"
            "- simulation: 30-day game-like simulation or choice-based scenario\n"
            "- collaboration: broad end-to-end consultation when the user asks for an overall plan or intent is genuinely ambiguous\n\n"
            "Rules:\n"
            "- Pick 1 agent for a narrow question.\n"
            "- Pick 2-3 agents when the user explicitly asks across multiple domains.\n"
            "- Do not pick collaboration when a smaller agent set can answer.\n"
            "- If legal, permit, report, contract, tax, or regulation is asked, include policy.\n"
            "- If budget, price, revenue, cost, profit, BEP, or feasibility is asked, include finance.\n\n"
            "Schema:\n"
            "{\n"
            '  "agents": ["finance"],\n'
            '  "confidence": "high"|"medium"|"low",\n'
            '  "reason": "short Korean reason"\n'
            "}\n\n"
            f"message: {request.message}\n"
            f"context: {json.dumps(request.context, ensure_ascii=False)}\n"
            f"profile: {json.dumps(request.profile.model_dump(), ensure_ascii=False)}"
        )
        try:
            raw = await self.finance_agent.llm.complete(
                system_prompt="You are a strict JSON planner. Return only valid JSON.",
                user_prompt=prompt,
                temperature=0.0,
                fallback="{}",
            )
            parsed = self._parse_json_object(raw)
            llm_plan = self._sanitize_agent_plan(parsed.get("agents"))
            if llm_plan:
                return llm_plan, {
                    "source": "llm_planner",
                    "confidence": parsed.get("confidence"),
                    "reason": parsed.get("reason"),
                    "raw_preview": raw[:500],
                    "heuristic_plan": heuristic_plan,
                }
            return heuristic_plan, {
                "source": "heuristic_fallback",
                "reason": "llm_plan_empty_or_invalid",
                "raw_preview": raw[:500],
                "heuristic_plan": heuristic_plan,
            }
        except Exception as error:
            return heuristic_plan, {
                "source": "heuristic_fallback",
                "reason": "llm_planner_error",
                "error_type": error.__class__.__name__,
                "error_message": str(error)[:500],
                "heuristic_plan": heuristic_plan,
            }

    def _sanitize_agent_plan(self, value: Any) -> list[str]:
        allowed = {
            "profile",
            "idea",
            "policy",
            "finance",
            "operation",
            "marketing",
            "simulation",
            "collaboration",
            "roadmap",
        }
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            name = str(item).strip().lower()
            if name in allowed and name not in result:
                result.append("collaboration" if name == "roadmap" else name)
        if "collaboration" in result and len(result) > 1:
            result = [item for item in result if item != "collaboration"]
        return result[:3]

    def _heuristic_agent_plan(self, message: str) -> list[str]:
        text = message.lower()
        plan: list[str] = []
        broad_collaboration = any(keyword in text for keyword in ["협업", "토론", "전체", "로드맵", "상담", "시작"])

        if any(keyword in text for keyword in ["지원사업", "공고", "정책", "서류", "마감"]):
            plan.append("policy")
        if any(keyword in text for keyword in ["법률", "법적", "법", "인허가", "허가", "신고", "계약", "세금", "세무"]):
            plan.append("policy")
        if any(keyword in text for keyword in ["아이템", "추천", "창업 뭐", "무슨 창업"]):
            plan.append("idea")
        if any(keyword in text for keyword in ["게임", "체험", "선택지", "30일", "이벤트"]):
            plan.append("simulation")
        if any(
            keyword in text
            for keyword in [
                "비용",
                "매출",
                "손익",
                "시뮬레이션",
                "bep",
                "재정",
                "예산",
                "객단가",
                "단가",
                "원가",
                "판매량",
                "하루",
                "월수익",
                "월 수익",
                "가능할까",
            ]
        ):
            plan.append("finance")
        if any(keyword in text for keyword in ["운영", "재고", "리뷰", "피드백", "매장"]):
            plan.append("operation")
        if any(keyword in text for keyword in ["sns", "홍보", "릴스", "게시글", "해시태그"]):
            plan.append("marketing")
        if any(keyword in text for keyword in ["프로필", "분석", "강점", "조건"]):
            plan.append("profile")

        plan = self._unique(plan)
        if not plan:
            return ["collaboration"]
        if broad_collaboration and len(plan) <= 1:
            return ["collaboration"]
        return plan

    async def _selective_consultation(
        self,
        request: ChatRequest,
        intents: list[str],
        plan_meta: dict[str, Any] | None = None,
    ) -> AgentResponse:
        state = {
            "request": request,
            "mode": "selective",
            "plan": intents,
            "plan_meta": plan_meta or {"source": "manual_selective"},
            "effective_profile": await self.profile_agent.build_effective_profile_async(request.profile, request.message),
            "results": {},
            "followups": [],
            "followup_meta": {},
        }
        await self._run_agents(state, intents)
        followups = await self._plan_followups(state)
        if followups:
            state["followups"] = followups
            await self._run_agents(state, followups)
        return self._synthesize_selective_response(state)

    def _agent_plan_reason(
        self,
        message: str,
        intents: list[str],
        plan_meta: dict[str, Any] | None = None,
        followup_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        labels = {
            "finance": "예산/매출/손익/객단가 등 재정 판단 표현",
            "policy": "지원사업/정책/법률/인허가/세무 관련 표현",
            "idea": "아이템 추천/창업 후보 탐색 표현",
            "operation": "운영/재고/리뷰/매장 관리 표현",
            "marketing": "SNS/홍보/콘텐츠 표현",
            "profile": "사용자 조건/강점/프로필 분석 표현",
            "simulation": "30일 체험/게임/선택지 표현",
        }
        return {
            "message_preview": message[:160],
            "matched": {intent: labels.get(intent, intent) for intent in intents},
            "planner": plan_meta or {"source": "unknown"},
            "followups": followup_meta or {},
        }

    def _should_follow_up_policy(self, finance_response: AgentResponse) -> bool:
        data = finance_response.data or {}
        budget = data.get("budget_analysis") or {}
        support = data.get("support_handoff") or {}
        if budget.get("status") == "funding_gap":
            return True
        if (budget.get("funding_gap_krw") or 0) > 0:
            return True
        if support.get("needed_support_types"):
            return True
        if data.get("risk_grade") == "C" and data.get("monthly_profit_krw", 0) <= 0:
            return True
        return False

    async def _finance_policy_follow_up(
        self,
        *,
        request: ChatRequest,
        effective_profile,
        finance_response: AgentResponse,
        plan_meta: dict[str, Any] | None,
        initial_plan: list[str],
    ) -> AgentResponse:
        policy_query = self._policy_query_from_finance(request.message, finance_response)
        policy_response = await self.policy_agent.run(
            PolicyRequest(profile=effective_profile, query=policy_query, limit=3)
        )
        selected_intents = self._unique([*initial_plan, "policy"])
        selected_agents = [finance_response.agent, policy_response.agent]
        contracts = [
            self._contract_summary(finance_response),
            self._contract_summary(policy_response),
        ]
        data = {
            "collaboration_mode": "result_triggered_follow_up",
            "selected_intents": selected_intents,
            "selected_agents": selected_agents,
            "selection_reason": {
                "message_preview": request.message[:160],
                "planner": plan_meta or {"source": "unknown"},
                "trigger": self._finance_policy_trigger_reason(finance_response),
            },
            "finance": finance_response.data,
            "policy": policy_response.data,
            "agent_results": {
                "finance": finance_response.data,
                "policy": policy_response.data,
            },
            "agent_contracts": contracts,
            "effective_profile": effective_profile.model_dump(),
        }
        return AgentResponse(
            intent="selective_collaboration",
            agent=self.name,
            summary=(
                "재정 검토에서 자금/지원 매칭 필요가 감지되어 FinanceAgent 결과에 PolicyAgent 검토를 이어 붙였습니다."
            ),
            data=data,
            next_actions=self._unique(
                [
                    *finance_response.next_actions[:2],
                    *policy_response.next_actions[:2],
                ]
            ),
            sources=policy_response.sources,
            warnings=self._unique([*finance_response.warnings, *policy_response.warnings]),
        )

    def _finance_policy_trigger_reason(self, finance_response: AgentResponse) -> dict[str, Any]:
        data = finance_response.data or {}
        budget = data.get("budget_analysis") or {}
        support = data.get("support_handoff") or {}
        return {
            "budget_status": budget.get("status"),
            "funding_gap_krw": budget.get("funding_gap_krw"),
            "monthly_profit_krw": data.get("monthly_profit_krw"),
            "risk_grade": data.get("risk_grade"),
            "needed_support_types": support.get("needed_support_types", []),
        }

    def _policy_query_from_finance(self, message: str, finance_response: AgentResponse) -> str:
        data = finance_response.data or {}
        support = data.get("support_handoff") or {}
        keywords = support.get("policy_query_keywords") or []
        support_types = support.get("needed_support_types") or []
        parts = [
            message,
            "재정 검토 결과 자금 또는 지원사업 매칭이 필요합니다.",
            f"필요 지원 유형: {', '.join(map(str, support_types))}" if support_types else "",
            f"검색 키워드: {', '.join(map(str, keywords))}" if keywords else "",
        ]
        return " ".join(part for part in parts if part)

    async def _finance_assumption_from_request(self, request: ChatRequest) -> tuple[FinanceAssumption, dict[str, Any]]:
        context = request.context
        rule_updates = self._finance_rule_updates(request.message)
        llm_updates, llm_meta = await self._finance_llm_updates(request)

        merged = {
            "item_name": context.get("item_name") or context.get("product_name") or "소자본 창업 아이템",
            "business_type": context.get("business_type", "auto"),
            "sales_channel": context.get("sales_channel", "auto"),
        }
        merged.update(llm_updates)
        merged.update(rule_updates)

        for key in ("item_name", "business_type", "sales_channel"):
            if context.get(key):
                merged[key] = context[key]
        if context.get("product_name") and not context.get("item_name"):
            merged["item_name"] = context["product_name"]

        valid_fields = FinanceAssumption.model_fields
        clean_updates = {key: value for key, value in merged.items() if key in valid_fields and value not in {None, ""}}
        assumption = FinanceAssumption(**clean_updates)
        return assumption, {
            "source": "llm_with_rule_fallback" if llm_updates else "rule_fallback",
            "rule_updates": rule_updates,
            "llm_updates": llm_updates,
            "llm_meta": llm_meta,
            "final_assumption": assumption.model_dump(),
        }

    async def _finance_llm_updates(self, request: ChatRequest) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.finance_agent.llm.is_enabled:
            return {}, {"attempted": False, "reason": "llm_disabled"}

        prompt = (
            "Extract explicit or strongly implied financial assumptions from the Korean startup consultation message. "
            "Return JSON only. Do not explain. Use null for unknown values. Prefer exact numbers mentioned by the user. "
            "Infer business_type and sales_channel only when the wording clearly implies them.\n\n"
            "Allowed business_type values: auto, popup, reservation_food, sns_service, local_service, ecommerce, offline_store.\n"
            "Allowed sales_channel values: auto, direct, online, offline, reservation, service.\n\n"
            "Schema:\n"
            "{\n"
            '  "item_name": string|null,\n'
            '  "business_type": string|null,\n'
            '  "sales_channel": string|null,\n'
            '  "unit_label": string|null,\n'
            '  "price_per_unit_krw": number|null,\n'
            '  "expected_daily_customers": number|null,\n'
            '  "operating_days_per_month": number|null,\n'
            '  "rent_krw_per_month": number|null,\n'
            '  "equipment_krw": number|null,\n'
            '  "initial_inventory_krw": number|null,\n'
            '  "marketing_krw_per_month": number|null,\n'
            '  "variable_cost_rate": number|null,\n'
            '  "platform_fee_rate": number|null,\n'
            '  "payment_fee_rate": number|null,\n'
            '  "reason": string|null\n'
            "}\n\n"
            f"message: {request.message}\n"
            f"context: {json.dumps(request.context, ensure_ascii=False)}\n"
            f"profile: {json.dumps(request.profile.model_dump(), ensure_ascii=False)}"
        )
        meta: dict[str, Any] = {"attempted": True}
        try:
            raw = await self.finance_agent.llm.complete(
                system_prompt="You are a strict JSON extraction engine for startup finance assumptions.",
                user_prompt=prompt,
                temperature=0.0,
                fallback="{}",
            )
            meta["raw_preview"] = raw[:500]
            parsed = self._parse_json_object(raw)
            updates = self._sanitize_finance_extraction(parsed)
            meta["parsed_keys"] = sorted(parsed) if isinstance(parsed, dict) else []
            meta["sanitized_fields"] = sorted(updates)
            if isinstance(parsed, dict) and parsed.get("reason"):
                meta["reason"] = str(parsed["reason"])[:300]
            return updates, meta
        except Exception as error:
            meta["error_type"] = error.__class__.__name__
            meta["error_message"] = str(error)[:500]
            return {}, meta

    def _finance_rule_updates(self, message: str) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        item_name = self._extract_finance_item_name(message)
        if item_name:
            updates["item_name"] = item_name

        price = self._extract_krw_near(message, ["객단가", "가격", "단가", "판매가"])
        if price is not None:
            updates["price_per_unit_krw"] = price

        daily_customers = self._extract_daily_customers(message)
        if daily_customers is not None:
            updates["expected_daily_customers"] = daily_customers

        business_type = self._infer_finance_business_type(message)
        if business_type != "auto":
            updates["business_type"] = business_type

        sales_channel = self._infer_finance_sales_channel(message)
        if sales_channel != "auto":
            updates["sales_channel"] = sales_channel

        return updates

    def _sanitize_finance_extraction(self, parsed: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parsed, dict):
            return {}

        updates: dict[str, Any] = {}
        text_fields = {"item_name": 80, "business_type": 40, "sales_channel": 40}
        int_fields = {
            "price_per_unit_krw": (100, 5_000_000),
            "expected_daily_customers": (1, 1_000),
            "operating_days_per_month": (1, 31),
            "rent_krw_per_month": (0, 10_000_000),
            "equipment_krw": (0, 20_000_000),
            "initial_inventory_krw": (0, 20_000_000),
            "marketing_krw_per_month": (0, 5_000_000),
        }
        rate_fields = {
            "variable_cost_rate": (0.0, 1.0),
            "platform_fee_rate": (0.0, 1.0),
            "payment_fee_rate": (0.0, 1.0),
        }

        for field, limit in text_fields.items():
            value = parsed.get(field)
            if isinstance(value, str) and value.strip():
                updates[field] = value.strip()[:limit]

        if updates.get("business_type") not in {
            None,
            "auto",
            "popup",
            "reservation_food",
            "sns_service",
            "local_service",
            "ecommerce",
            "offline_store",
        }:
            updates.pop("business_type", None)
        if updates.get("sales_channel") not in {None, "auto", "direct", "online", "offline", "reservation", "service"}:
            updates.pop("sales_channel", None)

        for field, value_range in int_fields.items():
            value = self._coerce_int(parsed.get(field))
            if value is not None and value_range[0] <= value <= value_range[1]:
                updates[field] = value

        for field, value_range in rate_fields.items():
            value = self._coerce_rate(parsed.get(field))
            if value is not None and value_range[0] <= value <= value_range[1]:
                updates[field] = value

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

    def _extract_finance_item_name(self, message: str) -> str:
        patterns = [
            r"예산\s*[0-9,억천백만원\s]+으로\s*(.+?)(?:을|를)\s*(?:해보고|하고|팔고|판매)",
            r"(.+?)(?:을|를)\s*(?:해보고|하고|팔고|판매)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1).strip(" .,!?\n\t")
        return ""

    def _infer_finance_business_type(self, message: str) -> str:
        text = message.lower()
        if "팝업" in text:
            return "popup"
        if any(keyword in text for keyword in ["쿠키", "디저트", "음식", "도시락", "예약"]):
            return "reservation_food"
        if any(keyword in text for keyword in ["온라인", "쇼핑몰", "커머스"]):
            return "ecommerce"
        if any(keyword in text for keyword in ["카페", "매장", "오프라인"]):
            return "offline_store"
        return "auto"

    def _infer_finance_sales_channel(self, message: str) -> str:
        text = message.lower()
        if "팝업" in text or "오프라인" in text or "매장" in text:
            return "offline"
        if "온라인" in text or "쇼핑몰" in text:
            return "online"
        if "예약" in text:
            return "reservation"
        return "auto"

    def _extract_krw_near(self, message: str, labels: list[str]) -> int | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        patterns = [
            rf"(?:{label_pattern})[^\d]*(\d[\d,]*)\s*원?",
            rf"(\d[\d,]*)\s*원?\s*(?:정도)?(?:의)?\s*(?:{label_pattern})",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    def _extract_daily_customers(self, message: str) -> int | None:
        patterns = [
            r"하루\s*(\d[\d,]*)\s*(?:명|개|건|팀|주문)",
            r"일\s*(\d[\d,]*)\s*(?:명|개|건|팀|주문)",
            r"(\d[\d,]*)\s*(?:명|개|건|팀|주문)\s*정도\s*(?:팔|판매|올)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    def _coerce_int(self, value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value).replace(",", "").strip()
        match = re.search(r"\d+(?:\.\d+)?", text)
        if not match:
            return None
        return int(float(match.group(0)))

    def _coerce_rate(self, value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            number = float(value)
        else:
            text = str(value).strip()
            match = re.search(r"\d+(?:\.\d+)?", text)
            if not match:
                return None
            number = float(match.group(0))
            if "%" in text:
                number /= 100
        if number > 1:
            number /= 100
        return number

    def _simulation_start_request(self, request: ChatRequest, profile=None) -> SimulationStartRequest:
        business_type = request.context.get("business_type", "content")
        if business_type not in {"cafe", "commerce", "content", "popup", "service"}:
            business_type = "content"
        difficulty = request.context.get("difficulty", "normal")
        if difficulty not in {"easy", "normal", "hard"}:
            difficulty = "normal"
        return SimulationStartRequest(
            profile=profile or request.profile,
            item_name=request.context.get("item_name", "로컬 SNS 콘텐츠 스튜디오"),
            business_type=business_type,
            difficulty=difficulty,
            seed=request.context.get("seed"),
        )

    async def _collaborative_consultation(self, request: ChatRequest) -> AgentResponse:
        effective_profile = await self.profile_agent.build_effective_profile_async(request.profile, request.message)
        profile_task = self.profile_agent.run(
            ProfileRequest(profile=effective_profile, question=request.message, use_llm_extraction=False)
        )
        ideas_task = self.idea_agent.run(IdeaRequest(profile=effective_profile, count=3))
        policies_task = self.policy_agent.run(PolicyRequest(profile=effective_profile, query=request.message, limit=3))
        profile, ideas, policies = await asyncio.gather(profile_task, ideas_task, policies_task)

        top_idea = self._pick_top_idea(ideas)
        top_idea_name = str(top_idea.get("title", "창업 아이템"))
        round1_synthesis = self._build_round1_synthesis(profile, ideas, policies)

        finance_task = self.finance_agent.run(
            FinanceRequest(
                profile=effective_profile,
                assumption=FinanceAssumption(item_name=top_idea_name),
            )
        )
        marketing_task = self.marketing_agent.run(
            MarketingRequest(
                profile=effective_profile,
                product_name=top_idea_name,
                target_customer=request.context.get("target_customer"),
                place=request.context.get("place"),
                brand_tone=request.context.get("brand_tone", "친근하고 실행력 있는"),
                goal=request.message,
            )
        )
        operation_task = self.operation_agent.run(
            OperationRequest(profile=effective_profile, business_name=top_idea_name)
        )
        finance, marketing, operation = await asyncio.gather(finance_task, marketing_task, operation_task)

        data = {
            "collaboration_mode": "parallel_multi_agent",
            "rounds": [
                {
                    "round": 1,
                    "agents": ["ProfileAgent", "IdeaAgent", "PolicyAgent"],
                    "purpose": "사용자 조건, 아이템 후보, 지원사업 가능성을 동시에 검토",
                },
                {
                    "round": 2,
                    "agents": ["FinanceAgent", "MarketingAgent", "OperationAgent"],
                    "purpose": "선정 후보의 비용, 홍보, 운영 리스크를 동시에 검증",
                },
            ],
            "selected_idea": top_idea,
            "round1_synthesis": round1_synthesis,
            "profile": profile.data,
            "ideas": ideas.data.get("recommendations", []),
            "policies": policies.data.get("matches", []),
            "finance": finance.data,
            "marketing": marketing.data,
            "operation": operation.data,
            "agent_contracts": [
                self._contract_summary(profile),
                self._contract_summary(ideas),
                self._contract_summary(policies),
                self._contract_summary(finance),
                self._contract_summary(marketing),
                self._contract_summary(operation),
            ],
            "debate": self._build_debate(profile, ideas, policies, finance, marketing, operation),
            "recommended_flow": [
                "프로필 제약조건 확정",
                f"{top_idea_name} 기준 30일 테스트 설계",
                "초기 현금 필요액과 손익분기점 재검산",
                "지원사업 상위 후보 신청 가능성 확인",
                "SNS 홍보 소재 제작 후 고객 반응 측정",
            ],
        }
        return AgentResponse(
            intent="collaboration",
            agent=self.name,
            summary=(
                "여러 전문 에이전트가 동시에 후보를 검토한 뒤, 실행 가능성과 리스크를 기준으로 "
                f"{top_idea_name} 중심의 실행안을 합의했습니다."
            ),
            data=data,
            next_actions=[
                "선정 아이템의 실제 고객 5명을 인터뷰",
                "임대료, 예상 방문자 수, 객단가를 실제 값으로 입력",
                "지원사업 상위 후보의 신청 서류 체크리스트 작성",
                "SNS 테스트 콘텐츠 1개를 제작해 반응 측정",
            ],
            sources=policies.sources,
            warnings=policies.warnings,
        )

    def _pick_top_idea(self, ideas: AgentResponse) -> dict[str, object]:
        recommendations = ideas.data.get("recommendations", [])
        if recommendations:
            return recommendations[0]
        return {"title": "창업 아이템", "match_score": 0, "difficulty": "확인 필요"}

    def _pick_top_policy(self, policies: AgentResponse) -> dict[str, object] | None:
        matches = policies.data.get("matches", [])
        if matches:
            return matches[0]
        return None

    def _build_round1_synthesis(
        self,
        profile: AgentResponse,
        ideas: AgentResponse,
        policies: AgentResponse,
    ) -> dict[str, object]:
        top_idea = self._pick_top_idea(ideas)
        top_policy = self._pick_top_policy(policies)
        profile_summary = profile.data.get("profile_summary", {})
        idea_score = int(top_idea.get("match_score", 0))
        policy_score = int(top_policy.get("eligibility_score", 0)) if top_policy else 0

        missing_inputs = self._unique(
            [
                *profile.data.get("missing_inputs", []),
                *ideas.data.get("missing_inputs", []),
                *policies.data.get("missing_inputs", []),
            ]
        )
        tensions = self._round1_tensions(profile, top_idea, top_policy)
        top_policy_title = top_policy.get("title") if top_policy else "지원사업 후보 없음"

        return {
            "round": 1,
            "purpose": "사용자 조건, 아이템 후보, 지원사업 가능성을 동시에 검토하고 2라운드 검증 대상을 정합니다.",
            "selected_direction": {
                "idea_title": top_idea.get("title"),
                "policy_title": top_policy_title,
                "decision": f"{top_idea.get('title')}을 기준 아이템으로 잡고 {top_policy_title} 매칭 가능성을 함께 확인합니다.",
            },
            "agent_votes": [
                {
                    "agent": profile.agent,
                    "vote": profile.data.get("recommendation"),
                    "score": profile.data.get("score"),
                    "basis": profile.data.get("position"),
                },
                {
                    "agent": ideas.agent,
                    "vote": top_idea.get("title"),
                    "score": idea_score,
                    "basis": top_idea.get("why_recommended", []),
                },
                {
                    "agent": policies.agent,
                    "vote": top_policy_title,
                    "score": policy_score,
                    "basis": top_policy.get("why_matched", []) if top_policy else [],
                },
            ],
            "profile_snapshot": {
                "user_type": profile_summary.get("user_type"),
                "budget_krw": profile_summary.get("budget_krw"),
                "risk_tolerance": profile_summary.get("risk_tolerance"),
                "capability_tags": profile_summary.get("capability_tags", []),
            },
            "top_idea": {
                "title": top_idea.get("title"),
                "match_score": idea_score,
                "score_breakdown": top_idea.get("score_breakdown", {}),
                "matched_keywords": top_idea.get("matched_keywords", []),
                "why_recommended": top_idea.get("why_recommended", []),
                "first_30_days": top_idea.get("first_30_days", []),
                "risks": top_idea.get("risks", []),
            },
            "top_policy": self._round1_policy_snapshot(top_policy),
            "round1_scores": {
                "ProfileAgent": profile.data.get("score"),
                "IdeaAgent": idea_score,
                "PolicyAgent": policy_score,
            },
            "agreement": [
                "ProfileAgent는 소자본/저위험 조건상 고정비가 낮은 검증형 아이템을 우선해야 한다고 봅니다.",
                f"IdeaAgent는 {top_idea.get('title')}의 경험/관심/채널 적합도가 가장 높다고 봅니다.",
                f"PolicyAgent는 {top_policy_title}을 통해 초기 비용 부담을 낮출 가능성을 봅니다.",
            ],
            "tensions": tensions,
            "missing_inputs": missing_inputs,
            "handoff_to_round2": [
                "FinanceAgent가 기준 아이템의 초기 현금 필요액과 손익분기점을 검증합니다.",
                "MarketingAgent가 SNS 반응 테스트용 메시지와 업로드 일정을 만듭니다.",
                "OperationAgent가 30일 테스트 이후 추적할 운영 지표를 정리합니다.",
            ],
        }

    def _round1_policy_snapshot(self, top_policy: dict[str, object] | None) -> dict[str, object] | None:
        if not top_policy:
            return None
        return {
            "title": top_policy.get("title"),
            "eligibility_score": top_policy.get("eligibility_score"),
            "fit_level": top_policy.get("fit_level"),
            "score_breakdown": top_policy.get("score_breakdown", {}),
            "retrieval": top_policy.get("retrieval", {}),
            "source_chunks": top_policy.get("source_chunks", []),
            "matched_keywords": top_policy.get("matched_keywords", []),
            "why_matched": top_policy.get("why_matched", []),
            "eligibility_gaps": top_policy.get("eligibility_gaps", []),
            "required_documents": top_policy.get("required_documents", []),
            "application_strategy": top_policy.get("application_strategy", []),
        }

    def _round1_tensions(
        self,
        profile: AgentResponse,
        top_idea: dict[str, object],
        top_policy: dict[str, object] | None,
    ) -> list[dict[str, object]]:
        tensions: list[dict[str, object]] = []
        budget_fit = int(top_idea.get("score_breakdown", {}).get("budget_fit", 100))
        if budget_fit < 75:
            tensions.append(
                {
                    "issue": "아이디어 매력도는 높지만 초기 예산 적합도가 낮습니다.",
                    "resolution": "2라운드 FinanceAgent가 임대/재고 없는 30일 테스트 비용으로 다시 검증합니다.",
                }
            )
        policy_gaps = top_policy.get("eligibility_gaps", []) if top_policy else []
        if policy_gaps:
            tensions.append(
                {
                    "issue": "지원사업 후보는 있지만 자격/서류 확인 항목이 남아 있습니다.",
                    "resolution": "사업계획서 초안과 지역/활동 증빙을 먼저 준비하고 실제 공고에서 마감일을 재확인합니다.",
                    "gaps": policy_gaps[:3],
                }
            )
        if profile.data.get("risks"):
            tensions.append(
                {
                    "issue": "사용자 제약조건이 아이템 선택 폭을 줄입니다.",
                    "resolution": "저비용 검증, 선주문, 포트폴리오형 서비스처럼 고정비를 미루는 방식으로 시작합니다.",
                }
            )
        return tensions or [
            {
                "issue": "Round 1 에이전트 간 큰 충돌 없음",
                "resolution": "선정 아이템을 바로 2라운드 실행 검증으로 넘깁니다.",
            }
        ]

    def _unique(self, values: list[object]) -> list[str]:
        seen = set()
        result: list[str] = []
        for value in values:
            item = str(value).strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _contract_summary(self, response: AgentResponse) -> dict[str, object]:
        return {
            "agent": response.agent,
            "position": response.data.get("position"),
            "score": response.data.get("score"),
            "risks": response.data.get("risks", []),
            "missing_inputs": response.data.get("missing_inputs", []),
            "recommendation": response.data.get("recommendation"),
        }

    def _debate_item(
        self,
        response: AgentResponse,
        *,
        fallback_position: str,
        fallback_evidence: object,
    ) -> dict[str, object]:
        return {
            "agent": response.agent,
            "position": response.data.get("position", fallback_position),
            "evidence": response.data.get("evidence", fallback_evidence),
            "score": response.data.get("score"),
            "risks": response.data.get("risks", []),
            "recommendation": response.data.get("recommendation"),
        }

    def _build_debate(
        self,
        profile: AgentResponse,
        ideas: AgentResponse,
        policies: AgentResponse,
        finance: AgentResponse,
        marketing: AgentResponse,
        operation: AgentResponse,
    ) -> dict[str, object]:
        selected = self._pick_top_idea(ideas)
        selected_name = selected.get("title", "창업 아이템")
        finance_data = finance.data
        policy_matches = policies.data.get("matches", [])
        top_policy = policy_matches[0]["title"] if policy_matches else "지원사업 후보 없음"

        return {
            "process": [
                {
                    "step": "1차 의견 수집",
                    "description": "ProfileAgent, IdeaAgent, PolicyAgent가 동시에 사용자 조건, 아이템 후보, 지원사업 가능성을 검토합니다.",
                    "agents": ["ProfileAgent", "IdeaAgent", "PolicyAgent"],
                },
                {
                    "step": "후보 압축",
                    "description": f"IdeaAgent의 1순위 후보인 {selected_name}을 기준 아이템으로 선택합니다.",
                    "agents": ["OrchestratorAgent", "IdeaAgent"],
                },
                {
                    "step": "2차 검증",
                    "description": "FinanceAgent, MarketingAgent, OperationAgent가 기준 아이템의 비용, 홍보, 운영 리스크를 동시에 검증합니다.",
                    "agents": ["FinanceAgent", "MarketingAgent", "OperationAgent"],
                },
                {
                    "step": "충돌 조정",
                    "description": "추천 매력도와 초기 현금 부담, 지원사업 준비와 빠른 시장 검증 사이의 충돌을 조정합니다.",
                    "agents": ["OrchestratorAgent"],
                },
                {
                    "step": "최종 합의",
                    "description": f"{selected_name}을 1순위로 두고 비용 검증, 지원사업 매칭, SNS 반응 테스트를 병렬 실행하는 전략으로 합의합니다.",
                    "agents": ["OrchestratorAgent"],
                },
            ],
            "agent_positions": [
                self._debate_item(
                    profile,
                    fallback_position="사용자 조건과 제약을 먼저 고정해야 추천 품질이 올라갑니다.",
                    fallback_evidence=profile.data.get("constraints", []),
                ),
                self._debate_item(
                    ideas,
                    fallback_position=f"{selected_name}이 현재 조건에서 가장 실행 가능성이 높습니다.",
                    fallback_evidence=selected,
                ),
                self._debate_item(
                    policies,
                    fallback_position="초기 비용 부담은 지원사업 매칭으로 낮출 수 있습니다.",
                    fallback_evidence=top_policy,
                ),
                self._debate_item(
                    finance,
                    fallback_position="고정비와 손익분기 판매량이 핵심 검증 포인트입니다.",
                    fallback_evidence={
                        "initial_cash_needed_krw": finance_data.get("initial_cash_needed_krw"),
                        "break_even_units_per_day": finance_data.get("break_even_units_per_day"),
                        "risk_grade": finance_data.get("risk_grade"),
                    },
                ),
                self._debate_item(
                    marketing,
                    fallback_position="초기 고객 반응은 SNS 콘텐츠 테스트로 빠르게 확인해야 합니다.",
                    fallback_evidence=marketing.data.get("upload_schedule", []),
                ),
                self._debate_item(
                    operation,
                    fallback_position="창업 후에는 매출, 재고, 리뷰를 주간 단위로 다시 학습해야 합니다.",
                    fallback_evidence=operation.data.get("next_week_plan", []),
                ),
            ],
            "conflicts": [
                {
                    "issue": "추천 아이템의 매력도 vs 초기 현금 부담",
                    "resolution": "선정 아이템은 유지하되, 임대/재고 부담이 생기는 실행안은 30일 테스트 이후로 미룬다.",
                },
                {
                    "issue": "지원사업 신청 준비 vs 빠른 시장 검증",
                    "resolution": "지원사업 서류 준비와 SNS 고객 반응 테스트를 병렬로 진행한다.",
                },
            ],
            "orchestrator_decision": (
                f"1순위 아이템은 {selected_name}입니다. 비용 검증, 지원사업 매칭, SNS 반응 테스트를 "
                "동시에 실행하는 것이 현재 가장 현실적인 전략입니다."
            ),
        }
