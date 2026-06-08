from __future__ import annotations

import asyncio

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
        intent = request.intent if request.intent != "auto" else self._detect_intent(request.message)

        if intent == "profile":
            result = await self.profile_agent.run(ProfileRequest(profile=request.profile, question=request.message))
        elif intent == "idea":
            result = await self.idea_agent.run(IdeaRequest(profile=request.profile))
        elif intent == "policy":
            result = await self.policy_agent.run(PolicyRequest(profile=request.profile, query=request.message))
        elif intent == "finance":
            result = await self.finance_agent.run(FinanceRequest(profile=request.profile))
        elif intent == "operation":
            result = await self.operation_agent.run(
                OperationRequest(profile=request.profile, business_name=request.context.get("business_name", "테스트 매장"))
            )
        elif intent == "marketing":
            result = await self.marketing_agent.run(
                MarketingRequest(
                    profile=request.profile,
                    product_name=request.context.get("product_name", "창업 상품"),
                    event_date=request.context.get("event_date"),
                    target_customer=request.context.get("target_customer"),
                    place=request.context.get("place"),
                    brand_tone=request.context.get("brand_tone", "친근하고 실행력 있는"),
                    goal=request.message,
                )
            )
        elif intent == "simulation":
            result = self.simulation_agent.start(self._simulation_start_request(request))
        elif intent in {"collaboration", "roadmap"}:
            result = await self._collaborative_consultation(request)
        else:
            result = await self._collaborative_consultation(request)

        result.data["routed_by"] = self.name
        result.data["user_message"] = request.message
        return result

    def _detect_intent(self, message: str) -> str:
        text = message.lower()
        if any(keyword in text for keyword in ["지원사업", "공고", "정책", "서류", "마감"]):
            return "policy"
        if any(keyword in text for keyword in ["아이템", "추천", "창업 뭐", "무슨 창업"]):
            return "idea"
        if any(keyword in text for keyword in ["게임", "체험", "선택지", "30일", "이벤트"]):
            return "simulation"
        if any(keyword in text for keyword in ["비용", "매출", "손익", "시뮬레이션", "bep"]):
            return "finance"
        if any(keyword in text for keyword in ["운영", "재고", "리뷰", "피드백", "매장"]):
            return "operation"
        if any(keyword in text for keyword in ["sns", "홍보", "릴스", "게시글", "해시태그"]):
            return "marketing"
        if any(keyword in text for keyword in ["프로필", "분석", "강점", "조건"]):
            return "profile"
        if any(keyword in text for keyword in ["협업", "토론", "전체", "로드맵", "상담", "시작"]):
            return "collaboration"
        return "collaboration"

    def _simulation_start_request(self, request: ChatRequest) -> SimulationStartRequest:
        business_type = request.context.get("business_type", "content")
        if business_type not in {"cafe", "commerce", "content", "popup", "service"}:
            business_type = "content"
        difficulty = request.context.get("difficulty", "normal")
        if difficulty not in {"easy", "normal", "hard"}:
            difficulty = "normal"
        return SimulationStartRequest(
            profile=request.profile,
            item_name=request.context.get("item_name", "로컬 SNS 콘텐츠 스튜디오"),
            business_type=business_type,
            difficulty=difficulty,
            seed=request.context.get("seed"),
        )

    async def _collaborative_consultation(self, request: ChatRequest) -> AgentResponse:
        profile_task = self.profile_agent.run(ProfileRequest(profile=request.profile, question=request.message))
        ideas_task = self.idea_agent.run(IdeaRequest(profile=request.profile, count=3))
        policies_task = self.policy_agent.run(PolicyRequest(profile=request.profile, query=request.message, limit=3))
        profile, ideas, policies = await asyncio.gather(profile_task, ideas_task, policies_task)

        top_idea = self._pick_top_idea(ideas)
        top_idea_name = str(top_idea.get("title", "창업 아이템"))

        finance_task = self.finance_agent.run(
            FinanceRequest(
                profile=request.profile,
                assumption=FinanceAssumption(item_name=top_idea_name),
            )
        )
        marketing_task = self.marketing_agent.run(
            MarketingRequest(
                profile=request.profile,
                product_name=top_idea_name,
                target_customer=request.context.get("target_customer"),
                place=request.context.get("place"),
                brand_tone=request.context.get("brand_tone", "친근하고 실행력 있는"),
                goal=request.message,
            )
        )
        operation_task = self.operation_agent.run(
            OperationRequest(profile=request.profile, business_name=top_idea_name)
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
