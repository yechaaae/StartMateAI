from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, PlanRequest


class PlanAgent(BaseAgent):
    name = "PlanAgent"

    async def run(self, request: PlanRequest) -> AgentResponse:
        idea_name = request.idea_name or self._idea_from_context(request.context) or "선택한 창업 아이템"
        announcement = (request.announcement or "").strip()
        support_title = (
            request.support_program.get("title")
            or request.target
            or "창업 지원사업"
        )
        focused_title = request.focused_section.get("title") or "전체 초안"

        # 기본(템플릿) 섹션 — 공고가 없거나 LLM이 꺼져 있을 때 fallback으로 사용한다.
        sections = self._template_sections(idea_name, support_title)
        if request.focused_section.get("body"):
            sections.append({
                "title": f"{focused_title} 보완 메모",
                "body": str(request.focused_section["body"])[:260],
            })

        # 공고문이 들어오면 그 내용(모집대상·지원내용·평가 관점·일정)에 맞춰 섹션을 실제로 다시 작성한다.
        # 기능 리포트 빠른 모드(FAST_FEATURE_REPORT)와 무관하게, 공고가 있을 때만 LLM을 호출한다.
        announcement_used = False
        if announcement:
            generated = await self._sections_from_announcement(
                announcement=announcement,
                idea_name=idea_name,
                target=support_title,
                profile=request.profile,
                goal=request.goal,
            )
            if generated:
                sections = generated
                announcement_used = True

        has_target = bool(request.support_program) or announcement_used
        score = 86 if has_target else 78
        assumptions = [
            "현재 프로필, 선택 아이템, 지원사업 맥락을 기준으로 초안을 구성했습니다.",
            "세부 매출 추정치는 재무 Agent 결과와 함께 보완하는 전제입니다.",
        ]
        if announcement_used:
            assumptions[0] = f"'{support_title}' 공고의 모집대상·지원내용·평가 관점을 반영해 초안을 구성했습니다."

        data = self.agent_data(
            position=f"{support_title} 제출용으로는 {idea_name}의 검증 계획과 자금 사용처를 명확히 보여주는 구성이 적합합니다.",
            evidence={
                "target": support_title,
                "idea_name": idea_name,
                "focused_section": focused_title,
                "announcement_reflected": announcement_used,
            },
            score=score,
            risks=["지원사업 세부 평가 기준과 실제 공고문 조건은 제출 전 재확인해야 합니다."],
            assumptions=assumptions,
            missing_inputs=[] if has_target else ["구체적인 지원사업 공고"],
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

    def _template_sections(self, idea_name: str, support_title: str) -> list[dict[str, str]]:
        return [
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

    async def _sections_from_announcement(
        self,
        *,
        announcement: str,
        idea_name: str,
        target: str,
        profile: Any,
        goal: str,
    ) -> list[dict[str, str]] | None:
        if not self.llm.is_enabled:
            return None
        try:
            profile_text = json.dumps(profile.model_dump(), ensure_ascii=False)[:1200]
        except Exception:
            profile_text = ""
        user_prompt = (
            "아래는 지원사업 '공고문'이며, 신청서 양식(작성해야 할 질문·항목 목록)이 함께 들어 있을 수 있습니다.\n"
            "이 내용에 '맞춰서' 제출용 답변 초안을 작성하세요.\n\n"
            "[작성 규칙]\n"
            "1) 신청서에 질문/항목(예: 창업 아이템, 지원동기, 창업여부, 주차별 교육 참가 확인, 알게 된 경로, 동의 등)이 있으면, "
            "각 항목을 하나의 섹션으로 만들어 그 항목에 대한 '실제 제출용 답변'을 작성하세요. "
            "이때 title은 항목명, body는 작성된 답변입니다.\n"
            "2) 창업 아이템·지원동기처럼 서술형 항목은 창업 아이템과 창업자 프로필에 근거해 구체적으로 쓰고, "
            "공고가 강조하는 가치(예: 사회적 가치)·지원내용·평가 관점을 반영하세요.\n"
            "3) 성명·연락처·이메일·거주지역처럼 개인정보라 알 수 없는 항목은 body에 "
            "'(직접 입력: 예시/형식 안내)'처럼 사용자가 채울 안내를 적으세요. 임의의 가짜 개인정보를 지어내지 마세요.\n"
            "4) 창업여부는 프로필상 예비창업자/기창업 여부에 맞게, 주차별 교육 참가 확인은 가능한 모든 차시 '참가'로, "
            "동의 항목은 '동의 함'으로 적으세요.\n"
            "5) 신청서 양식이 없고 공고문만 있으면, 공고에 맞춘 사업계획서 섹션"
            "(사업 개요·문제 정의·해결 방안·고객/시장·수익 모델)을 5~6개 작성하세요.\n"
            "6) 반드시 JSON 배열만 출력하세요. 형식: "
            '[{"title": "창업 아이템", "body": "..."}, ...]. 코드펜스나 설명 문장은 넣지 마세요.\n\n'
            f"[창업 아이템] {idea_name}\n"
            f"[지원사업/공고 제목] {target}\n"
            f"[작성 목표 코드] {goal}\n"
            f"[창업자 프로필] {profile_text}\n\n"
            f"[공고문 및 신청서 양식]\n{announcement[:4000]}"
        )
        try:
            raw = await self.llm.complete(
                system_prompt="You are a precise Korean startup business-plan writer who tailors drafts to a specific grant announcement.",
                user_prompt=user_prompt,
                temperature=0.3,
                fallback="",
            )
        except Exception:
            return None
        return self._parse_sections(raw)

    def _parse_sections(self, raw: str) -> list[dict[str, str]] | None:
        if not raw or not isinstance(raw, str):
            return None
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start:end + 1])
        except (ValueError, TypeError):
            return None
        if not isinstance(parsed, list):
            return None
        sections: list[dict[str, str]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            body = str(item.get("body") or "").strip()
            if not title or not body:
                continue
            sections.append({"title": title[:120], "body": body[:700]})
            if len(sections) >= 14:
                break
        return sections or None

    def _idea_from_context(self, context: dict[str, Any]) -> str | None:
        current_result = context.get("currentResult") if isinstance(context.get("currentResult"), dict) else {}
        idea_context = current_result.get("ideaContext") if isinstance(current_result.get("ideaContext"), dict) else {}
        selected_idea = idea_context or current_result.get("selectedIdea")
        if isinstance(selected_idea, dict) and selected_idea.get("title"):
            return str(selected_idea["title"])
        return None
