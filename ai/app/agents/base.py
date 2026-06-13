from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any

from app.core.gms_client import GMSClient


# 기능 리포트(ITEM/SUPPORT/PLAN) 빠른 모드 플래그.
# 오케스트레이터가 Agent 실행 직전에 True로 세팅하면, 각 Agent의 polish_summary가
# LLM 호출 없이 즉시 fallback을 돌려줘 리포트 1건당 LLM 호출 수를 절반 가까이 줄인다.
# asyncio.gather는 태스크 생성 시점의 컨텍스트를 복사하므로 gather 전에 set하면
# 병렬 Agent 코루틴들에서도 이 값이 보인다.
FAST_FEATURE_REPORT: ContextVar[bool] = ContextVar("fast_feature_report", default=False)


class BaseAgent:
    name = "base"
    contract_version = "1.0"

    def __init__(self, llm: GMSClient):
        self.llm = llm

    def agent_data(
        self,
        *,
        position: str,
        evidence: Any,
        score: int,
        risks: list[str] | None,
        assumptions: list[str] | None,
        missing_inputs: list[str] | None,
        recommendation: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = {
            "agent_contract_version": self.contract_version,
            "position": position,
            "evidence": evidence,
            "score": max(0, min(100, score)),
            "risks": risks or [],
            "assumptions": assumptions or [],
            "missing_inputs": missing_inputs or [],
            "recommendation": recommendation,
        }
        data.update(payload or {})
        return data

    async def polish_summary(
        self,
        *,
        task: str,
        data: dict[str, Any],
        fallback: str,
        instructions: str | None = None,
    ) -> str:
        if not self.llm.is_enabled or FAST_FEATURE_REPORT.get():
            return fallback

        prompt = (
            "아래 JSON 결과를 바탕으로 한국어 답변을 작성하세요.\n"
            "- 딱딱한 보고서 말투보다, 옆에서 같이 판단해주는 상담 톤으로 말하세요.\n"
            "- 단순 요약만 하지 말고 판단, 숫자/사실 근거, 다음 행동을 자연스럽게 포함하세요.\n"
            "- data.evidence, risks, assumptions, missing_inputs, recommendation에 있는 내용을 적극적으로 반영하세요.\n"
            "- 근거가 부족하면 '이건 아직 확정하기 어렵고, 이 정보가 더 필요해요'처럼 대화식으로 말하세요.\n"
            "- 공고/법률/비용처럼 출처나 계산 근거가 있는 항목은 이름과 수치를 그대로 언급하세요.\n"
            "- 과장하지 말고 4~8줄 정도로 쓰되, 가독성을 위해 가벼운 마크다운을 쓰세요: "
            "핵심 수치/키워드는 **굵게**, 항목 나열은 `- 불릿`, 비교가 필요하면 짧은 표. "
            "다만 짧은 답변은 굳이 구조화하지 말고 자연스러운 문장으로 두세요.\n\n"
            f"{instructions.strip() + chr(10) + chr(10) if instructions else ''}"
            f"task: {task}\n"
            f"data: {json.dumps(data, ensure_ascii=False)}"
        )
        try:
            return await self.llm.complete(
                system_prompt="You are a warm but precise Korean startup execution assistant.",
                user_prompt=prompt,
                temperature=0.25,
                fallback=fallback,
            )
        except Exception:
            return fallback
