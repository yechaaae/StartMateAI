from fastapi import APIRouter

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
    FinanceRequest,
    IdeaRequest,
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
retriever = SupportProgramRetriever.from_default()

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
    }


@router.post("/ai/chat", response_model=AgentResponse)
async def chat(request: ChatRequest) -> AgentResponse:
    response = await orchestrator.run(request)
    if response.intent == "simulation" and response.data.get("state"):
        simulation_sessions[response.data["session_id"]] = response.data["state"]
    return response


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
