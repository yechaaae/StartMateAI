from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas import StartupProfile
from app.schemas import AgentResponse, ProfileRequest


class ProfileAgent(BaseAgent):
    name = "ProfileAgent"

    async def run(self, request: ProfileRequest) -> AgentResponse:
        profile = request.profile
        analysis = self._analyze_profile(profile)
        missing_inputs = self._missing_inputs(request)
        score = self._profile_score(profile, missing_inputs, analysis["constraints"])
        data = self.agent_data(
            position=(
                f"사용자는 '{analysis['user_type']}'에 가깝고, "
                "고정비가 낮은 검증형 아이템부터 보는 것이 적합합니다."
            ),
            evidence=analysis["strengths"] + analysis["constraints"],
            score=score,
            risks=analysis["constraints"],
            assumptions=["입력되지 않은 항목은 예비창업자 기본값으로 해석했습니다."],
            missing_inputs=missing_inputs,
            recommendation=analysis["recommended_first_step"],
            payload={
                **analysis,
                "startup_stage": profile.startup_stage,
                "profile_summary": {
                    "region": profile.region,
                    "budget_krw": profile.budget_krw,
                    "risk_tolerance": profile.risk_tolerance,
                    "startup_stage": profile.startup_stage,
                    "tags": analysis["tags"],
                    "capability_tags": analysis["capability_tags"],
                    "user_type": analysis["user_type"],
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
                *analysis["next_questions"][:2],
                "초기 자금 기준으로 아이템 추천 실행",
                "거주 지역 기준 지원사업 매칭 실행",
            ],
        )

    def _analyze_profile(self, profile: StartupProfile) -> dict[str, object]:
        strengths: list[str] = []
        constraints: list[str] = []
        tags = self._ordered_unique(profile.interests + profile.preferred_channels)
        capability_tags = self._capability_tags(profile)
        budget_band = self._budget_band(profile.budget_krw)

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
        if "offline" not in capability_tags and "online_content" not in capability_tags:
            constraints.append("검증 가능한 고객 접점 정보가 부족함")

        user_type = self._user_type(capability_tags, budget_band, profile.risk_tolerance)
        next_questions = self._next_questions(profile)
        return {
            "user_type": user_type,
            "budget_band": budget_band,
            "strengths": strengths or ["입력 정보가 부족해 기본 예비창업자 프로필로 분석"],
            "constraints": constraints,
            "tags": tags,
            "capability_tags": capability_tags,
            "next_questions": next_questions,
            "recommended_first_step": "아이템 추천과 지원사업 매칭을 먼저 실행하세요.",
            "agent_hints": {
                "idea": "소자본/저위험/30일 검증 가능 아이템 우선",
                "policy": "지역, 예비창업, 청년/로컬/콘텐츠 키워드 우선",
                "finance": "고정비와 재고비가 낮은 가정부터 계산",
            },
        }

    def _capability_tags(self, profile: StartupProfile) -> list[str]:
        text = " ".join(
            [profile.major or "", *profile.experiences, *profile.interests, *profile.preferred_channels]
        ).lower()
        tags: list[str] = []
        rules = [
            ("design", ["디자인", "브랜딩", "로고", "굿즈"]),
            ("fnb", ["카페", "푸드", "음식", "외식", "쿠키", "팝업"]),
            ("online_content", ["sns", "콘텐츠", "릴스", "영상", "마케팅", "홍보"]),
            ("offline", ["오프라인", "알바", "매장", "상권", "팝업"]),
            ("local", ["로컬", "지역", "부산", "구미"]),
            ("commerce", ["커머스", "굿즈", "판매", "온라인"]),
        ]
        for tag, keywords in rules:
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        return tags

    def _budget_band(self, budget_krw: int | None) -> str:
        if budget_krw is None:
            return "unknown"
        if budget_krw <= 3_000_000:
            return "micro"
        if budget_krw <= 10_000_000:
            return "small"
        return "growth"

    def _user_type(self, capability_tags: list[str], budget_band: str, risk_tolerance: str) -> str:
        if "online_content" in capability_tags and "design" in capability_tags:
            base = "콘텐츠 실행형"
        elif "fnb" in capability_tags and "offline" in capability_tags:
            base = "오프라인 경험형"
        elif "commerce" in capability_tags:
            base = "커머스 테스트형"
        else:
            base = "소자본 탐색형"

        if budget_band == "micro" or risk_tolerance == "low":
            return f"소자본 안정 {base}"
        if budget_band == "growth":
            return f"확장 지향 {base}"
        return base

    def _profile_score(self, profile: StartupProfile, missing_inputs: list[str], constraints: list[str]) -> int:
        filled_fields = 6 - len(missing_inputs)
        score = 45 + filled_fields * 9
        if profile.region:
            score += 7
        if profile.budget_krw is not None:
            score += 6
        score -= max(0, len(constraints) - 1) * 5
        return max(0, min(100, score))

    def _next_questions(self, profile: StartupProfile) -> list[str]:
        questions = []
        if not profile.budget_krw:
            questions.append("초기 자금은 어느 정도까지 사용할 수 있나요?")
        if not profile.region:
            questions.append("어느 지역에서 먼저 테스트하고 싶나요?")
        if not profile.experiences:
            questions.append("아르바이트, 프로젝트, 동아리 등 바로 활용 가능한 경험이 있나요?")
        if not profile.preferred_channels:
            questions.append("오프라인, SNS, 온라인 판매 중 어떤 채널을 선호하나요?")
        questions.append("주당 몇 시간을 창업 준비에 쓸 수 있나요?")
        return questions

    def _ordered_unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            item = value.strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

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
