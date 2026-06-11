from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, PlanRequest


class PlanAgent(BaseAgent):
    name = "PlanAgent"

    async def run(self, request: PlanRequest) -> AgentResponse:
        idea_name = request.idea_name or self._idea_from_context(request.context) or "선택한 창업 아이템"
        support_title = (
            request.support_program.get("title")
            or request.target
            or "창업 지원사업"
        )
        focused_title = request.focused_section.get("title") or "전체 초안"

        sections = [
            {
                "title": "1. 사업 개요",
                "body": f"{idea_name}을 중심으로 초기 고객 반응을 빠르게 검증하고, {support_title}의 목적에 맞춰 실행 가능한 창업 모델로 정리합니다.",
            },
            {
                "title": "2. 문제 정의",
                "body": "초기 창업자는 고객 검증, 비용 구조, 홍보 채널을 동시에 확인해야 하지만 이를 한 번에 정리할 기준이 부족합니다.",
            },
            {
                "title": "3. 해결 방안",
                "body": "소규모 파일럿 운영, 온라인 홍보 테스트, 지원사업 자금 활용 계획을 묶어 30일 안에 검증 가능한 실행 단위로 설계합니다.",
            },
            {
                "title": "4. 고객 및 시장",
                "body": "프로필의 지역, 관심 분야, 강점을 바탕으로 접근 가능한 초기 고객군을 우선 정의하고 반복 구매 가능성을 확인합니다.",
            },
            {
                "title": "5. 수익 모델",
                "body": "초기에는 고정비를 낮춘 단일 상품 또는 패키지로 시작하고, 검증된 고객 반응을 기준으로 구독형/반복 구매 모델을 확장합니다.",
            },
        ]
        if request.focused_section.get("body"):
            sections.append({
                "title": f"{focused_title} 보완 메모",
                "body": str(request.focused_section["body"])[:260],
            })

        score = 86 if request.support_program else 78
        data = self.agent_data(
            position=f"{support_title} 제출용으로는 {idea_name}의 검증 계획과 자금 사용처를 명확히 보여주는 구성이 적합합니다.",
            evidence={
                "target": support_title,
                "idea_name": idea_name,
                "focused_section": focused_title,
            },
            score=score,
            risks=["지원사업 세부 평가 기준과 실제 공고문 조건은 제출 전 재확인해야 합니다."],
            assumptions=[
                "현재 프로필, 선택 아이템, 지원사업 맥락을 기준으로 초안을 구성했습니다.",
                "세부 매출 추정치는 재무 Agent 결과와 함께 보완하는 전제입니다.",
            ],
            missing_inputs=[] if request.support_program else ["구체적인 지원사업 공고"],
            recommendation="사업 개요, 문제 정의, 해결 방안, 고객/시장, 수익 모델 순서로 먼저 제출용 초안을 다듬으세요.",
            payload={
                "target": support_title,
                "sections": sections,
                "focused_section": request.focused_section,
                "goal": request.goal,
            },
        )
        fallback = f"{support_title}에 맞춘 사업계획서 초안 {len(sections)}개 섹션을 만들었습니다."
        summary = await self.polish_summary(task="business plan draft", data=data, fallback=fallback)
        return AgentResponse(
            intent="plan",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "시장 분석 문단에 지역/고객 근거 추가",
                "지원금 사용 계획을 항목별 예산으로 분리",
                "30일 검증 계획을 일정표로 정리",
            ],
        )

    def _idea_from_context(self, context: dict[str, Any]) -> str | None:
        current_result = context.get("currentResult") if isinstance(context.get("currentResult"), dict) else {}
        idea_context = current_result.get("ideaContext") if isinstance(current_result.get("ideaContext"), dict) else {}
        selected_idea = idea_context or current_result.get("selectedIdea")
        if isinstance(selected_idea, dict) and selected_idea.get("title"):
            return str(selected_idea["title"])
        return None
