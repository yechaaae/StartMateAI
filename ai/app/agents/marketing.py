from __future__ import annotations

import re
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, MarketingRequest


class MarketingAgent(BaseAgent):
    name = "MarketingAgent"

    async def run(self, request: MarketingRequest) -> AgentResponse:
        plan = self._build_plan(request)
        missing_inputs = self._missing_inputs(request)
        risks = []
        if missing_inputs:
            risks.append("타깃, 장소, 일정이 불명확하면 문구가 일반적인 홍보 문안에 가까워질 수 있습니다.")

        data = self.agent_data(
            position="초기 마케팅은 큰 캠페인보다 릴스/게시글 1개씩 빠르게 테스트하고 문의수로 검증하는 방식이 적합합니다.",
            evidence={
                "content_title": plan["topic"],
                "target_customer": plan["target_customer"],
                "channel": plan["channel"],
                "objective": plan["objective"],
                "hook": plan["hook"],
                "schedule": plan["schedule"],
            },
            score=82 if missing_inputs else 92,
            risks=risks,
            assumptions=[
                f"브랜드 톤은 '{plan['tone']}'로 적용했습니다.",
                "성과 판단은 조회수보다 저장수, 문의수, 예약/방문 전환을 우선합니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation="훅 2개를 A/B로 올리고 24시간 뒤 저장수, 프로필 클릭, 문의수를 비교하세요.",
            payload=plan,
        )

        return AgentResponse(
            intent="marketing",
            agent=self.name,
            summary=self._summary(plan, missing_inputs),
            data=data,
            next_actions=[
                "릴스 1개와 게시글 1개를 같은 주제로 업로드",
                "Hook A/B 테스트 후 저장수, 문의수, 예약 전환 기록",
                "반응이 좋은 메뉴, 혜택, 고객 불편을 다음 콘텐츠 주제로 재사용",
            ],
        )

    def _build_plan(self, request: MarketingRequest) -> dict[str, Any]:
        product = self._clean(request.product_name) or "창업 상품"
        target = self._target_customer(request)
        place = self._clean(request.place) or self._default_place(request)
        date = self._clean(request.event_date) or "이번 주"
        channel = self._channel(request)
        objective = self._objective(request)
        tone = self._clean(request.brand_tone) or "친근하고 실행력 있는"
        cta = self._call_to_action(objective, place)
        hook = self._hook(product, target, date, objective)
        beats = self._storyboard(product, place, target, cta)
        caption = self._caption(product, place, date, target, tone, cta)
        tags = self._hashtags(request, product)
        schedule = self._schedule(request, channel)

        return {
            "topic": f"{product} 홍보 콘텐츠",
            "content_title": f"{product} {channel} 콘텐츠 초안",
            "hook": hook,
            "beats": beats,
            "storyboard_15s": beats,
            "caption": caption,
            "body": caption,
            "tags": tags,
            "hashtags": tags,
            "target_customer": target,
            "targetCustomer": target,
            "channel": channel,
            "objective": objective,
            "tone": tone,
            "callToAction": cta,
            "schedule": schedule,
            "upload_schedule": [
                {"when": "D-3", "content": "티저 릴스와 스토리 투표"},
                {"when": "D-1", "content": "상품 상세 게시글과 방문/예약 안내"},
                {"when": "D-day 오전", "content": "장소, 시간, 수량 한정 CTA"},
                {"when": "D-day 종료 후", "content": "현장 반응, 후기, 다음 오픈 예고"},
            ],
            "customer_strategy": self._customer_strategy(target, product),
            "conversion_improvements": self._conversion_improvements(objective),
            "promotion_ideas": self._promotion_ideas(product),
            "metrics_to_track": ["저장수", "프로필 클릭", "DM/문의수", "예약/방문 전환", "콘텐츠별 매출"],
            "ab_test": [
                {"variant": "A", "focus": "한정성", "copy": f"{date}에만 만나는 {product}, 놓치기 전에 확인하세요."},
                {"variant": "B", "focus": "문제 해결", "copy": f"{target}를 위해 준비한 {product}, 오늘 바로 경험해보세요."},
            ],
        }

    def _summary(self, plan: dict[str, Any], missing_inputs: list[str]) -> str:
        missing = f"\n\n보완 필요: {', '.join(missing_inputs)}" if missing_inputs else ""
        beats = "\n".join(f"{idx + 1}. {beat}" for idx, beat in enumerate(plan["beats"]))
        tags = " ".join(plan["tags"])
        metrics = ", ".join(plan["metrics_to_track"])
        return (
            f"SNS 홍보 초안: {plan['topic']}\n\n"
            f"타깃: {plan['target_customer']}\n"
            f"채널/목적: {plan['channel']} / {plan['objective']}\n\n"
            f"Hook:\n{plan['hook']}\n\n"
            f"15초 영상 구성안:\n{beats}\n\n"
            f"본문 문구:\n{plan['caption']}\n\n"
            f"추천 해시태그:\n{tags}\n\n"
            f"게시 예약 정보:\n{plan['schedule']}\n\n"
            f"확인할 지표: {metrics}"
            f"{missing}"
        )

    def _target_customer(self, request: MarketingRequest) -> str:
        if request.target_customer:
            return self._clean(request.target_customer)
        interests = " ".join(request.profile.interests or [])
        product = request.product_name
        if any(keyword in f"{interests} {product}" for keyword in ["쿠키", "디저트", "카페", "음료", "요식"]):
            region = request.profile.region or "로컬"
            return f"{region} 직장인, 대학생, 디저트 관심 고객"
        if any(keyword in f"{interests} {product}" for keyword in ["소상공인", "매장", "운영", "서비스"]):
            region = request.profile.region or "로컬"
            return f"{region} 소상공인과 매장 운영자"
        return "초기 구매 가능성이 높은 로컬 고객"

    def _default_place(self, request: MarketingRequest) -> str:
        region = request.profile.region or "로컬"
        if "온라인" in request.goal:
            return f"{region} 온라인 판매 채널"
        if "팝업" in request.goal or "오프라인" in request.goal:
            return f"{region} 팝업 현장"
        return f"{region} 판매 채널"

    def _channel(self, request: MarketingRequest) -> str:
        raw = self._clean(request.channel)
        goal = request.goal.lower()
        if raw:
            return raw
        if any(keyword in goal for keyword in ["릴스", "reels", "인스타", "instagram"]):
            return "Instagram Reels"
        if any(keyword in goal for keyword in ["쇼츠", "shorts", "유튜브"]):
            return "YouTube Shorts"
        if any(keyword in goal for keyword in ["블로그", "검색"]):
            return "Blog/Search"
        if any(keyword in goal for keyword in ["전단", "오프라인"]):
            return "Offline Flyer"
        return "Instagram Reels"

    def _objective(self, request: MarketingRequest) -> str:
        raw = self._clean(request.objective)
        goal = request.goal
        if raw:
            return raw
        if any(keyword in goal for keyword in ["예약", "구매", "판매", "문의", "전환"]):
            return "예약/문의 전환"
        if any(keyword in goal for keyword in ["방문", "팝업", "행사"]):
            return "방문 유도"
        if any(keyword in goal for keyword in ["인지", "브랜딩", "홍보"]):
            return "인지도 확보"
        return "방문과 문의 확보"

    def _call_to_action(self, objective: str, place: str) -> str:
        if "예약" in objective or "문의" in objective:
            return "DM으로 예약 가능 여부를 먼저 확인하세요."
        if "방문" in objective:
            return f"{place}에서 오늘 운영 시간을 확인하고 방문하세요."
        return "저장해두고 다음 오픈 소식을 확인하세요."

    def _hook(self, product: str, target: str, date: str, objective: str) -> str:
        if "방문" in objective:
            return f"{target}이라면 {date} 놓치기 아까운 {product}, 현장에서 바로 확인하세요."
        if "예약" in objective or "문의" in objective:
            return f"{product}가 궁금했다면 {date} 예약 전에 이 3가지만 확인하세요."
        return f"{target}를 위한 {product}, 첫 반응을 확인할 시간입니다."

    def _storyboard(self, product: str, place: str, target: str, cta: str) -> list[str]:
        return [
            f"0-3초: {target}의 고민을 한 문장으로 보여주고 {product} 클로즈업",
            f"4-8초: 만드는 과정, 사용 장면, 차별 포인트 2가지를 빠르게 제시",
            f"9-12초: 가격, 수량, 장소처럼 구매 판단에 필요한 정보 노출",
            f"13-15초: {place} 안내와 '{cta}' 문구로 마무리",
        ]

    def _caption(self, product: str, place: str, date: str, target: str, tone: str, cta: str) -> str:
        return (
            f"{date}, {place}에서 {product} 콘텐츠를 준비했습니다.\n"
            f"{target}이 부담 없이 반응을 확인할 수 있도록 핵심 정보만 {tone} 톤으로 전합니다.\n"
            f"수량, 운영 시간, 위치를 확인한 뒤 {cta}"
        )

    def _hashtags(self, request: MarketingRequest, product: str) -> list[str]:
        region = request.profile.region or "로컬"
        compact_product = re.sub(r"\s+", "", product)
        base = [
            f"#{compact_product}",
            f"#{region}창업",
            f"#{region}맛집" if any(keyword in product for keyword in ["쿠키", "카페", "디저트", "음료"]) else f"#{region}소상공인",
            "#팝업스토어",
            "#청년창업",
            "#로컬브랜드",
        ]
        return list(dict.fromkeys(base))

    def _customer_strategy(self, target: str, product: str) -> list[str]:
        return [
            f"{target}가 바로 이해할 수 있게 첫 문장에 '{product}'의 용도와 혜택을 명시",
            "가격, 장소, 운영 시간, 남은 수량처럼 행동에 필요한 정보를 본문 상단에 배치",
            "댓글보다 DM/예약 링크로 행동을 모아 전환 추적을 단순화",
        ]

    def _conversion_improvements(self, objective: str) -> list[str]:
        improvements = [
            "프로필 상단에 예약/문의 링크를 고정",
            "스토리 하이라이트에 가격, 위치, 후기, FAQ를 분리",
        ]
        if "방문" in objective:
            improvements.append("지도 링크와 운영 시간을 게시물 첫 줄에 배치")
        if "예약" in objective or "문의" in objective:
            improvements.append("DM 자동응답 첫 문장에 가격, 가능 시간, 결제 방법을 안내")
        return improvements

    def _promotion_ideas(self, product: str) -> list[str]:
        return [
            f"{product} 첫 구매 인증 시 다음 구매 혜택 제공",
            "인기 상품과 재고 여유 상품을 세트로 묶어 객단가 테스트",
            "현장 후기 스토리 리그램으로 다음 운영일 재방문 유도",
        ]

    def _schedule(self, request: MarketingRequest, channel: str) -> str:
        if request.schedule:
            return self._clean(request.schedule)
        date = request.event_date or "운영일"
        if "Reels" in channel or "Shorts" in channel:
            return f"{date} 기준 D-3 티저, D-1 상세 안내, D-day 오전 위치/수량 공지"
        return f"{date} 기준 D-2 상세 게시, D-day 오전 리마인드, 종료 후 후기 업로드"

    def _missing_inputs(self, request: MarketingRequest) -> list[str]:
        missing = []
        if not request.target_customer:
            missing.append("타깃 고객층")
        if not request.event_date:
            missing.append("게시/행사 일정")
        if not request.place:
            missing.append("판매 장소 또는 채널")
        return missing

    def _clean(self, value: Any) -> str:
        return str(value).strip() if value is not None else ""
