from __future__ import annotations

import unittest

from app.feature_reports import FEATURE_REPORT_TEAMS, build_feature_result
from app.schemas import AgentResponse, ChatRequest, StartupProfile


def _response(intent: str, data: dict) -> AgentResponse:
    return AgentResponse(
        intent=intent,
        agent=f"{intent.title()}Agent",
        summary=f"{intent} summary",
        data=data,
    )


class FeatureReportsTest(unittest.TestCase):
    def test_all_feature_reports_include_renderable_report_data(self):
        request = ChatRequest(
            message="기능 리포트를 만들어줘",
            profile=StartupProfile(region="서울", interests=["카페"], budget_krw=5_000_000),
            context={
                "featureContext": {"featureKey": "ITEM"},
                "resultContext": {
                    "currentResult": {
                        "report": {
                            "metrics": [{"day": 1, "orders": 10, "revenue": 100000}],
                            "summary": {"totalRevenue": 100000, "totalCost": 70000, "totalProfit": 30000},
                        }
                    }
                },
            },
        )
        response = _response("selective_collaboration", {})
        results = {
            "profile": _response("profile", {"score": 85}),
            "idea": _response("idea", {
                "recommendations": [{"title": "테이크아웃 커피", "match_score": 91, "reason": "입지와 예산에 맞습니다."}],
            }),
            "finance": _response("finance", {
                "initial_cash_needed_krw": 3_000_000,
                "break_even_units_per_day": 18,
                "price_per_unit_krw": 5000,
                "expected_daily_customers": 20,
            }),
            "policy": _response("policy", {
                "matches": [{"title": "청년창업 지원", "eligibility_score": 88, "region": "서울"}],
            }),
            "plan": _response("plan", {
                "target": "청년창업 지원",
                "sections": [{"title": "1. 사업 개요", "body": "테이크아웃 커피 사업입니다."}],
            }),
            "operation": _response("operation", {
                "risk_items": [{"risk": "재고 누락", "action": "일일 체크"}],
                "recommended_actions": [{"action": "재고표 작성", "reason": "품절을 줄입니다."}],
            }),
            "marketing": _response("marketing", {
                "reels_hook": "출근길 3분 커피",
                "hashtags": ["#서울카페"],
                "storyboard_15s": ["0-3초: 출근길 문제 제시"],
            }),
            "simulation": _response("simulation", {"state": "ready"}),
        }

        expected_keys = {
            "ITEM": "items",
            "SIMULATOR": "metrics",
            "SUPPORT": "list",
            "PLAN": "sections",
            "OPERATION": "suggestions",
            "SNS": "beats",
        }

        for feature_key, expected_key in expected_keys.items():
            with self.subTest(feature_key=feature_key):
                request.context["featureContext"]["featureKey"] = feature_key
                result = build_feature_result(request=request, response=response, results=results)

                self.assertIsNotNone(result)
                self.assertEqual(result["targetFeature"], feature_key)
                self.assertEqual(
                    result["payload"]["featureId"],
                    feature_key.lower(),
                )
                self.assertIn(expected_key, result["payload"]["reportData"])

    def test_fixed_agent_team_contract_includes_all_report_features(self):
        self.assertEqual(set(FEATURE_REPORT_TEAMS), {"ITEM", "SIMULATOR", "SUPPORT", "PLAN", "OPERATION", "SNS"})
        self.assertEqual(FEATURE_REPORT_TEAMS["PLAN"], ["profile", "idea", "policy", "plan"])


if __name__ == "__main__":
    unittest.main()
