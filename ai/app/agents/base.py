from __future__ import annotations

import json
from typing import Any

from app.core.gms_client import GMSClient


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
        if not self.llm.is_enabled:
            return fallback

        prompt = (
            "아래 JSON 결과를 바탕으로 한국어 답변을 작성하세요.\n"
            "- 딱딱한 보고서 말투보다, 옆에서 같이 판단해주는 상담 톤으로 말하세요.\n"
            "- 단순 요약만 하지 말고 판단, 숫자/사실 근거, 다음 행동을 자연스럽게 포함하세요.\n"
            "- data.evidence, risks, assumptions, missing_inputs, recommendation에 있는 내용을 적극적으로 반영하세요.\n"
            "- 근거가 부족하면 '이건 아직 확정하기 어렵고, 이 정보가 더 필요해요'처럼 대화식으로 말하세요.\n"
            "- 공고/법률/비용처럼 출처나 계산 근거가 있는 항목은 이름과 수치를 그대로 언급하세요.\n"
            "- 과장하지 말고 4~8줄 정도로 쓰되, 필요한 경우 줄바꿈과 bullet을 사용하세요.\n\n"
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
