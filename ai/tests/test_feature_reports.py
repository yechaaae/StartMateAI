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
            "commercial_area": _response("commercial_area", {
                "payload": {"competition_level": "low", "direct_competitors": 4},
            }),
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
        self.assertEqual(FEATURE_REPORT_TEAMS["ITEM"], ["profile", "idea", "finance", "policy", "commercial_area"])
        self.assertEqual(FEATURE_REPORT_TEAMS["SUPPORT"], ["profile", "idea", "policy", "finance"])
        self.assertEqual(FEATURE_REPORT_TEAMS["PLAN"], ["profile", "idea", "policy", "plan", "finance", "commercial_area"])

    def test_reviewed_report_features_include_agent_review_payload(self):
        request = ChatRequest(
            message="기능 리포트를 만들어줘",
            profile=StartupProfile(region="서울", interests=["카페"], budget_krw=5_000_000),
            context={"featureContext": {"featureKey": "ITEM"}},
        )
        response = _response("selective_collaboration", {})
        results = {
            "profile": _response("profile", {"score": 85}),
            "idea": _response("idea", {
                "recommendations": [{"title": "테이크아웃 커피", "match_score": 91, "reason": "입지와 예산에 맞습니다."}],
            }),
            "finance": _response("finance", {"initial_cash_needed_krw": 3_000_000}),
            "policy": _response("policy", {
                "matches": [{"title": "청년창업 지원", "eligibility_score": 88, "region": "서울"}],
            }),
            "plan": _response("plan", {
                "target": "청년창업 지원",
                "sections": [{"title": "1. 사업 개요", "body": "테이크아웃 커피 사업입니다."}],
            }),
            "commercial_area": _response("commercial_area", {
                "payload": {"competition_level": "low", "direct_competitors": 4},
            }),
        }
        agent_review = {
            "summary": "상권, 재무, 정책 조건을 재검토해 추천 우선순위를 조정했습니다.",
            "checks": ["지역 적합성", "예산 현실성", "지원조건 부합성"],
            "revisions": ["경쟁도 리스크 반영", "초기비용 기준으로 후보 재정렬"],
            "rounds": [{"round": 1, "type": "draft"}],
            "challenges": [{"issue": "상권 확인 필요"}],
            "revisionMessages": [{"message": "수정"}],
            "consensus": {"decision": "conditional_consensus"},
        }

        for feature_key in ("ITEM", "SUPPORT", "PLAN"):
            with self.subTest(feature_key=feature_key):
                request.context["featureContext"]["featureKey"] = feature_key
                result = build_feature_result(
                    request=request,
                    response=response,
                    results=results,
                    agent_review=agent_review,
                )

                report_data = result["payload"]["reportData"]
                self.assertEqual(report_data["agentReview"]["summary"], agent_review["summary"])
                self.assertIn("agentDiscussion", result["payload"])

    def test_item_report_reranks_candidates_with_commercial_and_support_evidence(self):
        request = ChatRequest(
            message="아이템 추천 리포트를 만들어줘",
            profile=StartupProfile(region="서울 마포구 연남동", interests=["카페"], budget_krw=5_000_000),
            context={"featureContext": {"featureKey": "ITEM"}},
        )
        response = _response("selective_collaboration", {})
        results = {
            "idea": _response("idea", {
                "score": 91,
                "recommendations": [
                    {
                        "title": "연남동 테이크아웃 커피 매장",
                        "business_type": "cafe",
                        "match_score": 92,
                        "reason": "카페 관심사와 지역성이 맞습니다.",
                        "keywords": ["카페", "오프라인"],
                        "channels": ["오프라인"],
                    },
                    {
                        "title": "연남동 소상공인 SNS 숏폼 대행",
                        "business_type": "content",
                        "match_score": 85,
                        "reason": "고정비가 낮고 지역 매장을 고객으로 검증할 수 있습니다.",
                        "keywords": ["SNS", "콘텐츠", "소상공인"],
                        "channels": ["SNS"],
                    },
                ],
            }),
            "finance": _response("finance", {
                "initial_cash_needed_krw": 3_000_000,
                "break_even_units_per_day": 18,
            }),
            "policy": _response("policy", {
                "matches": [
                    {
                        "title": "소상공인 온라인 판로 지원",
                        "eligibility_score": 88,
                        "summary": "SNS 콘텐츠와 온라인 마케팅을 지원합니다.",
                        "support_type": "marketing",
                    }
                ],
            }),
            "commercial_area": _response("commercial_area", {
                "reference_data_used": True,
                "payload": {
                    "area": "서울 마포구 연남동",
                    "industry": "음식점업 > 커피점/카페 > 카페",
                    "competition_level": "high",
                    "total_stores": 2327,
                    "direct_competitors": 204,
                    "similar_competitors": 704,
                },
            }),
        }

        result = build_feature_result(request=request, response=response, results=results)
        report_data = result["payload"]["reportData"]
        items = report_data["items"]

        self.assertEqual(items[0]["title"], "연남동 소상공인 SNS 숏폼 대행")
        self.assertGreater(items[0]["score"], items[1]["score"])
        self.assertLess(items[1]["scoreBreakdown"]["commercial_area_adjustment"], 0)
        self.assertGreater(items[0]["scoreBreakdown"]["support_program_adjustment"], 0)
        self.assertIn("상권 데이터", report_data["dataSources"])
        self.assertIn("지원사업 추천", report_data["dataSources"])
        self.assertTrue(items[0]["supportPrograms"])

    def test_item_report_does_not_create_synthetic_candidate_without_idea_evidence(self):
        request = ChatRequest(
            message="아이템 추천 리포트를 만들어줘",
            profile=StartupProfile(region="서울", interests=["카페"], budget_krw=5_000_000),
            context={"featureContext": {"featureKey": "ITEM"}},
        )
        response = _response("selective_collaboration", {})
        results = {
            "idea": _response("idea", {"recommendations": []}),
            "finance": _response("finance", {}),
            "policy": _response("policy", {"matches": []}),
            "commercial_area": _response("commercial_area", {
                "payload": {"reference_data_used": False, "commercial_area": None},
            }),
        }

        result = build_feature_result(request=request, response=response, results=results)
        report_data = result["payload"]["reportData"]

        self.assertEqual(report_data["items"], [])
        self.assertIn("상권 데이터", report_data["missingEvidence"])
        self.assertIn("지원사업 추천", report_data["missingEvidence"])


if __name__ == "__main__":
    unittest.main()
