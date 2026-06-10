import asyncio
import json
from typing import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agents.finance import FinanceAgent
from app.agents.idea import IdeaAgent
from app.agents.legal import LegalAgent
from app.agents.marketing import MarketingAgent
from app.agents.commercial_area import CommercialAreaAgent
from app.agents.operation import OperationAgent
from app.agents.orchestrator import OrchestratorAgent
from app.agents.policy import PolicyAgent
from app.agents.profile import ProfileAgent
from app.agents.simulation import SimulationAgent
from app.core.config import get_settings
from app.core.backend_tools import BackendToolClient
from app.core.gms_client import GMSClient
from app.rag.retriever import SupportProgramRetriever
from app.rag.support_chroma_retriever import SupportProgramChromaRetriever
from app.rag.legal_retriever import LegalRetriever
from app.schemas import (
    AgentResponse,
    ChatRequest,
    CommercialAreaRequest,
    FinanceAssumption,
    FinanceRequest,
    IdeaRequest,
    LegalRequest,
    LLMChatRequest,
    MarketingRequest,
    OperationRequest,
    PolicyRequest,
    ProfileRequest,
    SimulationChoiceRequest,
    SimulationStartRequest,
    StartupProfile,
)

router = APIRouter()

settings = get_settings()
llm = GMSClient(settings)
backend_tools = BackendToolClient(settings)
if settings.support_rag_chroma_enabled:
    retriever = SupportProgramChromaRetriever(
        chroma_path=settings.support_rag_chroma_path,
        collection_name=settings.support_rag_chroma_collection,
        embedding_dimensions=settings.rag_embedding_dimensions,
        embedding_provider=settings.rag_embedding_provider,
    )
else:
    retriever = SupportProgramRetriever.from_default(
        retrieval_mode=settings.rag_retrieval_mode,
        vector_store_path=settings.rag_vector_store_path or None,
        embedding_dimensions=settings.support_rag_embedding_dimensions,
    )
legal_retriever = LegalRetriever(
    chroma_path=settings.rag_chroma_path,
    embedding_dimensions=settings.rag_embedding_dimensions,
    embedding_provider=settings.rag_embedding_provider,
)

profile_agent = ProfileAgent(llm)
idea_agent = IdeaAgent(llm)
policy_agent = PolicyAgent(llm, retriever, backend_tools)
legal_agent = LegalAgent(llm, legal_retriever)
finance_agent = FinanceAgent(llm)
operation_agent = OperationAgent(llm)
marketing_agent = MarketingAgent(llm)
commercial_area_agent = CommercialAreaAgent(llm, backend_tools)
simulation_agent = SimulationAgent(llm)
simulation_sessions: dict[str, dict] = {}
chat_sessions: dict[str, dict] = {}

orchestrator = OrchestratorAgent(
    profile_agent=profile_agent,
    idea_agent=idea_agent,
    policy_agent=policy_agent,
    legal_agent=legal_agent,
    finance_agent=finance_agent,
    operation_agent=operation_agent,
    marketing_agent=marketing_agent,
    commercial_area_agent=commercial_area_agent,
    simulation_agent=simulation_agent,
)


@router.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "mock_llm": settings.use_mock_llm,
        "gms_configured": llm.is_configured,
        "rag_retrieval_mode": retriever.retrieval_mode,
        "rag_vector_store": retriever.vector_store is not None,
        "legal_vector_store_count": legal_retriever.count(),
    }


@router.post("/ai/chat", response_model=AgentResponse)
async def chat(request: ChatRequest) -> AgentResponse:
    session_id, stateful_request = _stateful_chat_request(request)
    response = await orchestrator.run(stateful_request)
    _remember_chat_response(session_id, stateful_request, response)
    response.data["chat_session_id"] = session_id
    response.data["memory"] = _memory_view(session_id)
    if response.intent == "simulation" and response.data.get("state"):
        simulation_sessions[response.data["session_id"]] = response.data["state"]
    return response


@router.post("/ai/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    session_id, stateful_request = _stateful_chat_request(request)
    return StreamingResponse(
        _multi_agent_event_stream(stateful_request, session_id=session_id),
        media_type="application/x-ndjson; charset=utf-8",
    )


def _stateful_chat_request(request: ChatRequest) -> tuple[str, ChatRequest]:
    session_id = request.session_id or str(request.context.get("session_id") or uuid4())
    stored = chat_sessions.get(session_id, {})
    stored_profile = stored.get("profile")
    merged_profile = _merge_profiles(stored_profile, request.profile)
    context = dict(request.context)
    context["session_id"] = session_id
    if stored.get("messages"):
        context["chat_memory"] = stored["messages"][-8:]
    return session_id, request.model_copy(update={"profile": merged_profile, "session_id": session_id, "context": context})


def _merge_profiles(previous: dict | StartupProfile | None, current: StartupProfile) -> StartupProfile:
    data = {}
    if previous:
        data.update(previous.model_dump() if isinstance(previous, StartupProfile) else previous)
    current_data = current.model_dump()
    list_fields = {
        "experiences",
        "owned_assets",
        "customer_network",
        "confirmed_absent_fields",
        "interests",
        "preferred_channels",
        "preferred_business_types",
        "avoid_business_types",
    }
    for key, value in current_data.items():
        if key in list_fields:
            data[key] = _ordered_unique([*(data.get(key) or []), *(value or [])])
            if key == "experiences" and value:
                data["confirmed_absent_fields"] = [
                    item for item in data.get("confirmed_absent_fields", []) if item != "experiences"
                ]
        elif _is_informative_profile_value(key, value, data):
            data[key] = value
        elif key not in data:
            data[key] = value
    return StartupProfile.model_validate(data)


def _is_informative_profile_value(key: str, value, existing_data: dict) -> bool:
    if value in {None, ""}:
        return False
    if key == "risk_tolerance" and value == "medium" and existing_data.get(key):
        return False
    if key == "startup_stage" and value == StartupProfile().startup_stage and existing_data.get(key):
        return False
    return True


def _remember_chat_response(session_id: str, request: ChatRequest, response: AgentResponse) -> None:
    profile = _extract_effective_profile(response) or request.profile.model_dump()
    session = chat_sessions.setdefault(session_id, {"messages": []})
    session["profile"] = profile
    session["last_response_intent"] = response.intent
    session["last_agent"] = response.agent
    session["messages"].append({"role": "user", "content": request.message})
    session["messages"].append({"role": "assistant", "content": response.summary})
    session["messages"] = session["messages"][-12:]


def _extract_effective_profile(response: AgentResponse) -> dict | None:
    data = response.data or {}
    if isinstance(data.get("effective_profile"), dict):
        return data["effective_profile"]
    profile_data = data.get("profile")
    if isinstance(profile_data, dict) and isinstance(profile_data.get("effective_profile"), dict):
        return profile_data["effective_profile"]
    return None


def _memory_view(session_id: str) -> dict:
    session = chat_sessions.get(session_id, {})
    return {
        "session_id": session_id,
        "profile": session.get("profile"),
        "message_count": len(session.get("messages", [])),
        "last_agent": session.get("last_agent"),
        "last_response_intent": session.get("last_response_intent"),
    }


def _ordered_unique(values: list) -> list:
    seen = set()
    result = []
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(value)
    return result


async def _multi_agent_event_stream(request: ChatRequest, *, session_id: str) -> AsyncIterator[str]:
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

    def selective_agent_views(response: AgentResponse) -> list[dict]:
        agent_by_intent = {
            "profile": "ProfileAgent",
            "idea": "IdeaAgent",
            "policy": "PolicyAgent",
            "legal": "LegalAgent",
            "finance": "FinanceAgent",
            "operation": "OperationAgent",
            "marketing": "MarketingAgent",
            "simulation": "SimulationAgent",
        }
        data = response.data or {}
        results = data.get("agent_results") or {}
        selected = data.get("selected_intents") or list(results)
        views = []
        for intent in selected:
            detail = results.get(intent)
            if not isinstance(detail, dict):
                continue
            views.append(
                {
                    "agent": agent_by_intent.get(intent, intent),
                    "intent": intent,
                    "summary": detail.get("recommendation") or detail.get("position") or "",
                    "position": detail.get("position"),
                    "score": detail.get("score"),
                    "risks": detail.get("risks", []),
                    "missing_inputs": detail.get("missing_inputs", []),
                    "recommendation": detail.get("recommendation"),
                    "data": detail,
                }
            )
        return views

    async def run_named(name: str, coro) -> tuple[str, AgentResponse]:
        result = await coro
        return name, result

    plan_meta = {"source": "explicit_intent"}
    if request.intent == "auto":
        agent_plan, plan_meta = await orchestrator.plan_agents(request)
    else:
        agent_plan = [request.intent]
    stream_intent = "selective_collaboration" if len(agent_plan) > 1 else agent_plan[0]

    if stream_intent == "selective_collaboration":
        yield event(
            "start",
            {
                "message": "질문에 필요한 에이전트만 선택해 실행합니다.",
                "selected_intents": agent_plan,
                "planner": plan_meta,
                "chat_session_id": session_id,
                "memory": _memory_view(session_id),
            },
        )
        response = await orchestrator.run(request)
        _remember_chat_response(session_id, request, response)
        response.data["chat_session_id"] = session_id
        response.data["memory"] = _memory_view(session_id)
        for view in selective_agent_views(response):
            yield event("agent_result", view)
        yield event("final", response.model_dump(mode="json"))
        return

    if stream_intent not in {"auto", "collaboration", "roadmap"}:
        single_agent_request = request if request.intent == "auto" else request.model_copy(update={"intent": stream_intent})
        yield event(
            "start",
            {
                "message": "단일 에이전트로 시작하고 필요하면 후속 에이전트를 실행합니다.",
                "intent": stream_intent,
                "planner": plan_meta,
                "chat_session_id": session_id,
                "memory": _memory_view(session_id),
            },
        )
        response = await orchestrator.run(single_agent_request)
        _remember_chat_response(session_id, single_agent_request, response)
        response.data["chat_session_id"] = session_id
        response.data["memory"] = _memory_view(session_id)
        if response.intent == "selective_collaboration":
            for view in selective_agent_views(response):
                yield event("agent_result", view)
        else:
            yield event("agent_result", response_view(response))
        yield event("final", response.model_dump(mode="json"))
        return

    yield event(
        "start",
        {
            "message": "협업형 멀티에이전트 토론을 시작합니다.",
            "requested_intent": stream_intent,
            "chat_session_id": session_id,
            "memory": _memory_view(session_id),
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
    effective_profile = await profile_agent.build_effective_profile_async(request.profile, request.message)
    round1_tasks = [
        asyncio.create_task(
            run_named(
                "ProfileAgent",
                profile_agent.run(
                    ProfileRequest(profile=effective_profile, question=request.message, use_llm_extraction=False)
                ),
            )
        ),
        asyncio.create_task(run_named("IdeaAgent", idea_agent.run(IdeaRequest(profile=effective_profile, count=3)))),
        asyncio.create_task(
            run_named(
                "PolicyAgent",
                policy_agent.run(PolicyRequest(profile=effective_profile, query=request.message, limit=3, context=request.context)),
            )
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
            "step": "후보 선정",
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
                        profile=effective_profile,
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
                        profile=effective_profile,
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
                operation_agent.run(OperationRequest(profile=effective_profile, business_name=top_idea_name)),
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
            "초기 현금 필요액과 손익분기점 재계산",
            "지원사업 상위 후보 신청 가능성 확인",
            "SNS 홍보 소재 제작 후 고객 반응 측정",
        ],
    }
    final_response = AgentResponse(
        intent="collaboration",
        agent=orchestrator.name,
        summary=(
            "여러 전문 에이전트가 동시에 후보를 검토했고, Orchestrator가 충돌을 조정해 "
            f"{top_idea_name} 중심의 실행안을 합의했습니다."
        ),
        data=final_data,
        next_actions=[
            "선정 아이템의 실제 고객 5명을 인터뷰",
            "재료비, 예상 방문수, 객단가를 실제 값으로 입력",
            "지원사업 상위 후보의 신청 서류 체크리스트 작성",
            "SNS 테스트 콘텐츠 1개를 제작해 반응 측정",
        ],
        sources=policies.sources,
        warnings=policies.warnings,
    )
    _remember_chat_response(session_id, request, final_response)
    final_response.data["chat_session_id"] = session_id
    final_response.data["memory"] = _memory_view(session_id)
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


@router.post("/ai/legal/check", response_model=AgentResponse)
async def check_legal(request: LegalRequest) -> AgentResponse:
    return await legal_agent.run(request)


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
