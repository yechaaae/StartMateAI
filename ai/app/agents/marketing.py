from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, MarketingRequest


class MarketingAgent(BaseAgent):
    name = "MarketingAgent"

    async def run(self, request: MarketingRequest) -> AgentResponse:
        target = request.target_customer or "동네 고객"
        place = request.place or "매장/팝업 현장"
        date = request.event_date or "이번 주"
        data = {
            "reels_hook": f"{target}이 놓치면 아쉬운 {request.product_name}, {date}에 만나요.",
            "storyboard_15s": [
                "0-3초: 제품 클로즈업과 문제 상황 제시",
                "4-8초: 만드는 과정 또는 차별점 노출",
                "9-12초: 행사 혜택과 장소 안내",
                "13-15초: 방문/예약 CTA",
            ],
            "caption": (
                f"{place}에서 {request.product_name} 이벤트를 진행합니다. "
                f"{request.brand_tone} 톤으로 오늘 바로 방문하고 싶게 만드는 혜택을 준비했어요."
            ),
            "hashtags": self._hashtags(request),
            "upload_schedule": [
                {"when": "D-3", "content": "티저 릴스와 스토리 투표"},
                {"when": "D-1", "content": "제품/혜택 상세 게시글"},
                {"when": "D-day 오전", "content": "장소 안내와 방문 CTA"},
                {"when": "D-day 저녁", "content": "현장 반응 리캡"},
            ],
        }
        fallback = "SNS 홍보용 릴스 훅, 15초 콘티, 게시글 문구, 업로드 일정을 생성했습니다."
        summary = await self.polish_summary(task="sns content generation", data=data, fallback=fallback)

        return AgentResponse(
            intent="marketing",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "실제 이미지나 영상 소재 3개 선택",
                "게시 전 타깃 고객에게 문구 반응 확인",
                "업로드 후 조회수, 저장수, 문의수 기록",
            ],
        )

    def _hashtags(self, request: MarketingRequest) -> list[str]:
        region = request.profile.region or "로컬"
        compact_product = request.product_name.replace(" ", "")
        return [
            f"#{compact_product}",
            f"#{region}창업",
            "#청년창업",
            "#팝업이벤트",
            "#로컬브랜드",
        ]
