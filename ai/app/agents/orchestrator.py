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
        if any(keyword in text for keyword in ["협업", "토론", "전체", "로드맵", "상담", "시작"]):
            return "collaboration"
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
        round1_synthesis = self._build_round1_synthesis(profile, ideas, policies)

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
