from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, IdeaRequest, StartupProfile


class IdeaAgent(BaseAgent):
    name = "IdeaAgent"

    async def run(self, request: IdeaRequest) -> AgentResponse:
        profile = request.profile
        budget = profile.budget_krw or 3_000_000
        candidates = [self._score_candidate(profile, budget, candidate) for candidate in self._candidate_templates(profile)]
        candidates.sort(key=lambda item: item["match_score"], reverse=True)

        selected = candidates[: request.count]
        top = selected[0]
        missing_inputs = []
        if not profile.region:
            missing_inputs.append("지역")
        if profile.budget_krw is None:
            missing_inputs.append("초기 자금")
        if not profile.experiences:
            missing_inputs.append("경험")

        data = self.agent_data(
            position=f"{top['title']}이 현재 조건에서 가장 실행 가능성이 높습니다.",
            evidence={
                "top_idea": top,
                "ranking_basis": ["경험 적합도", "관심 분야", "초기비용", "채널 적합도", "리스크 성향", "지역 기회"],
            },
            score=int(top["match_score"]),
            risks=top["risks"],
            assumptions=[
                f"초기 예산은 {budget:,}원으로 계산했습니다.",
                "고객 검증 전에는 고정비를 최소화하는 실행안을 우선했습니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation=f"{top['title']}을 1순위로 두고 비용 시뮬레이션과 30일 체험을 실행하세요.",
            payload={
                "recommendations": selected,
                "ranking_basis": ["경험 적합도", "관심 분야", "초기비용", "채널 적합도", "리스크 성향", "지역 기회"],
                "decision_rules": [
                    "예산 초과 후보는 감점",
                    "전공/경험/관심 키워드가 겹치면 가점",
                    "낮은 리스크 성향이면 재고/임대 부담이 낮은 아이템 가점",
                    "오프라인/SNS 선호 채널과 실행 방식이 맞으면 가점",
                ],
            },
        )
        fallback = f"{len(selected)}개의 창업 아이템을 실행 가능성 기준으로 추천했습니다."
        summary = await self.polish_summary(task="startup idea recommendation", data=data, fallback=fallback)

        return AgentResponse(
            intent="idea",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "1순위 아이템의 예상 비용과 손익분기점 계산",
                "지역 지원사업 매칭으로 초기 비용 보완",
                "30일 테스트 계획을 할 일 목록으로 전환",
            ],
        )

    def _candidate_templates(self, profile: StartupProfile) -> list[dict[str, Any]]:
        region = profile.region or "거주 지역"
        return [
            {
                "title": "로컬 SNS 콘텐츠 스튜디오",
                "business_type": "content",
                "reason": "오프라인 영업 수요와 온라인 홍보 수요를 연결하기 쉽습니다.",
                "keywords": ["sns", "콘텐츠", "홍보", "브랜딩", "로컬", "디자인"],
                "channels": ["SNS", "오프라인"],
                "estimated_initial_cost_krw": 1_200_000,
                "fixed_cost_level": "low",
                "difficulty": "낮음",
                "risks": ["초기 고객 확보가 관건입니다.", "성과를 보여줄 샘플 콘텐츠가 필요합니다."],
                "first_30_days": ["상권 20곳 리스트업", "샘플 콘텐츠 3개 제작", "무료 진단 후 유료 패키지 제안"],
            },
            {
                "title": "동네 매장 브랜딩 패키지",
                "business_type": "service",
                "reason": f"{region} 소상공인을 대상으로 메뉴판, 로고가이드, SNS 템플릿을 묶어 판매합니다.",
                "keywords": ["디자인", "브랜딩", "로컬", "소상공인", "오프라인"],
                "channels": ["오프라인", "SNS"],
                "estimated_initial_cost_krw": 1_500_000,
                "fixed_cost_level": "low",
                "difficulty": "낮음",
                "risks": ["포트폴리오가 없으면 첫 수주가 늦어질 수 있습니다."],
                "first_30_days": ["포트폴리오 2종 제작", "카페/공방 방문 영업", "월 구독형 관리 상품 테스트"],
            },
            {
                "title": "소자본 굿즈 커머스",
                "business_type": "commerce",
                "reason": "선주문과 소량 제작을 활용하면 재고 부담을 낮출 수 있습니다.",
                "keywords": ["굿즈", "커머스", "디자인", "온라인", "브랜딩"],
                "channels": ["온라인", "SNS"],
                "estimated_initial_cost_krw": 2_500_000,
                "fixed_cost_level": "medium",
                "difficulty": "중간",
                "risks": ["재고가 남으면 현금 회수가 늦어질 수 있습니다.", "배송/CS 운영이 필요합니다."],
                "first_30_days": ["타깃 테마 선정", "시안 투표 진행", "선주문 페이지 오픈"],
            },
            {
                "title": "청년 창업 준비 대행/체크리스트 서비스",
                "business_type": "service",
                "reason": "지원사업 서류와 일정 관리의 반복 업무를 서비스화할 수 있습니다.",
                "keywords": ["지원사업", "체크리스트", "서류", "컨설팅", "창업"],
                "channels": ["온라인", "SNS"],
                "estimated_initial_cost_krw": 800_000,
                "fixed_cost_level": "low",
                "difficulty": "중간",
                "risks": ["정책/공고 정확도가 낮으면 신뢰가 떨어집니다."],
                "first_30_days": ["지원사업 10개 분석", "체크리스트 템플릿 제작", "예비창업자 인터뷰 5명"],
            },
            {
                "title": "푸드 팝업 테스트 키트",
                "business_type": "popup",
                "reason": "메뉴 테스트, 홍보, 재고 계산을 30일 단위로 패키징합니다.",
                "keywords": ["푸드", "카페", "음식", "팝업", "오프라인", "로컬"],
                "channels": ["오프라인", "SNS"],
                "estimated_initial_cost_krw": 2_800_000,
                "fixed_cost_level": "medium",
                "difficulty": "중간",
                "risks": ["재료비와 장소비가 빠르게 늘 수 있습니다.", "날씨와 유동인구 영향을 받습니다."],
                "first_30_days": ["메뉴 원가표 작성", "팝업 장소 후보 조사", "SNS 사전 예약 테스트"],
            },
        ]

    def _score_candidate(
        self,
        profile: StartupProfile,
        budget: int,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        profile_terms = self._profile_terms(profile)
        keyword_overlap = sorted(profile_terms & set(candidate["keywords"]))
        channel_overlap = sorted(set(profile.preferred_channels) & set(candidate["channels"]))

        experience_fit = min(100, 45 + len(keyword_overlap) * 12)
        interest_fit = min(100, 40 + len(set(profile.interests) & set(candidate["keywords"])) * 18)
        channel_fit = min(100, 55 + len(channel_overlap) * 18)
        budget_fit = self._budget_fit(budget, candidate["estimated_initial_cost_krw"])
        risk_fit = self._risk_fit(profile.risk_tolerance, candidate["fixed_cost_level"])
        local_opportunity = self._local_opportunity(profile, candidate)
        execution_fit = 88 if candidate["difficulty"] == "낮음" else 72
        policy_fit = self._policy_fit(profile, candidate)

        score_breakdown = {
            "experience_fit": experience_fit,
            "interest_fit": interest_fit,
            "budget_fit": budget_fit,
            "channel_fit": channel_fit,
            "risk_fit": risk_fit,
            "local_opportunity": local_opportunity,
            "execution_fit": execution_fit,
            "policy_fit": policy_fit,
        }
        weighted_score = int(
            experience_fit * 0.18
            + interest_fit * 0.16
            + budget_fit * 0.18
            + channel_fit * 0.12
            + risk_fit * 0.14
            + local_opportunity * 0.10
            + execution_fit * 0.08
            + policy_fit * 0.04
        )
        result = dict(candidate)
        result.update(
            {
                "match_score": max(0, min(100, weighted_score)),
                "score_breakdown": score_breakdown,
                "matched_keywords": keyword_overlap,
                "matched_channels": channel_overlap,
                "why_recommended": self._why_recommended(candidate, keyword_overlap, channel_overlap, budget_fit),
                "risk": " / ".join(candidate["risks"]),
            }
        )
        return result

    def _profile_terms(self, profile: StartupProfile) -> set[str]:
        raw = [profile.major or "", *profile.experiences, *profile.interests, *profile.preferred_channels]
        text = " ".join(raw).lower().replace(",", " ")
        terms = {term.strip() for term in text.split() if term.strip()}
        synonyms = {
            "디자인": "브랜딩",
            "카페": "푸드",
            "알바": "오프라인",
            "sns": "콘텐츠",
        }
        for term, mapped in synonyms.items():
            if term in terms:
                terms.add(mapped)
        return terms

    def _budget_fit(self, budget: int, estimated_cost: int) -> int:
        if estimated_cost <= budget:
            return 95
        over_ratio = estimated_cost / max(budget, 1)
        if over_ratio <= 1.25:
            return 70
        if over_ratio <= 1.6:
            return 45
        return 20

    def _risk_fit(self, risk_tolerance: str, fixed_cost_level: str) -> int:
        table = {
            "low": {"low": 95, "medium": 65, "high": 30},
            "medium": {"low": 85, "medium": 80, "high": 55},
            "high": {"low": 75, "medium": 85, "high": 85},
        }
        return table.get(risk_tolerance, table["medium"]).get(fixed_cost_level, 60)

    def _local_opportunity(self, profile: StartupProfile, candidate: dict[str, Any]) -> int:
        score = 65
        if profile.region:
            score += 12
        if "로컬" in candidate["keywords"]:
            score += 10
        if "오프라인" in candidate["channels"] and "오프라인" in profile.preferred_channels:
            score += 8
        return min(100, score)

    def _policy_fit(self, profile: StartupProfile, candidate: dict[str, Any]) -> int:
        score = 55
        if profile.startup_stage == "예비창업":
            score += 10
        if any(keyword in candidate["keywords"] for keyword in ["로컬", "콘텐츠", "브랜딩", "창업"]):
            score += 15
        return min(100, score)

    def _why_recommended(
        self,
        candidate: dict[str, Any],
        keyword_overlap: list[str],
        channel_overlap: list[str],
        budget_fit: int,
    ) -> list[str]:
        reasons = [candidate["reason"]]
        if keyword_overlap:
            reasons.append("프로필 키워드 일치: " + ", ".join(keyword_overlap))
        if channel_overlap:
            reasons.append("선호 채널 일치: " + ", ".join(channel_overlap))
        if budget_fit >= 90:
            reasons.append("현재 예산 안에서 30일 테스트가 가능합니다.")
        return reasons
