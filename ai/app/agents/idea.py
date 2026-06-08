from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, IdeaRequest


class IdeaAgent(BaseAgent):
    name = "IdeaAgent"

    async def run(self, request: IdeaRequest) -> AgentResponse:
        profile = request.profile
        budget = profile.budget_krw or 3_000_000
        region = profile.region or "거주 지역"
        interests = " ".join(profile.interests + profile.experiences + [profile.major or ""])

        candidates = [
            self._candidate(
                title="로컬 SNS 콘텐츠 스튜디오",
                reason="오프라인 영업 수요와 온라인 홍보 수요를 연결하기 쉽습니다.",
                budget=budget,
                score=86,
                difficulty="낮음",
                first_30_days=["상권 20곳 리스트업", "샘플 콘텐츠 3개 제작", "무료 진단 후 유료 패키지 제안"],
            ),
            self._candidate(
                title="동네 매장 브랜딩 패키지",
                reason=f"{region} 소상공인을 대상으로 메뉴판, 로고가이드, SNS 템플릿을 묶어 판매합니다.",
                budget=budget,
                score=82,
                difficulty="낮음",
                first_30_days=["포트폴리오 2종 제작", "카페/공방 방문 영업", "월 구독형 관리 상품 테스트"],
            ),
            self._candidate(
                title="소자본 굿즈 커머스",
                reason="선주문과 소량 제작을 활용하면 재고 부담을 낮출 수 있습니다.",
                budget=budget,
                score=76,
                difficulty="중간",
                first_30_days=["타깃 테마 선정", "시안 투표 진행", "선주문 페이지 오픈"],
            ),
            self._candidate(
                title="청년 창업 준비 대행/체크리스트 서비스",
                reason="지원사업 서류와 일정 관리의 반복 업무를 서비스화할 수 있습니다.",
                budget=budget,
                score=74,
                difficulty="중간",
                first_30_days=["지원사업 10개 분석", "체크리스트 템플릿 제작", "예비창업자 인터뷰 5명"],
            ),
            self._candidate(
                title="푸드 팝업 테스트 키트",
                reason="메뉴 테스트, 홍보, 재고 계산을 30일 단위로 패키징합니다.",
                budget=budget,
                score=72,
                difficulty="중간",
                first_30_days=["메뉴 원가표 작성", "팝업 장소 후보 조사", "SNS 사전 예약 테스트"],
            ),
        ]

        if any(keyword in interests for keyword in ["푸드", "카페", "음식", "외식"]):
            candidates.insert(0, candidates.pop(-1))
        if any(keyword in interests.lower() for keyword in ["design", "디자인", "브랜딩"]):
            candidates.insert(0, candidates.pop(1))

        selected = candidates[: request.count]
        data = {
            "recommendations": selected,
            "ranking_basis": ["경험 적합도", "초기비용", "30일 실행 가능성", "지역 기회"],
        }
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

    def _candidate(
        self,
        *,
        title: str,
        reason: str,
        budget: int,
        score: int,
        difficulty: str,
        first_30_days: list[str],
    ) -> dict[str, object]:
        estimated_cost = min(max(int(budget * 0.75), 500_000), budget)
        return {
            "title": title,
            "match_score": score,
            "difficulty": difficulty,
            "estimated_initial_cost_krw": estimated_cost,
            "reason": reason,
            "risk": "고객 검증 전 고정비 지출을 피해야 합니다.",
            "first_30_days": first_30_days,
        }
