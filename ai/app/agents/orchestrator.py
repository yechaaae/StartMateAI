from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Awaitable, Callable

from app.agents.finance import FinanceAgent
from app.agents.idea import IdeaAgent
from app.agents.legal import LegalAgent
from app.agents.marketing import MarketingAgent
from app.agents.commercial_area import CommercialAreaAgent
from app.agents.operation import OperationAgent
from app.agents.plan import PlanAgent
from app.agents.policy import PolicyAgent
from app.agents.profile import ProfileAgent
from app.agents.simulation import SimulationAgent
from app.feature_reports import (
    FEATURE_REPORT_TEAMS,
    FEATURE_REVIEW_FEATURES,
    build_feature_result,
    feature_key_from_request,
)
from app.schemas import (
    AgentResponse,
    FinanceAssumption,
    ChatRequest,
    CommercialAreaRequest,
    FinanceRequest,
    IdeaRequest,
    LegalRequest,
    MarketingRequest,
    OperationMetric,
    OperationRequest,
    PlanRequest,
    PolicyRequest,
    ProfileRequest,
    SimulationStartRequest,
)

AgentProgressCallback = Callable[[dict[str, Any]], Awaitable[None]]
LOGGER = logging.getLogger(__name__)

# --- 데모 pacing -----------------------------------------------------------
# 해커톤 시연용: 응답이 즉시 끝나더라도 Agent들이 "고민하며 의견을 맞추는" 것처럼
# 보이도록 진행 이벤트(narration)에 최소 간격과 최소 사고 시간을 부여한다.
# 실제 작업으로 이미 충분히 벌어진 간격은 그대로 두고, 한 번에 쏟아지는 버스트만
# 펼쳐 주기 때문에 실제 LLM 응답 지연은 거의 늘지 않는다. (둘 다 0으로 두면 비활성화)
PROGRESS_MIN_GAP_SECONDS = float(os.getenv("AGENT_PROGRESS_MIN_GAP_SECONDS", "0.5"))
AGENT_MIN_THINK_SECONDS = float(os.getenv("AGENT_MIN_THINK_SECONDS", "0.9"))


class OrchestratorAgent:
    name = "OrchestratorAgent"

    def __init__(
        self,
        *,
        profile_agent: ProfileAgent,
        idea_agent: IdeaAgent,
        policy_agent: PolicyAgent,
        legal_agent: LegalAgent,
        finance_agent: FinanceAgent,
        operation_agent: OperationAgent,
        plan_agent: PlanAgent,
        marketing_agent: MarketingAgent,
        commercial_area_agent: CommercialAreaAgent,
        simulation_agent: SimulationAgent,
    ):
        self.profile_agent = profile_agent
        self.idea_agent = idea_agent
        self.policy_agent = policy_agent
        self.legal_agent = legal_agent
        self.finance_agent = finance_agent
        self.operation_agent = operation_agent
        self.plan_agent = plan_agent
        self.marketing_agent = marketing_agent
        self.commercial_area_agent = commercial_area_agent
        self.simulation_agent = simulation_agent

    async def run(
        self,
        request: ChatRequest,
        progress_callback: AgentProgressCallback | None = None,
    ) -> AgentResponse:
        state = await self._build_orchestration_state(request)
        state["progress_callback"] = progress_callback
        await self._emit_progress(
            state,
            "agents.selected",
            self._selected_agents_message(state),
            selected_intents=self._selected_intents_for_progress(state),
        )

        if state["mode"] == "collaboration":
            result = await self._collaborative_consultation(request, state)
            result = self._annotate_response(result, state)
            result = self._attach_feature_result(result, state)
            await self._emit_progress(
                state,
                "orchestrator.completed",
                "Agent들 의견까지 맞춰봤어요. 이제 정리해서 답할게요.",
                agent_status="completed",
                status="COMPLETED",
            )
            return result

        await self._run_agents(state, state["plan"])
        followups = await self._plan_followups(state)
        if followups:
            state["followups"] = followups
            await self._emit_progress(
                state,
                "agents.selected",
                self._selected_agents_message(state),
                selected_intents=self._selected_intents_for_progress(state),
            )
            await self._run_agents(state, followups)

        if len(state["results"]) > 1:
            state["debate_rounds"] = await self._run_debate_round(state)
        if self._should_run_feature_report_review(state):
            await self._run_feature_report_review(state)

        if len(state["results"]) == 1 and not followups:
            result = next(iter(state["results"].values()))
        else:
            result = self._synthesize_selective_response(state)
        result = self._annotate_response(result, state)
        result = self._attach_feature_result(result, state)
        await self._emit_progress(
            state,
            "orchestrator.completed",
            "Agent들 의견까지 맞춰봤어요. 이제 정리해서 답할게요.",
            agent_status="completed",
            status="COMPLETED",
        )
        return result

    async def _emit_progress(
        self,
        state: dict[str, Any],
        event_type: str,
        message: str,
        *,
        agent_intent: str = "orchestrator",
        agent_status: str = "running",
        selected_intents: list[str] | None = None,
        status: str = "PROCESSING",
        view_type: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        callback = state.get("progress_callback")
        if callback is None:
            return

        event = {
            "eventType": event_type,
            "type": view_type or self._progress_view_type(event_type, agent_intent, agent_status),
            "orchestrator": self.name,
            "status": status,
            "message": message,
            "agent": self._agent_descriptor(agent_intent, agent_status),
        }
        if detail:
            event["detail"] = detail
        if selected_intents is not None:
            event["selectedAgents"] = [
                self._agent_descriptor(intent, "queued")
                for intent in selected_intents
            ]

        lock = state.get("progress_lock")
        try:
            if lock is None:
                await callback(event)
            else:
                # 락으로 narration을 직렬화해, 병렬 Agent들의 이벤트가 한 프레임에
                # 몰려 그려지지 않고 단계별로 하나씩 노출되게 한다.
                async with lock:
                    await self._pace_before_emit(state)
                    await callback(event)
                    state["progress_last_at"] = time.monotonic()
        except Exception as error:  # noqa: BLE001 - progress events should not fail the final chat answer.
            LOGGER.warning("Failed to publish agent progress event: %s", error)

    async def _pace_before_emit(self, state: dict[str, Any]) -> None:
        """직전 narration 이벤트와 최소 간격을 보장한다.

        실제 작업으로 이미 충분히 벌어진 간격은 그대로 두고, 토론/시작 알림처럼
        한꺼번에 쏟아지는 버스트만 펼쳐서 단계가 하나씩 보이도록 한다.
        """
        if PROGRESS_MIN_GAP_SECONDS <= 0:
            return
        last = state.get("progress_last_at")
        if last is None:
            return
        wait = PROGRESS_MIN_GAP_SECONDS - (time.monotonic() - last)
        if wait > 0:
            await asyncio.sleep(wait)

    async def _think_dwell(self, started_at: float) -> None:
        """실제 검토가 즉시 끝나도 Agent가 잠시 '고민'한 것처럼 보이게 한다."""
        if AGENT_MIN_THINK_SECONDS <= 0:
            return
        remaining = AGENT_MIN_THINK_SECONDS - (time.monotonic() - started_at)
        if remaining > 0:
            await asyncio.sleep(remaining)

    def _progress_view_type(self, event_type: str, agent_intent: str, agent_status: str) -> str:
        if event_type in {"orchestrator.started", "agents.selected", "agent.started", "orchestrator.completed"}:
            return "status"
        if event_type == "agent.completed":
            return "result"
        if event_type == "agent.argument":
            return "argument"
        if event_type == "agent.challenge":
            return "challenge"
        if event_type == "agent.revision":
            return "revision"
        if event_type == "orchestrator.consensus":
            return "consensus"
        if event_type == "orchestrator.synthesizing":
            return "discussion"
        if event_type == "agent.failed" or agent_status == "failed":
            return "status"
        if agent_intent == "orchestrator":
            return "discussion"
        return "discussion"

    def _agent_descriptor(self, intent: str, status: str) -> dict[str, str]:
        descriptors = {
            "orchestrator": ("OrchestratorAgent", "Orchestrator", "Agent 의견 조율"),
            "profile": ("ProfileAgent", "프로필 Agent", "사용자 조건 분석"),
            "idea": ("IdeaAgent", "아이디어 Agent", "아이템 후보 탐색"),
            "policy": ("PolicyAgent", "지원사업 Agent", "지원사업 추천"),
            "plan": ("PlanAgent", "사업계획 Agent", "사업계획서 초안 작성"),
            "legal": ("LegalAgent", "법률 Agent", "체크리스트 검토"),
            "finance": ("FinanceAgent", "재무 Agent", "비용/손익 검토"),
            "operation": ("OperationAgent", "운영 Agent", "운영 리스크 검토"),
            "marketing": ("MarketingAgent", "마케팅 Agent", "홍보 실행 검토"),
            "commercial_area": ("CommercialAreaAgent", "상권 Agent", "입지/경쟁점 분석"),
            "simulation": ("SimulationAgent", "시뮬레이션 Agent", "창업 시뮬레이션"),
        }
        agent_key, label, role = descriptors.get(intent, (f"{intent.title()}Agent", intent, "Agent 검토"))
        return {
            "agentKey": agent_key,
            "label": label,
            "role": role,
            "status": status,
        }

    def _selected_intents_for_progress(self, state: dict[str, Any]) -> list[str]:
        if state.get("mode") == "collaboration":
            return ["profile", "idea", "policy", "finance", "marketing", "operation"]
        return self._unique([*state.get("plan", []), *state.get("followups", [])])

    def _selected_agents_message(self, state: dict[str, Any]) -> str:
        labels = [self._agent_descriptor(intent, "queued")["label"] for intent in self._selected_intents_for_progress(state)]
        if not labels:
            return "잠깐만요. 어떤 Agent가 들어오면 좋을지 먼저 볼게요."
        return f"이번엔 {', '.join(labels)}가 같이 들어와서 서로 의견을 맞춰볼게요."

    def _agent_started_message(self, intent: str) -> str:
        descriptor = self._agent_descriptor(intent, "running")
        return f"{descriptor['label']}가 {descriptor['role']} 쪽 근거를 먼저 살펴보고 있어요."

    def _agent_completed_message(self, response: AgentResponse) -> str:
        summary = (response.summary or "").strip()
        if not summary:
            return f"{response.agent}는 아직 확정 의견을 내기 어렵다고 봅니다."
        message = self._discussion_prefix(response.agent, summary)
        evidence_lines = self._agent_evidence_lines(response)
        if evidence_lines:
            message += "\n\n판단 근거\n" + "\n".join(f"- {line}" for line in evidence_lines[:5])
        return message

    def _agent_short_position(self, response: AgentResponse) -> str:
        data = response.data or {}
        text = str(data.get("position") or response.summary or "").strip()
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        sentences = re.split(r"(?<=[.!?。！？])\s+", text)
        compact = sentences[0].strip() if sentences else text
        if len(compact) > 180:
            compact = compact[:177].rstrip() + "..."
        return compact

    def _agent_progress_detail(self, response: AgentResponse) -> dict[str, Any]:
        data = response.data or {}
        return {
            "position": data.get("position"),
            "score": data.get("score"),
            "evidence": data.get("evidence"),
            "risks": data.get("risks", [])[:3] if isinstance(data.get("risks"), list) else [],
            "missingInputs": data.get("missing_inputs", [])[:3] if isinstance(data.get("missing_inputs"), list) else [],
            "recommendation": data.get("recommendation"),
        }

    def _discussion_prefix(self, agent: str, summary: str) -> str:
        labels = {
            "ProfileAgent": "프로필 관점에서는",
            "IdeaAgent": "아이디어 관점에서는",
            "PolicyAgent": "지원사업 관점에서는",
            "LegalAgent": "법률 관점에서는",
            "FinanceAgent": "재무 관점에서는",
            "OperationAgent": "운영 관점에서는",
            "MarketingAgent": "마케팅 관점에서는",
            "CommercialAreaAgent": "상권 관점에서는",
            "SimulationAgent": "시뮬레이션 관점에서는",
        }
        prefix = labels.get(agent)
        if not prefix or summary.startswith(prefix):
            return summary
        return f"{prefix} {summary}"

    def _agent_evidence_lines(self, response: AgentResponse) -> list[str]:
        data = response.data or {}
        lines: list[str] = []
        score = data.get("score")
        if isinstance(score, (int, float)):
            lines.append(f"검토 점수 {int(score)}점")

        lines.extend(self._agent_specific_evidence(response.agent, data))

        evidence = data.get("evidence")
        lines.extend(self._flatten_evidence(evidence))

        recommendation = data.get("recommendation")
        if isinstance(recommendation, str) and recommendation.strip():
            lines.append(f"권장 방향: {recommendation.strip()}")

        risks = data.get("risks")
        if isinstance(risks, list):
            for risk in risks[:2]:
                if isinstance(risk, str) and risk.strip():
                    lines.append(f"주의 신호: {risk.strip()}")

        return self._unique_compact(lines, limit=7)

    def _agent_specific_evidence(self, agent: str, data: dict[str, Any]) -> list[str]:
        if agent == "FinanceAgent":
            return self._finance_evidence(data)
        if agent == "OperationAgent":
            return self._operation_evidence(data)
        if agent == "PolicyAgent":
            return self._policy_evidence(data)
        if agent == "LegalAgent":
            return self._legal_evidence(data)
        if agent == "CommercialAreaAgent":
            return self._commercial_area_evidence(data)
        if agent == "MarketingAgent":
            return self._marketing_evidence(data)
        if agent == "IdeaAgent":
            return self._idea_evidence(data)
        if agent == "ProfileAgent":
            return self._profile_evidence(data)
        return []

    def _finance_evidence(self, data: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        for key, label, suffix in [
            ("initial_cash_needed_krw", "초기 필요 현금", "원"),
            ("monthly_profit_krw", "월 예상 손익", "원"),
            ("break_even_units_per_day", "손익분기 판매량", "개/day"),
        ]:
            value = data.get(key)
            if isinstance(value, (int, float)):
                lines.append(f"{label} {int(value):,}{suffix}")
        budget = data.get("budget_analysis")
        if isinstance(budget, dict) and isinstance(budget.get("funding_gap_krw"), (int, float)):
            lines.append(f"예산 대비 부족액 {int(budget['funding_gap_krw']):,}원")
        return lines

    def _operation_evidence(self, data: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        sales = data.get("sales_analysis")
        if isinstance(sales, dict) and isinstance(sales.get("latest_sales_krw"), (int, float)):
            lines.append(f"최근 매출 {int(sales['latest_sales_krw']):,}원")
        orders = data.get("order_analysis")
        if isinstance(orders, dict) and orders.get("orders") is not None:
            lines.append(f"주문 수 {orders.get('orders')}건")
        inventory = data.get("inventory_analysis")
        if isinstance(inventory, dict):
            stockouts = inventory.get("stockout_items") or []
            slow = inventory.get("slow_moving_items") or []
            if stockouts:
                lines.append(f"품절 품목: {', '.join(map(str, stockouts[:3]))}")
            if slow:
                lines.append(f"재고 누적 품목: {', '.join(map(str, slow[:3]))}")
        risks = data.get("risk_items")
        if isinstance(risks, list) and risks:
            top = risks[0]
            if isinstance(top, dict) and top.get("risk"):
                lines.append(f"최우선 운영 리스크: {top.get('risk')}")
        return lines

    def _policy_evidence(self, data: dict[str, Any]) -> list[str]:
        matches = data.get("matches")
        if not isinstance(matches, list) or not matches:
            return []
        top = matches[0]
        if not isinstance(top, dict):
            return []
        lines = []
        title = top.get("title")
        score = top.get("eligibility_score")
        if title:
            lines.append(f"1순위 공고: {title}")
        if isinstance(score, (int, float)):
            lines.append(f"공고 적합도 {int(score)}점")
        reasons = top.get("why_matched")
        if isinstance(reasons, list) and reasons:
            lines.append(f"매칭 이유: {reasons[0]}")
        return lines

    def _legal_evidence(self, data: dict[str, Any]) -> list[str]:
        lines: list[str] = []
        for key in ("citations", "source_chunks", "legal_references", "references"):
            values = data.get(key)
            if isinstance(values, list) and values:
                first = values[0]
                if isinstance(first, dict):
                    title = first.get("law_name") or first.get("title") or first.get("source")
                    article = first.get("article_title") or first.get("article_no")
                    if title:
                        lines.append(f"참조 법령: {title}{f' {article}' if article else ''}")
                elif isinstance(first, str):
                    lines.append(f"참조 근거: {first}")
                break
        checklist = data.get("checklist") or data.get("required_checks")
        if isinstance(checklist, list) and checklist:
            lines.append(f"우선 확인 항목: {checklist[0]}")
        return lines

    def _commercial_area_evidence(self, data: dict[str, Any]) -> list[str]:
        payload = data.get("payload")
        source = payload if isinstance(payload, dict) else data
        lines = []
        for key, label in [
            ("total_stores", "전체 점포"),
            ("direct_competitors", "직접 경쟁점"),
            ("similar_competitors", "유사 경쟁점"),
        ]:
            value = source.get(key)
            if isinstance(value, (int, float)):
                lines.append(f"{label} {int(value):,}개")
        level = source.get("competition_level")
        if level:
            lines.append(f"경쟁 강도 {level}")
        return lines

    def _marketing_evidence(self, data: dict[str, Any]) -> list[str]:
        lines = []
        for key, label in [
            ("target_customer", "타깃"),
            ("channel", "채널"),
            ("objective", "목표"),
        ]:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(f"{label}: {value.strip()}")
        schedule = data.get("upload_schedule") or data.get("schedule")
        if isinstance(schedule, list) and schedule:
            lines.append(f"실행 일정: {schedule[0]}")
        return lines

    def _idea_evidence(self, data: dict[str, Any]) -> list[str]:
        recommendations = data.get("recommendations")
        if not isinstance(recommendations, list) or not recommendations:
            return []
        top = recommendations[0]
        if not isinstance(top, dict):
            return []
        lines = []
        title = top.get("title")
        score = top.get("match_score")
        if title:
            lines.append(f"1순위 후보: {title}")
        if isinstance(score, (int, float)):
            lines.append(f"아이템 적합도 {int(score)}점")
        why = top.get("why_recommended")
        if isinstance(why, list) and why:
            lines.append(f"추천 이유: {why[0]}")
        return lines

    def _profile_evidence(self, data: dict[str, Any]) -> list[str]:
        summary = data.get("profile_summary")
        if not isinstance(summary, dict):
            return []
        lines = []
        for key, label in [
            ("region", "지역"),
            ("budget_krw", "예산"),
            ("risk_tolerance", "위험 선호"),
        ]:
            value = summary.get(key)
            if isinstance(value, (int, float)) and key.endswith("_krw"):
                lines.append(f"{label} {int(value):,}원")
            elif value:
                lines.append(f"{label}: {value}")
        return lines

    def _flatten_evidence(self, evidence: Any) -> list[str]:
        if not evidence:
            return []
        if isinstance(evidence, str):
            return [evidence.strip()] if evidence.strip() else []
        if isinstance(evidence, list):
            lines: list[str] = []
            for item in evidence[:3]:
                lines.extend(self._flatten_evidence(item))
            return lines
        if isinstance(evidence, dict):
            lines = []
            for key, value in evidence.items():
                if value in (None, "", [], {}):
                    continue
                label = str(key).replace("_", " ")
                if isinstance(value, (int, float)):
                    lines.append(f"{label}: {value:,}")
                elif isinstance(value, str):
                    lines.append(f"{label}: {value}")
                elif isinstance(value, list) and value:
                    lines.append(f"{label}: {', '.join(map(str, value[:3]))}")
                if len(lines) >= 3:
                    break
            return lines
        return []

    def _unique_compact(self, values: list[str], limit: int = 4) -> list[str]:
        seen = set()
        result: list[str] = []
        for value in values:
            item = " ".join(str(value).split())
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
            if len(result) >= limit:
                break
        return result

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
        feature_key = feature_key_from_request(request)
        if feature_key in FEATURE_REPORT_TEAMS:
            plan = FEATURE_REPORT_TEAMS[feature_key]
            plan_meta = {
                "source": "feature_report_team",
                "target_feature": feature_key,
                "reason": "기능 페이지 리포트 생성을 위해 고정 Agent 팀을 사용합니다.",
            }
        elif request.intent == "auto":
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
            "target_feature": feature_key,
            "plan": plan,
            "plan_meta": plan_meta,
            "effective_profile": effective_profile,
            "results": {},
            "followups": [],
            "followup_meta": {},
            "progress_lock": asyncio.Lock(),
            "progress_last_at": time.monotonic(),
        }

    async def _run_agents(self, state: dict[str, Any], intents: list[str]) -> None:
        pending = [intent for intent in intents if intent not in state["results"]]
        if not pending:
            return
        pairs = await asyncio.gather(*(self._run_agent_with_progress(state, intent) for intent in pending))
        for intent, response in pairs:
            state["results"][intent] = response

    async def _run_agent_with_progress(self, state: dict[str, Any], intent: str) -> tuple[str, AgentResponse]:
        await self._emit_progress(
            state,
            "agent.started",
            self._agent_started_message(intent),
            agent_intent=intent,
            agent_status="running",
        )
        started_at = time.monotonic()
        try:
            intent, response = await self._run_agent(state, intent)
        except Exception:
            await self._emit_progress(
                state,
                "agent.failed",
                f"{self._agent_descriptor(intent, 'failed')['label']} 검토 중 오류가 발생했습니다.",
                agent_intent=intent,
                agent_status="failed",
                status="FAILED",
            )
            raise
        await self._think_dwell(started_at)
        await self._emit_progress(
            state,
            "agent.completed",
            self._agent_completed_message(response),
            agent_intent=intent,
            agent_status="completed",
            detail=self._agent_progress_detail(response),
        )
        return intent, response

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
                PolicyRequest(profile=effective_profile, query=query, limit=3, context=request.context)
            )
        if intent == "legal":
            return intent, await self.legal_agent.run(
                LegalRequest(profile=effective_profile, query=request.message, limit=5)
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
                self._operation_request_from_context(request, effective_profile)
            )
        if intent == "plan":
            return intent, await self.plan_agent.run(
                self._plan_request_from_context(request, effective_profile)
            )
        if intent == "commercial_area":
            return intent, await self.commercial_area_agent.run(
                CommercialAreaRequest(profile=effective_profile, query=request.message, context=request.context)
            )
        if intent == "marketing":
            return intent, await self.marketing_agent.run(
                self._marketing_request_from_context(request, effective_profile)
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
            "debate_rounds": state.get("debate_rounds", {}),
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
            summary=self._selective_summary(results, state.get("debate_rounds")),
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

    def _selective_summary(self, results: dict[str, AgentResponse], debate_rounds: dict[str, Any] | None = None) -> str:
        sections: list[str] = []
        for intent, response in results.items():
            sections.append(self._agent_final_section(intent, response))

        if not sections:
            agent_names = [response.agent for response in results.values()]
            return f"{', '.join(agent_names)}가 이 질문에 필요한 범위로 검토했습니다."

        if len(sections) == 1:
            return sections[0]

        return "\n\n".join(
            [
                "Agent들이 각자 먼저 보고, 서로 걸리는 부분까지 맞춰본 내용이에요.",
                *sections,
                self._debate_transcript_summary(debate_rounds),
                self._final_consensus(results, debate_rounds),
            ]
        )

    def _agent_final_section(self, intent: str, response: AgentResponse) -> str:
        label = self._agent_descriptor(intent, "completed")["label"]
        summary = (response.summary or response.data.get("position") or "").strip()
        evidence_lines = self._agent_evidence_lines(response)
        risks = response.data.get("risks", []) if isinstance(response.data, dict) else []
        next_actions = response.next_actions or []

        lines = [f"[{label}]"]
        if summary:
            lines.append(summary)
        if evidence_lines:
            lines.append("")
            lines.append("근거")
            lines.extend(f"- {line}" for line in evidence_lines)
        if isinstance(risks, list) and risks:
            lines.append("")
            lines.append("주의할 점")
            lines.extend(f"- {str(risk).strip()}" for risk in risks[:3] if str(risk).strip())
        if next_actions:
            lines.append("")
            lines.append("다음 행동")
            lines.extend(f"- {action}" for action in next_actions[:3])
        return "\n".join(lines)

    def _final_consensus(self, results: dict[str, AgentResponse], debate_rounds: dict[str, Any] | None = None) -> str:
        labels = [
            self._agent_descriptor(intent, "completed")["label"]
            for intent in results
        ]
        actions = self._unique([
            action
            for response in results.values()
            for action in response.next_actions[:2]
        ])
        lines = [
            "[마지막 정리]",
            self._consensus_sentence(results, debate_rounds, labels),
        ]
        if actions:
            lines.append("우선순위 액션")
            lines.extend(f"- {action}" for action in actions[:4])
        return "\n".join(lines)

    async def _run_debate_round(self, state: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, AgentResponse] = state["results"]
        challenges = self._debate_challenges(results)[:2]
        if not challenges:
            await self._emit_progress(
                state,
                "orchestrator.synthesizing",
                "Agent 의견을 한 번 맞춰보고 있어요.",
                view_type="discussion",
            )
            return {
                "arguments": [],
                "challenges": [],
                "revisions": [],
                "consensus": self._debate_consensus(results, [], []),
            }

        await self._emit_progress(
            state,
            "orchestrator.synthesizing",
            "의견이 갈리는 부분만 짧게 짚어볼게요.",
            view_type="discussion",
        )

        for challenge in challenges:
            await self._emit_progress(
                state,
                "agent.challenge",
                challenge["message"],
                agent_intent=challenge["source_intent"],
                agent_status="completed",
                view_type="challenge",
                detail=challenge,
            )

        revisions: list[dict[str, Any]] = []

        consensus = self._debate_consensus(results, challenges, revisions)
        await self._emit_progress(
            state,
            "orchestrator.consensus",
            consensus["message"],
            agent_intent="orchestrator",
            agent_status="completed",
            view_type="consensus",
            detail=consensus,
        )

        return {
            "arguments": [],
            "challenges": challenges,
            "revisions": revisions,
            "consensus": consensus,
        }

    def _should_run_feature_report_review(self, state: dict[str, Any]) -> bool:
        feature_key = str(state.get("target_feature") or "").upper()
        return (
            feature_key in FEATURE_REVIEW_FEATURES
            and self._should_create_feature_result(state["request"])
            and len(state.get("results", {})) > 1
        )

    async def _run_feature_report_review(self, state: dict[str, Any]) -> None:
        feature_key = str(state.get("target_feature") or "").upper()
        try:
            await self._emit_progress(
                state,
                "feature_review.started",
                "Agent들이 리포트 초안을 한 번 더 검토하고 있어요.",
                view_type="discussion",
            )
            results: dict[str, AgentResponse] = state["results"]
            debate_rounds = state.get("debate_rounds") or {}
            raw_challenges = debate_rounds.get("challenges")
            challenges = raw_challenges[:3] if isinstance(raw_challenges, list) else []
            if not challenges:
                challenges = self._debate_challenges(results)[:3]
            revisions = self._debate_revisions(challenges, results)
            consensus = self._debate_consensus(results, challenges, revisions)
            review = self._feature_report_review(feature_key, results, challenges, revisions, consensus)
            state["feature_review"] = review
            state["debate_rounds"] = {
                **debate_rounds,
                "challenges": challenges,
                "revisions": revisions,
                "consensus": consensus,
            }
            await self._emit_progress(
                state,
                "feature_review.completed",
                review["summary"],
                agent_intent="orchestrator",
                agent_status="completed",
                view_type="consensus",
                detail=review,
            )
        except Exception as exc:
            state["feature_review"] = {
                "summary": "Agent 검토 중 일부 오류가 있어 기본 리포트를 우선 생성했습니다.",
                "checks": self._feature_review_checks(feature_key, state.get("results", {}), []),
                "revisions": [],
                "warnings": [str(exc)],
                "rounds": [],
                "challenges": [],
                "revisionMessages": [],
                "consensus": {},
            }

    def _feature_report_review(
        self,
        feature_key: str,
        results: dict[str, AgentResponse],
        challenges: list[dict[str, Any]],
        revisions: list[dict[str, Any]],
        consensus: dict[str, Any],
    ) -> dict[str, Any]:
        checks = self._feature_review_checks(feature_key, results, challenges)
        revision_lines = self._feature_review_revisions(feature_key, challenges, revisions)
        if challenges:
            summary = f"{', '.join(checks[:3])} 기준으로 {len(challenges)}개 보완점을 리포트에 반영했습니다."
        else:
            summary = f"{', '.join(checks[:3])} 기준으로 Agent들이 초안을 재검토했고 큰 충돌은 없었습니다."
        return {
            "summary": summary,
            "checks": checks,
            "revisions": revision_lines,
            "warnings": [],
            "rounds": [
                {"round": 1, "type": "draft", "agents": [response.agent for response in results.values()]},
                {"round": 2, "type": "critique", "items": challenges},
                {"round": 2, "type": "revision", "items": revisions},
            ],
            "challenges": challenges,
            "revisionMessages": revisions,
            "consensus": consensus,
        }

    def _feature_review_checks(
        self,
        feature_key: str,
        results: dict[str, AgentResponse],
        challenges: list[dict[str, Any]],
    ) -> list[str]:
        labels = {
            "profile": "프로필 적합성",
            "idea": "아이템-고객 적합성",
            "finance": "예산 현실성",
            "policy": "지원조건 부합성",
            "plan": "사업계획서 논리",
            "commercial_area": "지역/상권 경쟁도",
        }
        feature_defaults = {
            "ITEM": ["프로필 적합성", "아이템-고객 적합성", "예산 현실성", "지원조건 부합성", "지역/상권 경쟁도"],
            "SUPPORT": ["프로필 적합성", "지원조건 부합성", "예산 현실성"],
            "PLAN": ["사업계획서 논리", "지원조건 부합성", "예산 현실성", "지역/상권 경쟁도"],
        }
        ordered = [labels[intent] for intent in results if intent in labels]
        ordered.extend(labels[str(item.get("source_intent"))] for item in challenges if str(item.get("source_intent")) in labels)
        ordered.extend(feature_defaults.get(feature_key, []))
        return self._unique_compact(ordered, limit=5)

    def _feature_review_revisions(
        self,
        feature_key: str,
        challenges: list[dict[str, Any]],
        revisions: list[dict[str, Any]],
    ) -> list[str]:
        proposals = [
            str(item.get("proposal") or "").strip()
            for item in challenges
            if str(item.get("proposal") or "").strip()
        ]
        if proposals:
            return self._unique_compact(proposals, limit=4)
        if revisions:
            messages = [self._compact_revision_message(item.get("message")) for item in revisions]
            return self._unique_compact(messages, limit=4)
        defaults = {
            "ITEM": ["추천 아이템은 상권 경쟁도와 초기비용을 함께 보고 우선순위를 유지했습니다."],
            "SUPPORT": ["지원사업 후보는 자격 조건과 자금 사용 계획을 함께 확인하도록 보완했습니다."],
            "PLAN": ["사업계획서 초안은 지원조건, 비용 가정, 실행 근거를 확인하는 문단을 추가했습니다."],
        }
        return defaults.get(feature_key, [])

    def _compact_revision_message(self, value: Any) -> str:
        text = " ".join(str(value or "").split())
        if "\n" in str(value or ""):
            text = " ".join(str(value).splitlines()[-1].split())
        return text[:180]

    def _debate_argument(self, intent: str, response: AgentResponse) -> dict[str, Any]:
        label = self._agent_descriptor(intent, "completed")["label"]
        position = str(response.data.get("position") or response.summary or "추가 판단이 필요합니다.").strip()
        evidence = self._agent_evidence_lines(response)
        evidence_text = "; ".join(evidence[:3]) if evidence else "명시 근거 부족"
        return {
            "type": "argument",
            "source_intent": intent,
            "source_agent": response.agent,
            "label": label,
            "position": position,
            "evidence": evidence,
            "message": f"{label}: 저는 일단 이렇게 봤어요.\n{position}\n근거로는 {evidence_text}를 봤습니다.",
        }

    def _debate_challenges(self, results: dict[str, AgentResponse]) -> list[dict[str, Any]]:
        challenges: list[dict[str, Any]] = []

        finance = results.get("finance")
        if finance:
            finance_data = finance.data or {}
            budget = finance_data.get("budget_analysis") or {}
            monthly_profit = finance_data.get("monthly_profit_krw")
            funding_gap = budget.get("funding_gap_krw") or 0
            if funding_gap > 0 or (isinstance(monthly_profit, (int, float)) and monthly_profit < 0):
                target = "idea" if "idea" in results else "orchestrator"
                challenges.append(self._challenge(
                    source="finance",
                    target=target,
                    issue="현재 아이템/실행안은 재무 조건과 충돌합니다.",
                    basis=self._join_nonempty([
                        f"부족액 {int(funding_gap):,}원" if funding_gap else "",
                        f"월 손익 {int(monthly_profit):,}원" if isinstance(monthly_profit, (int, float)) else "",
                        f"손익분기 {finance_data.get('break_even_units_per_day')}개/day" if finance_data.get("break_even_units_per_day") else "",
                    ]),
                    proposal="아이디어를 유지하더라도 매장형/재고형 실행은 미루고 30일 MVP나 예약판매로 축소해야 합니다.",
                ))
            elif "policy" in results and (finance_data.get("support_handoff") or {}).get("needed_support_types"):
                challenges.append(self._challenge(
                    source="finance",
                    target="policy",
                    issue="재무 Agent는 지원사업 매칭을 비용 보완 수단으로 요청합니다.",
                    basis="초기 현금, 마케팅비, 공간/장비 지원 필요 신호가 있습니다.",
                    proposal="PolicyAgent는 단순 추천보다 자금/공간/장비 지원 여부를 우선 검토해야 합니다.",
                ))

        policy = results.get("policy")
        if policy:
            matches = policy.data.get("matches") or []
            top = matches[0] if matches else {}
            score = top.get("eligibility_score") if isinstance(top, dict) else None
            gaps = top.get("eligibility_gaps") if isinstance(top, dict) else []
            if isinstance(score, (int, float)) and score < 70:
                challenges.append(self._challenge(
                    source="policy",
                    target="orchestrator",
                    issue="지원사업 후보를 최종 전략의 중심에 두기에는 적합도가 낮습니다.",
                    basis=f"상위 공고 적합도 {int(score)}점",
                    proposal="지원사업은 보조 플랜으로 두고 고객 검증과 재무 축소안을 먼저 확정해야 합니다.",
                ))
            elif gaps:
                challenges.append(self._challenge(
                    source="policy",
                    target="profile" if "profile" in results else "orchestrator",
                    issue="지원사업 신청 전 자격 공백이 남아 있습니다.",
                    basis=", ".join(map(str, gaps[:3])),
                    proposal="지역, 창업 단계, 사업자 등록 여부 같은 증빙 정보를 먼저 확인해야 합니다.",
                ))

        operation = results.get("operation")
        if operation:
            data = operation.data or {}
            missing = data.get("missing_inputs") or []
            risk_items = data.get("risk_items") or []
            if missing or data.get("needs_more_data"):
                challenges.append(self._challenge(
                    source="operation",
                    target="finance" if "finance" in results else "idea" if "idea" in results else "orchestrator",
                    issue="운영 Agent는 현재 결론의 실행 근거가 부족하다고 봅니다.",
                    basis=f"부족 입력: {', '.join(map(str, missing[:4]))}" if missing else "매출/주문/재고/피드백 데이터 부족",
                    proposal="최종 답변은 확정 판단보다 추가 질문과 데이터 수집 액션을 먼저 제시해야 합니다.",
                ))
            elif risk_items:
                top_risk = risk_items[0]
                if isinstance(top_risk, dict):
                    challenges.append(self._challenge(
                        source="operation",
                        target="marketing" if "marketing" in results else "idea" if "idea" in results else "orchestrator",
                        issue=f"운영 리스크 '{top_risk.get('risk')}'가 실행안을 제한합니다.",
                        basis=str(top_risk.get("basis") or top_risk.get("signal") or "운영 데이터 기반 위험 신호"),
                        proposal=str(top_risk.get("action") or "다음 주 운영 액션에 리스크 완화 계획을 넣어야 합니다."),
                    ))

        legal = results.get("legal")
        if legal:
            citations = legal.data.get("citations") or legal.data.get("search_results") or []
            if citations:
                challenges.append(self._challenge(
                    source="legal",
                    target="marketing" if "marketing" in results else "operation" if "operation" in results else "orchestrator",
                    issue="법률 Agent는 홍보/판매 실행 전에 인허가와 고지 의무를 확인해야 한다고 봅니다.",
                    basis=self._join_nonempty(self._agent_evidence_lines(legal)[:3]),
                    proposal="최종 액션에 관할 지자체 확인, 신고 대상 여부, 표시/광고/개인정보 체크를 넣어야 합니다.",
                ))

        commercial_area = results.get("commercial_area")
        if commercial_area:
            payload = commercial_area.data.get("payload") if isinstance(commercial_area.data, dict) else {}
            level = (payload or {}).get("competition_level") or commercial_area.data.get("competition_level")
            direct = (payload or {}).get("direct_competitors") or commercial_area.data.get("direct_competitors")
            if str(level).lower() in {"high", "높음"} or (isinstance(direct, (int, float)) and direct >= 50):
                challenges.append(self._challenge(
                    source="commercial_area",
                    target="idea" if "idea" in results else "marketing" if "marketing" in results else "orchestrator",
                    issue="상권 Agent는 입지 경쟁 강도가 높아 일반적인 아이템 추천만으로는 부족하다고 봅니다.",
                    basis=self._join_nonempty([
                        f"경쟁 강도 {level}" if level else "",
                        f"직접 경쟁점 {int(direct):,}개" if isinstance(direct, (int, float)) else "",
                    ]),
                    proposal="입점 판단 전에 메뉴/가격/운영 시간 차별화와 후보지 비교를 먼저 해야 합니다.",
                ))

        marketing = results.get("marketing")
        if marketing and marketing.data.get("missing_inputs"):
            challenges.append(self._challenge(
                source="marketing",
                target="idea" if "idea" in results else "orchestrator",
                issue="마케팅 Agent는 타깃/장소/일정이 부족하면 홍보안의 전환성이 낮다고 봅니다.",
                basis=", ".join(map(str, marketing.data.get("missing_inputs", [])[:4])),
                proposal="콘텐츠 초안보다 타깃 고객, 판매 장소, CTA를 먼저 좁혀야 합니다.",
            ))

        return challenges

    def _challenge(self, *, source: str, target: str, issue: str, basis: str, proposal: str) -> dict[str, Any]:
        source_label = self._agent_descriptor(source, "completed")["label"]
        target_label = self._agent_descriptor(target, "completed")["label"] if target != "orchestrator" else "Plan Agent"
        return {
            "type": "challenge",
            "source_intent": source,
            "target_intent": target,
            "issue": issue,
            "basis": basis,
            "proposal": proposal,
            "message": (
                f"{source_label} -> {target_label}: 잠깐, 이 부분은 그대로 가면 조금 위험해 보여요.\n"
                f"걸리는 점: {issue}\n"
                f"제가 본 근거: {basis or '근거를 조금 더 확인해야 합니다'}\n"
                f"그래서 제안은 이거예요: {proposal}"
            ),
        }

    def _debate_revisions(
        self,
        challenges: list[dict[str, Any]],
        results: dict[str, AgentResponse],
    ) -> list[dict[str, Any]]:
        revisions: list[dict[str, Any]] = []
        handled_targets: set[str] = set()
        for challenge in challenges:
            target = str(challenge.get("target_intent") or "orchestrator")
            if target in handled_targets and target != "orchestrator":
                continue
            handled_targets.add(target)
            source = target if target in results else str(challenge.get("source_intent") or "orchestrator")
            label = self._agent_descriptor(source, "completed")["label"] if source != "orchestrator" else "Plan Agent"
            message = self._revision_message(source, challenge, results)
            revisions.append({
                "type": "revision",
                "source_intent": source,
                "target_intent": challenge.get("source_intent"),
                "based_on_issue": challenge.get("issue"),
                "message": f"{label}: 맞아요, 그 지적 반영하면 이렇게 조정하는 게 낫겠어요.\n{message}",
            })
        return revisions

    def _revision_message(
        self,
        source: str,
        challenge: dict[str, Any],
        results: dict[str, AgentResponse],
    ) -> str:
        issue = str(challenge.get("issue") or "")
        if source == "idea":
            return "아이템 자체는 괜찮지만, 바로 크게 열기보다는 30일 MVP/예약판매/팝업 테스트로 작게 검증하는 쪽으로 바꿀게요."
        if source == "finance":
            return "수익은 확정처럼 말하면 안 되겠네요. 가정 기반 시뮬레이션으로 낮춰 말하고, 실제 원가/임대료/판매량 확인을 먼저 넣겠습니다."
        if source == "policy":
            return "지원사업은 1순위와 예비 후보를 나누고, 실제 공고의 지역/업력/업종 조건 확인을 먼저 하도록 정리할게요."
        if source == "marketing":
            return "홍보안은 확정 캠페인처럼 말하지 않고, 타깃/장소/일정을 확인한 뒤 A/B 테스트하는 초안으로 둘게요."
        if source == "operation":
            return "운영 평가는 결론부터 내리기보다, 매출/주문/재고/피드백 중 최소 2~3개를 더 묻는 쪽이 맞겠어요."
        if source == "legal":
            return "실행 전에 인허가, 신고 대상, 표시광고, 개인정보 확인을 체크리스트에 꼭 넣겠습니다."
        if "재무" in issue or "비용" in issue:
            return "최종안은 비용 부담이 낮은 검증형 실행으로 낮춰 잡겠습니다."
        return "최종 답변에서 이 걸리는 지점을 숨기지 않고, 확인할 조건까지 같이 말하겠습니다."

    def _debate_consensus(
        self,
        results: dict[str, AgentResponse],
        challenges: list[dict[str, Any]],
        revisions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not challenges:
            message = "Plan Agent: 크게 부딪히는 부분은 없네요. 각 Agent 의견을 한 실행 흐름으로 묶어도 괜찮겠습니다."
            decision = "agent_agreement"
        else:
            main_issues = self._unique([str(item.get("issue")) for item in challenges if item.get("issue")])
            message = (
                "Plan Agent: 좋아요, 이 충돌은 최종 답변에 조건으로 반영할게요.\n"
                f"체크할 부분: {' / '.join(main_issues[:3])}\n"
                "그래서 결론은 '바로 확정'이 아니라, 아이템 방향은 살리되 필요한 정보 확인과 30일 검증을 먼저 두는 쪽으로 정리하겠습니다."
            )
            decision = "conditional_consensus"
        return {
            "type": "consensus",
            "decision": decision,
            "challenge_count": len(challenges),
            "revision_count": len(revisions),
            "message": message,
        }

    def _debate_transcript_summary(self, debate_rounds: dict[str, Any] | None) -> str:
        if not debate_rounds:
            return ""
        challenges = debate_rounds.get("challenges") or []
        revisions = debate_rounds.get("revisions") or []
        consensus = debate_rounds.get("consensus") or {}
        lines = ["[Agent 의견 조율]"]
        if challenges:
            lines.append("걸리는 부분")
            for item in challenges[:4]:
                lines.append(f"- {item.get('source_intent')} -> {item.get('target_intent')}: {item.get('issue')}")
        else:
            return ""
        if consensus.get("message"):
            lines.append("정리")
            lines.append(f"- {consensus['message']}")
        return "\n".join(lines)

    def _consensus_sentence(
        self,
        results: dict[str, AgentResponse],
        debate_rounds: dict[str, Any] | None,
        labels: list[str],
    ) -> str:
        consensus = (debate_rounds or {}).get("consensus") or {}
        if consensus.get("decision") == "conditional_consensus":
            return (
                f"{', '.join(labels)}가 이야기해본 결과, 바로 확정 실행하기보다는 "
                "아이템 방향은 살리고 재무, 법률, 운영 리스크를 30일 검증으로 낮추는 쪽이 좋아 보입니다."
            )
        return f"{', '.join(labels)} 의견을 모아보면, 위 근거를 같이 보고 다음 행동을 정하면 됩니다."

    def _join_nonempty(self, values: list[str]) -> str:
        return ", ".join(value for value in values if value)

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

    def _attach_feature_result(self, response: AgentResponse, state: dict[str, Any]) -> AgentResponse:
        if not self._should_attach_result(state):
            return response
        feature_result = build_feature_result(
            request=state["request"],
            response=response,
            results=state.get("results", {}),
            agent_review=state.get("feature_review"),
        )
        if feature_result is None:
            return response
        response.result = feature_result
        return response

    def _should_attach_result(self, state: dict[str, Any]) -> bool:
        request = state["request"]
        if self._should_create_feature_result(request):
            return True
        if feature_key_from_request(request):
            return True
        if state.get("mode") == "collaboration":
            return True
        if len(state.get("results", {})) > 1:
            return True
        result_intents = set(state.get("results", {}).keys())
        if result_intents & {
            "idea",
            "policy",
            "finance",
            "simulation",
            "operation",
            "marketing",
            "legal",
            "commercial_area",
        }:
            return True
        intent = (request.intent or "").lower()
        return intent in {
            "idea",
            "policy",
            "finance",
            "simulation",
            "operation",
            "marketing",
            "legal",
            "commercial_area",
            "roadmap",
        }

    def _should_create_feature_result(self, request: ChatRequest) -> bool:
        metadata = self._dict_at(request.context or {}, "requestMetadata")
        report_generation = metadata.get("reportGeneration")
        if report_generation is True or str(report_generation).lower() == "true":
            return True

        text = (request.message or "").lower()
        update_keywords = [
            "다시 추천",
            "다시 만들어",
            "재생성",
            "새로고침",
            "갱신",
            "업데이트",
            "수정",
            "반영",
            "조건 바꿔",
            "조건을 바꿔",
            "바꿔줘",
            "변경",
            "고쳐줘",
            "다시 짜",
            "다시 써",
            "refresh",
            "update",
            "regenerate",
            "revise",
        ]
        return any(keyword in text for keyword in update_keywords)

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
            "- policy: government support programs, applications, grant documents and deadlines\n"
            "- legal: laws, permits, reports, contracts, tax/legal checklist, privacy, trademark, labor\n"
            "- finance: budget, price, revenue, cost, margin, BEP, cash flow, feasibility\n"
            "- operation: inventory, staffing, store operations, reviews, execution process\n"
            "- marketing: SNS, reels, captions, promotion, customer acquisition\n"
            "- commercial_area: store location, local commercial area, nearby competitors, market density\n"
            "- simulation: 30-day game-like simulation or choice-based scenario\n"
            "- collaboration: broad end-to-end consultation when the user asks for an overall plan or intent is genuinely ambiguous\n\n"
            "Rules:\n"
            "- Pick 1 agent for a narrow question.\n"
            "- Pick 2-3 agents when the user explicitly asks across multiple domains.\n"
            "- Do not pick collaboration when a smaller agent set can answer.\n"
            "- If legal, permit, report, contract, tax, privacy, trademark, labor, or regulation is asked, include legal.\n"
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
            "plan",
            "legal",
            "finance",
            "operation",
            "marketing",
            "commercial_area",
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
        if any(keyword in text for keyword in ["법률", "법적", "법", "인허가", "허가", "신고", "계약", "세금", "세무", "개인정보", "상표", "저작권", "근로", "최저임금"]):
            plan.append("legal")
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
        if any(keyword in text for keyword in ["상권", "입지", "경쟁점", "경쟁", "주변 점포", "주변 가게", "연남동", "마포구", "구미", "인동동"]):
            plan.append("commercial_area")
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
        if len(state["results"]) > 1:
            state["debate_rounds"] = await self._run_debate_round(state)
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
            "policy": "지원사업/정책/공고/서류 관련 표현",
            "legal": "법률/인허가/신고/계약/세무/개인정보 관련 표현",
            "idea": "아이템 추천/창업 후보 탐색 표현",
            "operation": "운영/재고/리뷰/매장 관리 표현",
            "marketing": "SNS/홍보/콘텐츠 표현",
            "commercial_area": "상권/입지/경쟁점/주변 점포 분석 표현",
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
            PolicyRequest(profile=effective_profile, query=policy_query, limit=3, context=request.context)
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

    def _marketing_request_from_context(self, request: ChatRequest, profile=None) -> MarketingRequest:
        context = request.context or {}
        message = request.message or ""
        feature_payload = self._dict_at(context, "featurePayload") or self._dict_at(context, "feature_payload")
        current_result = (
            self._dict_at(context, "currentResult")
            or self._dict_at(feature_payload, "currentResult")
            or self._dict_at(context, "current_result")
        )
        business_context = (
            self._dict_at(context, "businessContext")
            or self._dict_at(current_result, "businessContext")
            or self._dict_at(feature_payload, "businessContext")
        )
        selected_idea = self._dict_at(business_context, "selectedIdea")

        product_name = (
            context.get("product_name")
            or context.get("item_name")
            or self._title_at(selected_idea)
            or self._infer_marketing_product(message)
            or "창업 상품"
        )
        return MarketingRequest(
            profile=profile or request.profile,
            product_name=str(product_name),
            event_date=context.get("event_date") or self._infer_marketing_event_date(message),
            target_customer=context.get("target_customer") or self._infer_marketing_target(message, profile or request.profile),
            place=context.get("place") or self._infer_marketing_place(message, profile or request.profile),
            brand_tone=context.get("brand_tone", "친근하고 실행력 있는"),
            goal=message,
            channel=context.get("channel") or self._infer_marketing_channel(message),
            objective=context.get("objective") or self._infer_marketing_objective(message),
            schedule=context.get("schedule"),
        )

    def _infer_marketing_product(self, message: str) -> str | None:
        patterns = [
            r"([\w가-힣\s]{2,30}?)\s*(?:홍보|마케팅|릴스|게시글|콘텐츠|문구)",
            r"([\w가-힣\s]{2,30}?)\s*(?:팝업|스토어)\s*(?:홍보|마케팅|하려고|하고)",
            r"(수제\s*쿠키|쿠키\s*팝업|팝업\s*카페|음료\s*스탠드|스마트\s*운영\s*점검\s*서비스)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" ,.!?\n\t")
                value = re.sub(r"^(혹시|이번|지금|내가|저희|우리)\s*", "", value).strip()
                value = re.sub(r"^[가-힣A-Za-z0-9\s]+에서\s+", "", value).strip()
                if value:
                    return value
        if "쿠키" in message:
            return "수제 쿠키 팝업"
        if "카페" in message:
            return "팝업 카페"
        if "요식" in message or "음식" in message:
            return "요식업 창업 아이템"
        return None

    def _infer_marketing_event_date(self, message: str) -> str | None:
        patterns = [
            r"((?:이번|다음)\s*(?:주|주말|달|월|금요일|토요일|일요일))",
            r"(\d{1,2}\s*월\s*\d{1,2}\s*일)",
            r"(\d{1,2}\s*일\s*(?:동안|간))",
            r"(D-\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1).strip()
        return None

    def _infer_marketing_target(self, message: str, profile=None) -> str | None:
        target_keywords = {
            "대학생": "대학생",
            "직장인": "직장인",
            "청년": "청년 고객",
            "소상공인": "소상공인",
            "부모": "가족 고객",
            "아이": "가족 고객",
            "커플": "커플 고객",
        }
        found = [label for keyword, label in target_keywords.items() if keyword in message]
        if found:
            return ", ".join(self._unique(found))
        region = getattr(profile, "region", None) or "로컬"
        if any(keyword in message for keyword in ["쿠키", "디저트", "카페", "음료", "요식"]):
            return f"{region} 직장인, 대학생, 디저트 관심 고객"
        if any(keyword in message for keyword in ["매장", "운영", "점검", "소상공인"]):
            return f"{region} 소상공인과 매장 운영자"
        return None

    def _infer_marketing_place(self, message: str, profile=None) -> str | None:
        region_match = re.search(r"(구미|김천|대구|서울|부산|광주|대전|인천|울산|경북|경남|전북|전남|충북|충남|강원|제주)", message)
        region = region_match.group(1) if region_match else getattr(profile, "region", None)
        if "온라인" in message or "인스타" in message:
            return f"{region + ' ' if region else ''}온라인 판매 채널"
        if "팝업" in message or "길거리" in message or "오프라인" in message:
            return f"{region + ' ' if region else ''}팝업 현장"
        if region:
            return f"{region} 판매 채널"
        return None

    def _infer_marketing_channel(self, message: str) -> str | None:
        if any(keyword in message.lower() for keyword in ["릴스", "reels", "인스타", "instagram"]):
            return "Instagram Reels"
        if any(keyword in message.lower() for keyword in ["쇼츠", "shorts", "유튜브"]):
            return "YouTube Shorts"
        if "블로그" in message or "검색" in message:
            return "Blog/Search"
        if "전단" in message or "길거리" in message:
            return "Offline Flyer"
        return None

    def _infer_marketing_objective(self, message: str) -> str | None:
        if any(keyword in message for keyword in ["예약", "문의", "구매", "판매"]):
            return "예약/문의 전환"
        if any(keyword in message for keyword in ["방문", "팝업", "행사", "길거리"]):
            return "방문 유도"
        if any(keyword in message for keyword in ["홍보", "인지", "브랜딩"]):
            return "인지도 확보"
        return None

    def _plan_request_from_context(self, request: ChatRequest, profile=None) -> PlanRequest:
        context = request.context or {}
        current_result = self._dict_at(context, "currentResult")
        plan_context = (
            self._dict_at(context, "planContext")
            or self._dict_at(current_result, "planContext")
        )
        selection = self._dict_at(context, "selection")
        support_program = (
            self._dict_at(context, "selectedSupportProgram")
            or self._dict_at(current_result, "selectedSupportProgram")
            or self._dict_at(selection, "selectedSupportProgram")
        )
        idea_context = (
            self._dict_at(current_result, "ideaContext")
            or self._dict_at(context, "ideaContext")
        )
        plan_draft = self._dict_at(current_result, "planDraft")
        target = (
            plan_context.get("target")
            or plan_draft.get("target")
            or support_program.get("title")
            or "창업 지원사업"
        )
        return PlanRequest(
            profile=profile or request.profile,
            target=str(target),
            idea_name=self._title_at(idea_context),
            support_program=support_program,
            focused_section=self._dict_at(plan_context, "focusedSection") or self._dict_at(current_result, "focusedSection"),
            goal=str(plan_context.get("planGoal") or current_result.get("planGoal") or "ALIGN_SUPPORT"),
            context=context,
        )

    def _operation_request_from_context(self, request: ChatRequest, profile=None) -> OperationRequest:
        context = request.context or {}
        feature_payload = self._dict_at(context, "featurePayload") or self._dict_at(context, "feature_payload")
        current_result = (
            self._dict_at(context, "currentResult")
            or self._dict_at(feature_payload, "currentResult")
            or self._dict_at(context, "current_result")
        )
        operation_context = self._dict_at(feature_payload, "operationContext") or self._dict_at(context, "operationContext")
        operation_input = (
            self._dict_at(context, "operationInput")
            or self._dict_at(current_result, "operationInput")
            or self._dict_at(operation_context, "input")
            or operation_context
        )
        business_context = (
            self._dict_at(context, "businessContext")
            or self._dict_at(current_result, "businessContext")
            or self._dict_at(feature_payload, "businessContext")
        )

        business_name = (
            context.get("business_name")
            or context.get("item_name")
            or context.get("product_name")
            or self._title_at(self._dict_at(business_context, "selectedIdea"))
            or "테스트 매장"
        )
        kpis = self._operation_metrics_from_kpis(operation_input.get("kpis"))
        products = self._operation_products(operation_input.get("products"))
        channels = self._operation_channels(operation_input.get("channels"))
        notes = str(operation_input.get("notes") or context.get("notes") or "").strip() or None

        monthly_sales = self._metric_number(kpis, "매출", "sales", "revenue")
        orders = self._metric_number(kpis, "주문", "order")
        ad_spend = self._metric_number(kpis, "광고비", "ad spend", "ad_spend")
        conversion_rate = self._metric_ratio(kpis, "전환", "conversion")
        if monthly_sales is None:
            monthly_sales = self._metric_value_at(kpis, 0)
        if orders is None:
            orders = self._metric_value_at(kpis, 1)
        if conversion_rate is None:
            conversion_candidate = self._metric_value_at(kpis, 2)
            conversion_rate = conversion_candidate / 100 if conversion_candidate and conversion_candidate > 1 else conversion_candidate
        message_inputs = self._operation_inputs_from_message(request.message)
        if monthly_sales is None:
            monthly_sales = message_inputs.get("monthly_sales_krw")
        if orders is None:
            orders = message_inputs.get("orders")
        if ad_spend is None:
            ad_spend = message_inputs.get("ad_spend_krw")
        inventory_notes = self._unique([
            *self._list_str(context.get("inventory_notes")),
            *message_inputs.get("inventory_notes", []),
        ])
        customer_feedback = self._unique([
            *self._list_str(context.get("customer_feedback")),
            *message_inputs.get("customer_feedback", []),
        ])
        notes = notes or message_inputs.get("notes")

        return OperationRequest(
            profile=profile or request.profile,
            business_name=str(business_name),
            period=str(operation_input.get("period") or context.get("period") or "") or None,
            notes=notes,
            daily_sales_krw=self._list_int(context.get("daily_sales_krw")),
            weekly_sales_krw=self._list_int(context.get("weekly_sales_krw")),
            monthly_sales_krw=int(monthly_sales) if monthly_sales is not None else self._optional_int(context.get("monthly_sales_krw")),
            orders=int(orders) if orders is not None else self._optional_int(context.get("orders")),
            ad_spend_krw=int(ad_spend) if ad_spend is not None else self._optional_int(context.get("ad_spend_krw")),
            material_cost_krw=self._optional_int(context.get("material_cost_krw")),
            labor_cost_krw=self._optional_int(context.get("labor_cost_krw")),
            fixed_cost_krw=self._optional_int(context.get("fixed_cost_krw")),
            impressions=self._optional_int(context.get("impressions")),
            clicks=self._optional_int(context.get("clicks")),
            conversion_rate=conversion_rate if conversion_rate is not None else self._coerce_rate(context.get("conversion_rate")),
            inventory_notes=inventory_notes,
            stockout_items=self._list_str(context.get("stockout_items")),
            slow_moving_items=self._list_str(context.get("slow_moving_items")),
            customer_feedback=customer_feedback,
            review_keywords=self._list_str(context.get("review_keywords")),
            complaints=self._list_str(context.get("complaints")),
            channel_notes=channels,
            product_sales=products,
            metrics=kpis,
        )

    def _dict_at(self, value: Any, key: str) -> dict[str, Any]:
        if isinstance(value, dict) and isinstance(value.get(key), dict):
            return value[key]
        return {}

    def _title_at(self, value: dict[str, Any]) -> str | None:
        if not value:
            return None
        title = value.get("title") or value.get("name")
        return str(title).strip() if title else None

    def _operation_metrics_from_kpis(self, raw_kpis: Any) -> list[OperationMetric]:
        metrics: list[OperationMetric] = []
        if not isinstance(raw_kpis, list):
            return metrics
        for raw in raw_kpis:
            if isinstance(raw, dict):
                name = str(raw.get("name") or raw.get("label") or "").strip()
                value = self._number_from_text(raw.get("value"))
                memo = str(raw.get("delta") or raw.get("memo") or "").strip() or None
            elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                name = str(raw[0]).strip()
                value = self._number_from_text(raw[1])
                memo = str(raw[2]).strip() if len(raw) >= 3 and raw[2] is not None else None
            else:
                continue
            if name and value is not None:
                unit = "%" if "%" in str(raw) else None
                metrics.append(OperationMetric(name=name, value=value, unit=unit, memo=memo))
        return metrics

    def _operation_products(self, raw_products: Any) -> list[dict[str, Any]]:
        products = []
        if not isinstance(raw_products, list):
            return products
        for raw in raw_products:
            if isinstance(raw, dict):
                products.append(raw)
            elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                products.append({"name": str(raw[0]), "sales": self._number_from_text(raw[1]) or 0})
        return products

    def _operation_channels(self, raw_channels: Any) -> list[str]:
        notes = []
        if not isinstance(raw_channels, list):
            return notes
        for raw in raw_channels:
            if isinstance(raw, dict):
                name = raw.get("name") or raw.get("label") or "채널"
                summary = raw.get("summary") or raw.get("value") or raw.get("memo") or ""
                notes.append(f"{name}: {summary}")
            elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                notes.append(f"{raw[0]}: {raw[1]}")
            elif raw:
                notes.append(str(raw))
        return notes

    def _metric_number(self, metrics: list[OperationMetric], *keywords: str) -> float | None:
        lowered = [keyword.lower() for keyword in keywords]
        for metric in metrics:
            name = metric.name.lower()
            if any(keyword in name for keyword in lowered):
                return metric.value
        return None

    def _metric_ratio(self, metrics: list[OperationMetric], *keywords: str) -> float | None:
        value = self._metric_number(metrics, *keywords)
        if value is None:
            return None
        return value / 100 if value > 1 else value

    def _metric_value_at(self, metrics: list[OperationMetric], index: int) -> float | None:
        if 0 <= index < len(metrics):
            return metrics[index].value
        return None

    def _operation_inputs_from_message(self, message: str) -> dict[str, Any]:
        text = message or ""
        inventory_notes = self._sentences_with_keywords(
            text,
            ["품절", "재고", "남았", "남음", "부족", "완판", "과다"],
        )
        customer_feedback = self._feedback_from_message(text)
        return {
            "monthly_sales_krw": self._money_after_labels(text, ["매출", "월매출", "이번 달 매출"]),
            "orders": self._count_after_labels(text, ["주문 수", "주문수", "주문", "판매량"]),
            "ad_spend_krw": self._money_after_labels(text, ["광고비", "광고 비용", "마케팅비", "홍보비"]),
            "inventory_notes": inventory_notes,
            "customer_feedback": customer_feedback,
            "notes": text if any(keyword in text for keyword in ["운영", "매출", "주문", "재고", "피드백", "리뷰"]) else None,
        }

    def _money_after_labels(self, text: str, labels: list[str]) -> int | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = rf"(?:{label_pattern})[^\d-]*(\d[\d,]*(?:\.\d+)?)\s*(만원|천원|원)?"
        match = re.search(pattern, text)
        if not match:
            return None
        return self._korean_money_to_krw(match.group(1), match.group(2))

    def _count_after_labels(self, text: str, labels: list[str]) -> int | None:
        label_pattern = "|".join(re.escape(label) for label in labels)
        pattern = rf"(?:{label_pattern})[^\d-]*(\d[\d,]*)\s*(?:건|개|명|회)?"
        match = re.search(pattern, text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _korean_money_to_krw(self, raw_number: str, unit: str | None) -> int:
        number = float(raw_number.replace(",", ""))
        if unit == "만원":
            number *= 10_000
        elif unit == "천원":
            number *= 1_000
        return int(number)

    def _sentences_with_keywords(self, text: str, keywords: list[str]) -> list[str]:
        chunks = re.split(r"[.!?\n]|[。！？]", text)
        matches = []
        for chunk in chunks:
            item = chunk.strip(" ,，")
            if item and any(keyword in item for keyword in keywords):
                matches.append(item)
        return self._unique(matches)

    def _feedback_from_message(self, text: str) -> list[str]:
        feedback = []
        feedback_match = re.search(r"고객\s*피드백[^\w가-힣]*(.+)", text)
        if feedback_match:
            feedback_text = feedback_match.group(1)
            feedback_text = re.split(r"[.!?\n]|[。！？]", feedback_text)[0]
            feedback.extend(
                item.strip(" ,，'\"")
                for item in re.split(r",|、|그리고|및", feedback_text)
                if item.strip(" ,，'\"")
            )
        feedback.extend(
            self._sentences_with_keywords(
                text,
                ["비싸", "대기", "불만", "리뷰", "느리", "맛", "품질", "친절", "환불"],
            )
        )
        return self._unique(feedback)

    def _number_from_text(self, value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace(",", "").strip()
        multiplier = 1
        if "만원" in text:
            multiplier = 10_000
        elif "천원" in text:
            multiplier = 1_000
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        return float(match.group(0)) * multiplier

    def _optional_int(self, value: Any) -> int | None:
        number = self._number_from_text(value)
        return int(number) if number is not None else None

    def _list_int(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        numbers = []
        for item in value:
            number = self._number_from_text(item)
            if number is not None:
                numbers.append(int(number))
        return numbers

    def _list_str(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

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

    async def _run_direct_agent_with_progress(
        self,
        state: dict[str, Any],
        intent: str,
        task,
    ) -> AgentResponse:
        await self._emit_progress(
            state,
            "agent.started",
            self._agent_started_message(intent),
            agent_intent=intent,
            agent_status="running",
        )
        started_at = time.monotonic()
        try:
            response = await task
        except Exception:
            await self._emit_progress(
                state,
                "agent.failed",
                f"{self._agent_descriptor(intent, 'failed')['label']} 검토 중 오류가 발생했습니다.",
                agent_intent=intent,
                agent_status="failed",
                status="FAILED",
            )
            raise
        await self._think_dwell(started_at)
        await self._emit_progress(
            state,
            "agent.completed",
            self._agent_completed_message(response),
            agent_intent=intent,
            agent_status="completed",
            detail=self._agent_progress_detail(response),
        )
        return response

    async def _collaborative_consultation(
        self,
        request: ChatRequest,
        state: dict[str, Any] | None = None,
    ) -> AgentResponse:
        state = state or {}
        effective_profile = await self.profile_agent.build_effective_profile_async(request.profile, request.message)
        profile_task = self._run_direct_agent_with_progress(
            state,
            "profile",
            self.profile_agent.run(
                ProfileRequest(profile=effective_profile, question=request.message, use_llm_extraction=False)
            ),
        )
        ideas_task = self._run_direct_agent_with_progress(
            state,
            "idea",
            self.idea_agent.run(IdeaRequest(profile=effective_profile, count=3)),
        )
        policies_task = self._run_direct_agent_with_progress(
            state,
            "policy",
            self.policy_agent.run(PolicyRequest(profile=effective_profile, query=request.message, limit=3, context=request.context)),
        )
        profile, ideas, policies = await asyncio.gather(profile_task, ideas_task, policies_task)

        top_idea = self._pick_top_idea(ideas)
        top_idea_name = str(top_idea.get("title", "창업 아이템"))
        round1_synthesis = self._build_round1_synthesis(profile, ideas, policies)
        await self._emit_progress(
            state,
            "orchestrator.synthesizing",
            f"1차 의견을 합쳐 {top_idea_name}을 기준 후보로 검토합니다.",
        )

        finance_task = self._run_direct_agent_with_progress(
            state,
            "finance",
            self.finance_agent.run(
                FinanceRequest(
                    profile=effective_profile,
                    assumption=FinanceAssumption(item_name=top_idea_name),
                )
            ),
        )
        marketing_task = self._run_direct_agent_with_progress(
            state,
            "marketing",
            self.marketing_agent.run(
                MarketingRequest(
                    profile=effective_profile,
                    product_name=top_idea_name,
                    target_customer=request.context.get("target_customer"),
                    place=request.context.get("place"),
                    brand_tone=request.context.get("brand_tone", "친근하고 실행력 있는"),
                    goal=request.message,
                )
            ),
        )
        operation_task = self._run_direct_agent_with_progress(
            state,
            "operation",
            self.operation_agent.run(OperationRequest(profile=effective_profile, business_name=top_idea_name)),
        )
        finance, marketing, operation = await asyncio.gather(finance_task, marketing_task, operation_task)
        state["results"] = {
            "profile": profile,
            "idea": ideas,
            "policy": policies,
            "finance": finance,
            "marketing": marketing,
            "operation": operation,
        }
        debate_rounds = await self._run_debate_round(state)

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
            "debate_rounds": debate_rounds,
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
            summary=self._collaborative_final_summary(
                top_idea_name=top_idea_name,
                profile=profile,
                ideas=ideas,
                policies=policies,
                finance=finance,
                marketing=marketing,
                operation=operation,
                debate_rounds=debate_rounds,
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

    def _collaborative_final_summary(
        self,
        *,
        top_idea_name: str,
        profile: AgentResponse,
        ideas: AgentResponse,
        policies: AgentResponse,
        finance: AgentResponse,
        marketing: AgentResponse,
        operation: AgentResponse,
        debate_rounds: dict[str, Any] | None = None,
    ) -> str:
        top_idea = self._pick_top_idea(ideas)
        top_policy = self._pick_top_policy(policies)
        profile_summary = profile.data.get("profile_summary", {}) if isinstance(profile.data, dict) else {}
        finance_data = finance.data or {}
        marketing_data = marketing.data or {}
        operation_data = operation.data or {}

        profile_bits = self._unique([
            f"지역 {profile_summary.get('region')}" if profile_summary.get("region") else "",
            f"예산 {self._format_money(profile_summary.get('budget_krw'))}" if profile_summary.get("budget_krw") else "",
            f"관심 분야 {profile_summary.get('interest_area')}" if profile_summary.get("interest_area") else "",
            f"전공/역량 {profile_summary.get('major')}" if profile_summary.get("major") else "",
        ])
        idea_reason = self._first_text(top_idea.get("why_recommended"), top_idea.get("reason"), top_idea.get("description"))
        policy_title = str(top_policy.get("title")) if top_policy else ""
        policy_score = top_policy.get("eligibility_score") if isinstance(top_policy, dict) else None
        target = self._first_text(
            marketing_data.get("target_customer"),
            marketing_data.get("target"),
            marketing_data.get("primary_target"),
        )
        channel = self._first_text(
            marketing_data.get("channel"),
            marketing_data.get("recommended_channel"),
            marketing_data.get("primary_channel"),
        )

        finance_bits = self._unique([
            f"초기 필요 현금 {self._format_money(finance_data.get('initial_cash_needed_krw'))}" if finance_data.get("initial_cash_needed_krw") is not None else "",
            f"월 예상 손익 {self._format_money(finance_data.get('monthly_profit_krw'))}" if finance_data.get("monthly_profit_krw") is not None else "",
            f"손익분기 {finance_data.get('break_even_units_per_day')}개/day" if finance_data.get("break_even_units_per_day") else "",
            f"리스크 등급 {finance_data.get('risk_grade')}" if finance_data.get("risk_grade") else "",
        ])
        operation_missing = operation_data.get("missing_inputs") or []
        operation_risks = operation_data.get("risk_items") or operation_data.get("risks") or []
        challenges = (debate_rounds or {}).get("challenges") or []

        lines = [
            f"정리하면, 지금은 `{top_idea_name}`을 바로 확정 창업안으로 밀기보다 30일 검증 아이템으로 잡는 게 가장 현실적입니다.",
            "Agent들이 각자 본 결론을 합치면 방향성은 괜찮지만, 재무 가정과 운영 데이터는 아직 확인이 필요해요.",
            "",
            "왜 이 방향이냐면",
        ]
        if profile_bits:
            lines.append(f"- 프로필: {', '.join(profile_bits)} 조건을 기준으로 봤습니다.")
        else:
            lines.append("- 프로필: 아직 사용자 조건이 충분히 고정되지 않아, 지역/예산/투입 시간을 먼저 확인해야 합니다.")

        idea_line = f"- 아이디어: `{top_idea_name}`이 1순위 후보입니다."
        if top_idea.get("match_score"):
            idea_line += f" 적합도는 {top_idea.get('match_score')}점으로 계산됐습니다."
        if idea_reason:
            idea_line += f" 이유는 {idea_reason}"
        lines.append(idea_line)

        if finance_bits:
            lines.append(f"- 재무: {', '.join(finance_bits)} 기준으로 봤습니다. 다만 실제 원가, 임대료, 판매량이 들어가야 확정 판단이 가능합니다.")
        else:
            lines.append("- 재무: 아직 초기 비용과 월 손익을 확정할 입력이 부족해서, 실제 원가와 고정비를 먼저 넣어야 합니다.")

        if policy_title:
            policy_line = f"- 지원사업: `{policy_title}`을 우선 후보로 봤습니다."
            if isinstance(policy_score, (int, float)):
                policy_line += f" 적합도는 {int(policy_score)}점입니다."
            policy_line += " 단, 모집 상태와 자격 요건은 실제 공고에서 다시 확인해야 합니다."
            lines.append(policy_line)

        marketing_line = "- 마케팅: 큰 캠페인보다 작은 콘텐츠 테스트로 문의 수와 저장 수를 먼저 보는 쪽이 맞습니다."
        if target or channel:
            marketing_line += f" 현재 가정은 타깃 {target or '확인 필요'}, 채널 {channel or '확인 필요'}입니다."
        lines.append(marketing_line)

        if operation_missing:
            lines.append(f"- 운영: {', '.join(map(str, operation_missing[:4]))} 데이터가 부족해서 운영 평가는 보수적으로 봐야 합니다.")
        elif operation_risks:
            risk_text = self._first_text(operation_risks[0])
            lines.append(f"- 운영: 가장 먼저 볼 리스크는 {risk_text}입니다.")
        else:
            lines.append("- 운영: 매출, 주문 수, 재고, 고객 피드백을 주간 단위로 쌓아야 다음 판단이 좋아집니다.")

        if challenges:
            lines.append("")
            lines.append("Agent들이 조심하자고 본 부분")
            for challenge in challenges[:3]:
                issue = str(challenge.get("issue") or "").strip()
                proposal = str(challenge.get("proposal") or "").strip()
                if issue and proposal:
                    lines.append(f"- {issue} 그래서 {proposal}")
                elif issue:
                    lines.append(f"- {issue}")

        lines.extend([
            "",
            "30일 실행안",
            "1. 1주차: 고객 또는 매장 후보 5~10곳을 인터뷰해서 실제 불편, 지불 의사, 구매 동선을 확인합니다.",
            "2. 2주차: 가장 작은 형태의 상품/서비스 설명서와 가격안을 만들고, 첫 유료 제안 1건을 목표로 테스트합니다.",
            "3. 3주차: 광고비를 크게 쓰기보다 릴스/게시글 1~2개로 문의 수, 저장 수, 상담 전환을 기록합니다.",
            "4. 4주차: 실제 반응, 예상 비용, 지원사업 자격을 합쳐 계속 진행/축소/전환 중 하나로 결정합니다.",
            "",
            "지금 바로 확인할 것",
            "- 주당 투입 가능 시간과 같이 일할 수 있는 인력",
            "- 실제 원가, 임대료 또는 장비비, 월 고정비",
            "- 첫 고객을 만날 채널과 검증 지표",
            "- 지원사업의 지역, 업력, 사업자등록, 제출 서류 조건",
            "",
            f"결론은 이거예요. `{top_idea_name}` 방향은 살릴 만하지만, 지금 답은 확정 판정이 아니라 검증 계획에 가깝습니다. 30일 동안 숫자를 모아서 재무와 운영 Agent가 다시 계산하게 만드는 게 다음 단계입니다.",
        ])
        return "\n".join(lines)

    def _format_money(self, value: object) -> str:
        if isinstance(value, (int, float)):
            return f"{int(value):,}원"
        return str(value).strip() if value is not None else ""

    def _first_text(self, *values: object) -> str:
        for value in values:
            if isinstance(value, list):
                for item in value:
                    text = self._first_text(item)
                    if text:
                        return text
            elif isinstance(value, dict):
                for key in ("summary", "text", "description", "reason", "risk", "title", "name"):
                    text = str(value.get(key) or "").strip()
                    if text:
                        return text
            else:
                text = str(value or "").strip()
                if text:
                    return text
        return ""

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
