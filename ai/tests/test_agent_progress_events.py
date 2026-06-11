from __future__ import annotations

import unittest

from app.agents.orchestrator import OrchestratorAgent
from app.rabbitmq_worker import progress_event_to_envelope
from app.schemas import AgentResponse, ChatRequest, StartupProfile


class FakeLlm:
    is_enabled = False


class FakeAgent:
    def __init__(self, name: str, intent: str):
        self.name = name
        self.intent = intent

    async def run(self, _request) -> AgentResponse:
        return AgentResponse(
            intent=self.intent,
            agent=self.name,
            summary=f"{self.name} 검토 완료",
            data={
                "position": f"{self.name} 입장",
                "evidence": {"source": "test"},
                "score": 70,
                "recommendation": f"{self.name} 추천",
            },
        )


class FakeProfileAgent(FakeAgent):
    async def build_effective_profile_async(self, profile: StartupProfile, _message: str) -> StartupProfile:
        return profile


class FakeFinanceAgent(FakeAgent):
    llm = FakeLlm()


def build_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent(
        profile_agent=FakeProfileAgent("ProfileAgent", "profile"),
        idea_agent=FakeAgent("IdeaAgent", "idea"),
        policy_agent=FakeAgent("PolicyAgent", "policy"),
        legal_agent=FakeAgent("LegalAgent", "legal"),
        finance_agent=FakeFinanceAgent("FinanceAgent", "finance"),
        operation_agent=FakeAgent("OperationAgent", "operation"),
        plan_agent=FakeAgent("PlanAgent", "plan"),
        marketing_agent=FakeAgent("MarketingAgent", "marketing"),
        commercial_area_agent=FakeAgent("CommercialAreaAgent", "commercial_area"),
        simulation_agent=FakeAgent("SimulationAgent", "simulation"),
    )


class AgentProgressEventsTest(unittest.IsolatedAsyncioTestCase):
    async def test_orchestrator_emits_progress_events_for_selected_agents(self):
        events: list[dict] = []

        async def capture(event: dict) -> None:
            events.append(event)

        orchestrator = build_orchestrator()

        response = await orchestrator.run(
            ChatRequest(
                message="서울 마포구 연남동 카페 창업 지원사업이랑 상권 봐줘",
                profile=StartupProfile(region="서울", interests=["카페"]),
            ),
            progress_callback=capture,
        )

        event_types = [event["eventType"] for event in events]
        self.assertIn("agents.selected", event_types)
        self.assertIn("agent.started", event_types)
        self.assertIn("agent.completed", event_types)
        self.assertIn("orchestrator.synthesizing", event_types)
        self.assertIn("orchestrator.completed", event_types)

        selected_event = next(event for event in events if event["eventType"] == "agents.selected")
        selected_keys = {agent["agentKey"] for agent in selected_event["selectedAgents"]}
        self.assertIn("PolicyAgent", selected_keys)
        self.assertIn("CommercialAreaAgent", selected_keys)
        self.assertEqual(response.agent, "OrchestratorAgent")
        self.assertEqual(response.data["collaboration_mode"], "selective_dynamic_agents")

    async def test_orchestrator_emits_completed_event_for_single_agent_response(self):
        events: list[dict] = []

        async def capture(event: dict) -> None:
            events.append(event)

        orchestrator = build_orchestrator()

        response = await orchestrator.run(
            ChatRequest(
                message="지원사업 공고 마감 알려줘",
                profile=StartupProfile(region="서울", interests=["카페"]),
            ),
            progress_callback=capture,
        )

        event_types = [event["eventType"] for event in events]
        self.assertIn("agents.selected", event_types)
        self.assertIn("agent.started", event_types)
        self.assertIn("agent.completed", event_types)
        self.assertIn("orchestrator.completed", event_types)
        self.assertEqual(response.agent, "PolicyAgent")

    async def test_feature_report_request_uses_fixed_agent_team_and_attaches_result(self):
        events: list[dict] = []

        async def capture(event: dict) -> None:
            events.append(event)

        orchestrator = build_orchestrator()

        response = await orchestrator.run(
            ChatRequest(
                message="사업계획서 초안 리포트를 만들어줘",
                profile=StartupProfile(region="서울", interests=["카페"]),
                context={
                    "featureContext": {"featureKey": "PLAN"},
                    "requestMetadata": {"reportGeneration": True},
                },
            ),
            progress_callback=capture,
        )

        selected_event = next(event for event in events if event["eventType"] == "agents.selected")
        selected_keys = [agent["agentKey"] for agent in selected_event["selectedAgents"]]
        self.assertEqual(
            selected_keys,
            ["ProfileAgent", "IdeaAgent", "PolicyAgent", "PlanAgent", "FinanceAgent", "CommercialAreaAgent"],
        )
        event_types = [event["eventType"] for event in events]
        self.assertIn("feature_review.started", event_types)
        self.assertIn("feature_review.completed", event_types)
        self.assertIsNotNone(response.result)
        self.assertEqual(response.result["targetFeature"], "PLAN")
        self.assertEqual(response.result["payload"]["featureId"], "plan")
        self.assertIn("reportData", response.result["payload"])
        self.assertIn("agentReview", response.result["payload"]["reportData"])

    async def test_feature_chat_without_update_intent_does_not_attach_result(self):
        orchestrator = build_orchestrator()

        response = await orchestrator.run(
            ChatRequest(
                message="이 리포트에서 손익분기 의미만 설명해줘",
                profile=StartupProfile(region="서울", interests=["카페"]),
                context={"featureContext": {"featureKey": "ITEM"}},
            ),
        )

        self.assertIsNone(response.result)


class RabbitMqProgressEnvelopeTest(unittest.TestCase):
    def test_progress_event_maps_to_agent_event_envelope(self):
        envelope = progress_event_to_envelope(
            {
                "requestId": "req-1",
                "roomId": 10,
                "userId": 2,
                "targetFeature": "SUPPORT",
            },
            {
                "eventType": "agent.started",
                "orchestrator": "OrchestratorAgent",
                "status": "PROCESSING",
                "message": "지원사업 Agent가 지원사업 추천을 시작했습니다.",
                "agent": {
                    "agentKey": "PolicyAgent",
                    "label": "지원사업 Agent",
                    "role": "지원사업 추천",
                    "status": "running",
                },
                "selectedAgents": [],
            },
            3,
        )

        self.assertEqual(envelope["messageType"], "AGENT_EVENT")
        self.assertEqual(envelope["requestId"], "req-1")
        self.assertEqual(envelope["roomId"], 10)
        self.assertEqual(envelope["targetFeature"], "SUPPORT")
        self.assertEqual(envelope["status"], "PROCESSING")
        self.assertEqual(envelope["payload"]["eventType"], "agent.started")
        self.assertEqual(envelope["payload"]["sequence"], 3)
        self.assertEqual(envelope["payload"]["agent"]["agentKey"], "PolicyAgent")


if __name__ == "__main__":
    unittest.main()
