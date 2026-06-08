from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, ProfileRequest


class ProfileAgent(BaseAgent):
    name = "ProfileAgent"

    async def run(self, request: ProfileRequest) -> AgentResponse:
        profile = request.profile
        strengths: list[str] = []
        constraints: list[str] = []

        if profile.major:
            strengths.append(f"{profile.major} 전공 기반 역량")
        if profile.experiences:
            strengths.append("경험: " + ", ".join(profile.experiences[:3]))
        if profile.region:
            strengths.append(f"{profile.region} 지역 기반 실행 가능성")
        if profile.budget_krw is not None:
            if profile.budget_krw <= 3_000_000:
                constraints.append("초기 자금이 낮아 재고/임대 부담이 작은 모델 우선")
            else:
                strengths.append(f"초기 자금 {profile.budget_krw:,}원 활용 가능")
        if profile.risk_tolerance == "low":
            constraints.append("낮은 리스크 선호: 테스트형/위탁형 모델 우선")

        tags = sorted(
            set(
                [item.strip() for item in profile.interests + profile.preferred_channels if item.strip()]
            )
        )
        missing_inputs = self._missing_inputs(request)
        usable_strengths = strengths or ["입력 정보가 부족해 기본 예비창업자 프로필로 분석"]
        score = 100 - len(missing_inputs) * 12
        data = self.agent_data(
            position="사용자 조건과 제약을 먼저 고정해야 추천 품질이 올라갑니다.",
            evidence=usable_strengths + constraints,
            score=score,
            risks=constraints,
            assumptions=["입력되지 않은 항목은 예비창업자 기본값으로 해석했습니다."],
            missing_inputs=missing_inputs,
            recommendation="아이템 추천과 지원사업 매칭을 먼저 실행하세요.",
            payload={
                "strengths": usable_strengths,
                "constraints": constraints,
                "tags": tags,
                "startup_stage": profile.startup_stage,
                "recommended_first_step": "아이템 추천과 지원사업 매칭을 먼저 실행",
                "profile_summary": {
                    "region": profile.region,
                    "budget_krw": profile.budget_krw,
                    "risk_tolerance": profile.risk_tolerance,
                    "startup_stage": profile.startup_stage,
                    "tags": tags,
                },
            },
        )
        fallback = "프로필을 분석해 강점, 제약조건, 우선 실행 기능을 정리했습니다."
        summary = await self.polish_summary(task="profile analysis", data=data, fallback=fallback)

        return AgentResponse(
            intent="profile",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "관심 분야와 가능한 근무 시간을 추가 입력",
                "초기 자금 기준으로 아이템 추천 실행",
                "거주 지역 기준 지원사업 매칭 실행",
            ],
        )

    def _missing_inputs(self, request: ProfileRequest) -> list[str]:
        profile = request.profile
        missing = []
        if not profile.major:
            missing.append("전공/핵심 역량")
        if not profile.experiences:
            missing.append("관련 경험")
        if not profile.region:
            missing.append("창업 희망 지역")
        if profile.budget_krw is None:
            missing.append("초기 자금")
        if not profile.interests:
            missing.append("관심 분야")
        if not profile.preferred_channels:
            missing.append("선호 판매/홍보 채널")
        return missing
