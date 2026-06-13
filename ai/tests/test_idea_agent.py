from __future__ import annotations

import json
import unittest

from app.agents.idea import IdeaAgent
from app.schemas import IdeaRequest, StartupProfile


class FakeLLM:
    def __init__(self, *, enabled: bool, response: str = "{}"):
        self.is_enabled = enabled
        self.response = response
        self.settings = None
        self.calls = 0

    async def complete(self, **kwargs):
        self.calls += 1
        return self.response


class IdeaAgentTest(unittest.IsolatedAsyncioTestCase):
    async def test_does_not_emit_rule_fallback_candidates_when_llm_is_disabled(self):
        agent = IdeaAgent(FakeLLM(enabled=False))
        response = await agent.run(IdeaRequest(
            profile=StartupProfile(
                region="포항",
                interests=["카페"],
                budget_krw=5_000_000,
            ),
            count=3,
        ))

        self.assertEqual(response.data["recommendations"], [])
        self.assertEqual(response.data["all_candidates"], [])
        self.assertEqual(response.data["generation"]["generated_by"], "none")
        self.assertIn("idea_llm_disabled_no_recommendations", response.warnings)

    async def test_uses_only_llm_candidates_without_mixing_guardrail_templates(self):
        llm_payload = {
            "ideas": [
                {
                    "title": "포항 해변 러닝 크루 굿즈 예약판매",
                    "business_type": "commerce",
                    "target_customer": "포항 러닝 모임",
                    "reason": "지역 커뮤니티를 대상으로 예약 수량을 먼저 확인할 수 있습니다.",
                    "why_fit": ["콘텐츠 제작 경험을 상세페이지와 SNS 홍보에 활용할 수 있습니다."],
                    "keywords": ["러닝", "굿즈", "예약판매"],
                    "channels": ["SNS"],
                    "estimated_initial_cost_krw": 900000,
                    "fixed_cost_level": "low",
                    "difficulty": "낮음",
                    "first_30_days": ["크루 5곳 인터뷰", "시안 3개 제작", "예약 페이지 공개"],
                    "validation_method": "예약 수량과 문의 전환율을 봅니다.",
                    "risks": ["초기 디자인 선호가 분산될 수 있습니다."],
                }
            ]
        }
        agent = IdeaAgent(FakeLLM(enabled=True, response=json.dumps(llm_payload, ensure_ascii=False)))

        response = await agent.run(IdeaRequest(
            profile=StartupProfile(
                region="포항",
                major="디자인",
                interests=["커뮤니티", "콘텐츠"],
                budget_krw=5_000_000,
            ),
            count=3,
        ))

        titles = [item["title"] for item in response.data["all_candidates"]]
        self.assertEqual(titles, ["포항 해변 러닝 크루 굿즈 예약판매"])
        self.assertEqual(response.data["recommendations"][0]["generated_by"], "llm")
        self.assertNotIn("포항 한식 소량 예약 판매", titles)
        self.assertNotIn("포항 공유주방 팝업 메뉴 테스트", titles)


if __name__ == "__main__":
    unittest.main()
