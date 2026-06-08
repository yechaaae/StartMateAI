import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.finance import FinanceAgent
from app.agents.idea import IdeaAgent
from app.agents.marketing import MarketingAgent
from app.agents.operation import OperationAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.policy import PolicyAgent
from app.agents.profile import ProfileAgent
from app.agents.simulation import SimulationAgent
from app.core.config import get_settings
from app.core.gms_client import GMSClient
from app.rag.retriever import SupportProgramRetriever
from app.schemas import (
    AgentResponse,
    ChatRequest,
    FinanceAssumption,
    FinanceRequest,
    IdeaRequest,
    LLMChatRequest,
    MarketingRequest,
    OperationRequest,
    PolicyRequest,
    ProfileRequest,
    SimulationChoiceRequest,
    SimulationStartRequest,
)

router = APIRouter()

settings = get_settings()
llm = GMSClient(settings)
retriever = SupportProgramRetriever.from_default(
    retrieval_mode=settings.rag_retrieval_mode,
    vector_store_path=settings.rag_vector_store_path or None,
    embedding_dimensions=settings.rag_embedding_dimensions,
)

profile_agent = ProfileAgent(llm)
idea_agent = IdeaAgent(llm)
policy_agent = PolicyAgent(llm, retriever)
finance_agent = FinanceAgent(llm)
operation_agent = OperationAgent(llm)
marketing_agent = MarketingAgent(llm)
simulation_agent = SimulationAgent(llm)
simulation_sessions: dict[str, dict] = {}

orchestrator = OrchestratorAgent(
    profile_agent=profile_agent,
    idea_agent=idea_agent,
    policy_agent=policy_agent,
    finance_agent=finance_agent,
    operation_agent=operation_agent,
    marketing_agent=marketing_agent,
    simulation_agent=simulation_agent,
)


@router.get("/health")
async def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "mock_llm": settings.use_mock_llm,
        "gms_configured": llm.is_configured,
        "rag_retrieval_mode": retriever.retrieval_mode,
        "rag_vector_store": retriever.vector_store is not None,
    }


@router.post("/ai/chat", response_model=AgentResponse)
async def chat(request: ChatRequest) -> AgentResponse:
    response = await orchestrator.run(request)
    if response.intent == "simulation" and response.data.get("state"):
        simulation_sessions[response.data["session_id"]] = response.data["state"]
    return response


@router.post("/ai/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _multi_agent_event_stream(request),
        media_type="application/x-ndjson; charset=utf-8",
    )


async def _multi_agent_event_stream(request: ChatRequest) -> AsyncIterator[str]:
    def event(name: str, data: dict) -> str:
        return json.dumps({"event": name, "data": data}, ensure_ascii=False) + "\n"

    def response_view(response: AgentResponse) -> dict:
        return {
            "agent": response.agent,
            "intent": response.intent,
            "summary": response.summary,
            "position": response.data.get("position"),
            "score": response.data.get("score"),
            "risks": response.data.get("risks", []),
            "missing_inputs": response.data.get("missing_inputs", []),
            "recommendation": response.data.get("recommendation"),
            "data": response.data,
        }

    async def run_named(name: str, coro) -> tuple[str, AgentResponse]:
        result = await coro
        return name, result

    if request.intent not in {"auto", "collaboration", "roadmap"}:
        yield event("start", {"message": "단일 에이전트 요청을 실행합니다.", "intent": request.intent})
        response = await orchestrator.run(request)
        yield event("agent_result", response_view(response))
        yield event("final", response.model_dump(mode="json"))
        return

    yield event(
        "start",
        {
            "message": "협업형 멀티에이전트 토론을 시작합니다.",
            "requested_intent": request.intent,
        },
    )

    yield event(
        "round_start",
        {
            "round": 1,
            "title": "1차 의견 수집",
            "agents": ["ProfileAgent", "IdeaAgent", "PolicyAgent"],
            "purpose": "사용자 조건, 아이템 후보, 지원사업 가능성을 동시에 검토합니다.",
        },
    )
    round1_tasks = [
        asyncio.create_task(
            run_named("ProfileAgent", profile_agent.run(ProfileRequest(profile=request.profile, question=request.message)))
        ),
        asyncio.create_task(run_named("IdeaAgent", idea_agent.run(IdeaRequest(profile=request.profile, count=3)))),
        asyncio.create_task(
            run_named("PolicyAgent", policy_agent.run(PolicyRequest(profile=request.profile, query=request.message, limit=3)))
        ),
    ]
    round1: dict[str, AgentResponse] = {}
    for task in asyncio.as_completed(round1_tasks):
        name, result = await task
        round1[name] = result
        yield event("agent_result", {"round": 1, **response_view(result)})

    yield event(
        "round_end",
        {
            "round": 1,
            "message": "1차 의견 수집이 끝났습니다.",
            "completed_agents": list(round1),
        },
    )

    top_idea = orchestrator._pick_top_idea(round1["IdeaAgent"])
    top_idea_name = str(top_idea.get("title", "창업 아이템"))
    round1_synthesis = orchestrator._build_round1_synthesis(
        round1["ProfileAgent"],
        round1["IdeaAgent"],
        round1["PolicyAgent"],
    )
    yield event(
        "orchestrator_step",
        {
            "step": "후보 압축",
            "message": f"IdeaAgent의 1순위 후보인 {top_idea_name}을 기준 아이템으로 선택했습니다.",
            "selected_idea": top_idea,
            "round1_synthesis": round1_synthesis,
        },
    )

    yield event(
        "round_start",
        {
            "round": 2,
            "title": "2차 검증",
            "agents": ["FinanceAgent", "MarketingAgent", "OperationAgent"],
            "purpose": "기준 아이템의 비용, 홍보, 운영 리스크를 동시에 검증합니다.",
        },
    )
    round2_tasks = [
        asyncio.create_task(
            run_named(
                "FinanceAgent",
                finance_agent.run(
                    FinanceRequest(
                        profile=request.profile,
                        assumption=FinanceAssumption(item_name=top_idea_name),
                    )
                ),
            )
        ),
        asyncio.create_task(
            run_named(
                "MarketingAgent",
                marketing_agent.run(
                    MarketingRequest(
                        profile=request.profile,
                        product_name=top_idea_name,
                        target_customer=request.context.get("target_customer"),
                        place=request.context.get("place"),
                        brand_tone=request.context.get("brand_tone", "친근하고 실행력 있는"),
                        goal=request.message,
                    )
                ),
            )
        ),
        asyncio.create_task(
            run_named(
                "OperationAgent",
                operation_agent.run(OperationRequest(profile=request.profile, business_name=top_idea_name)),
            )
        ),
    ]
    round2: dict[str, AgentResponse] = {}
    for task in asyncio.as_completed(round2_tasks):
        name, result = await task
        round2[name] = result
        yield event("agent_result", {"round": 2, **response_view(result)})

    yield event(
        "round_end",
        {
            "round": 2,
            "message": "2차 검증이 끝났습니다.",
            "completed_agents": list(round2),
        },
    )

    profile = round1["ProfileAgent"]
    ideas = round1["IdeaAgent"]
    policies = round1["PolicyAgent"]
    finance = round2["FinanceAgent"]
    marketing = round2["MarketingAgent"]
    operation = round2["OperationAgent"]
    debate = orchestrator._build_debate(profile, ideas, policies, finance, marketing, operation)

    yield event(
        "orchestrator_step",
        {
            "step": "충돌 조정",
            "message": "에이전트 의견의 충돌 지점을 정리하고 실행 순서를 조정합니다.",
            "conflicts": debate.get("conflicts", []),
        },
    )

    final_data = {
        "collaboration_mode": "streaming_parallel_multi_agent",
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
            orchestrator._contract_summary(profile),
            orchestrator._contract_summary(ideas),
            orchestrator._contract_summary(policies),
            orchestrator._contract_summary(finance),
            orchestrator._contract_summary(marketing),
            orchestrator._contract_summary(operation),
        ],
        "debate": debate,
        "recommended_flow": [
            "프로필 제약조건 확정",
            f"{top_idea_name} 기준 30일 테스트 설계",
            "초기 현금 필요액과 손익분기점 재검산",
            "지원사업 상위 후보 신청 가능성 확인",
            "SNS 홍보 소재 제작 후 고객 반응 측정",
        ],
    }
    final_response = AgentResponse(
        intent="collaboration",
        agent=orchestrator.name,
        summary=(
            "여러 전문 에이전트가 순차 라운드로 의견을 제시했고, Orchestrator가 충돌을 조정해 "
            f"{top_idea_name} 중심의 실행안을 합의했습니다."
        ),
        data=final_data,
        next_actions=[
            "선정 아이템의 실제 고객 5명을 인터뷰",
            "임대료, 예상 방문자 수, 객단가를 실제 값으로 입력",
            "지원사업 상위 후보의 신청 서류 체크리스트 작성",
            "SNS 테스트 콘텐츠 1개를 제작해 반응 측정",
        ],
        sources=policies.sources,
        warnings=policies.warnings,
    )
    yield event("final", final_response.model_dump(mode="json"))


@router.post("/ai/llm/chat", response_model=AgentResponse)
async def llm_chat(request: LLMChatRequest) -> AgentResponse:
    answer = await llm.complete(
        system_prompt=request.system_prompt,
        user_prompt=request.message,
        temperature=request.temperature,
        fallback=(
            "Mock LLM response: USE_MOCK_LLM=false와 GMS_API_KEY를 설정하면 "
            "GMS Gemini 응답이 여기에 표시됩니다."
        ),
    )
    return AgentResponse(
        intent="llm",
        agent="GMSClient",
        summary=answer,
        data={
            "model": settings.gms_model,
            "mock_llm": settings.use_mock_llm,
            "gms_configured": llm.is_configured,
            "temperature": request.temperature,
        },
    )


@router.post("/ai/profile/analyze", response_model=AgentResponse)
async def analyze_profile(request: ProfileRequest) -> AgentResponse:
    return await profile_agent.run(request)


@router.post("/ai/ideas/recommend", response_model=AgentResponse)
async def recommend_ideas(request: IdeaRequest) -> AgentResponse:
    return await idea_agent.run(request)


@router.post("/ai/policies/match", response_model=AgentResponse)
async def match_policies(request: PolicyRequest) -> AgentResponse:
    return await policy_agent.run(request)


@router.post("/ai/finance/simulate", response_model=AgentResponse)
async def simulate_finance(request: FinanceRequest) -> AgentResponse:
    return await finance_agent.run(request)


@router.post("/ai/simulation/start", response_model=AgentResponse)
async def start_simulation(request: SimulationStartRequest) -> AgentResponse:
    response = simulation_agent.start(request)
    simulation_sessions[response.data["session_id"]] = response.data["state"]
    return response


@router.post("/ai/simulation/choose", response_model=AgentResponse)
async def choose_simulation(request: SimulationChoiceRequest) -> AgentResponse:
    state = simulation_sessions.get(request.session_id)
    if state is None:
        return AgentResponse(
            intent="simulation",
            agent=simulation_agent.name,
            summary="시뮬레이션 세션을 찾을 수 없습니다. 새 시뮬레이션을 시작해주세요.",
            data={"session_id": request.session_id},
            warnings=["simulation_session_not_found"],
        )
    response = simulation_agent.choose(state, request.choice_id)
    simulation_sessions[request.session_id] = response.data["state"]
    return response


@router.post("/ai/operations/feedback", response_model=AgentResponse)
async def operation_feedback(request: OperationRequest) -> AgentResponse:
    return await operation_agent.run(request)


@router.post("/ai/marketing/sns", response_model=AgentResponse)
async def create_sns_plan(request: MarketingRequest) -> AgentResponse:
    return await marketing_agent.run(request)
