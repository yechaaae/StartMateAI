from __future__ import annotations

import unittest

from app.agents.commercial_area import CommercialAreaAgent
from app.agents.policy import PolicyAgent
from app.rabbitmq_worker import request_from_envelope
from app.rag.retriever import SupportProgramRetriever
from app.schemas import CommercialAreaRequest, PolicyRequest, StartupProfile


class FakeLlm:
    is_enabled = False


class ReferenceDataIntegrationTest(unittest.IsolatedAsyncioTestCase):
    def test_rabbitmq_envelope_maps_to_chat_request_with_reference_context(self):
        chat_request = request_from_envelope(
            {
                "requestId": "req-1",
                "roomId": 10,
                "targetFeature": "SUPPORT",
                "payload": {
                    "common": {"message": "서울 마포구 연남동 카페 창업이면 지원사업이랑 상권 봐줘"},
                    "profile": {
                        "region": "서울",
                        "budgetKrw": 3000000,
                        "interests": ["카페"],
                        "startupStage": "예비창업",
                    },
                    "reference": {
                        "externalData": {
                            "supportPrograms": {"items": [{"title": "청년 예비창업 패키지"}]},
                            "commercialArea": {"directCompetitors": 5, "competitionLevel": "low"},
                        }
                    },
                },
            }
        )

        self.assertEqual(chat_request.intent, "policy")
        self.assertEqual(chat_request.profile.budget_krw, 3000000)
        self.assertIn("reference", chat_request.context)
        self.assertIn("supportPrograms", chat_request.context["reference"]["externalData"])

    async def test_policy_agent_prefers_backend_support_program_reference(self):
        agent = PolicyAgent(FakeLlm(), SupportProgramRetriever([]))

        response = await agent.run(
            PolicyRequest(
                profile=StartupProfile(region="서울", interests=["카페"], startup_stage="예비창업"),
                query="지원사업 추천해줘",
                limit=3,
                context={
                    "reference": {
                        "externalData": {
                            "supportPrograms": {
                                "items": [
                                    {
                                        "programId": 1,
                                        "title": "청년 예비창업 패키지",
                                        "source": "kstartup",
                                        "summary": "사업화 자금과 멘토링 지원",
                                        "matchScore": 92,
                                        "matchReasons": ["청년 연령 조건에 맞을 가능성이 높습니다."],
                                        "cautionReasons": [],
                                        "applicationEndDate": "2026-06-30",
                                        "applyUrl": "https://example.com/apply",
                                    }
                                ]
                            }
                        }
                    }
                },
            )
        )

        self.assertTrue(response.data["reference_data_used"])
        self.assertEqual(response.data["reference_sources"], ["backend.support_programs"])
        self.assertEqual(response.data["matches"][0]["title"], "청년 예비창업 패키지")
        self.assertEqual(response.data["matches"][0]["eligibility_score"], 92)

    async def test_commercial_area_agent_uses_backend_competitor_counts(self):
        agent = CommercialAreaAgent(FakeLlm())

        response = await agent.run(
            CommercialAreaRequest(
                profile=StartupProfile(region="서울", interests=["카페"]),
                query="연남동 카페 상권 봐줘",
                context={
                    "reference": {
                        "externalData": {
                            "commercialArea": {
                                "areaLabel": "서울 마포구 연남동",
                                "industryLabel": "음식점업 > 커피점/카페 > 카페",
                                "totalStores": 7,
                                "directCompetitors": 5,
                                "similarCompetitors": 1,
                                "competitionLevel": "low",
                                "notes": ["정확한 임대료/매출은 별도 데이터 필요"],
                            }
                        }
                    }
                },
            )
        )

        self.assertTrue(response.data["reference_data_used"])
        self.assertEqual(response.data["reference_sources"], ["backend.commercial_area"])
        self.assertEqual(response.data["commercial_area"]["directCompetitors"], 5)
        self.assertIn("low", response.summary)


if __name__ == "__main__":
    unittest.main()
