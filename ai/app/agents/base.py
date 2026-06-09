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
            "아래 JSON 결과를 바탕으로 사용자가 바로 이해할 수 있는 한국어 요약을 "
            "2문장 이내로 작성하세요. 과장하지 말고 다음 행동을 포함하세요.\n\n"
            f"{instructions.strip() + chr(10) + chr(10) if instructions else ''}"
            f"task: {task}\n"
            f"data: {json.dumps(data, ensure_ascii=False)}"
        )
        try:
            return await self.llm.complete(
                system_prompt="You are a concise startup execution assistant.",
                user_prompt=prompt,
                temperature=0.2,
                fallback=fallback,
            )
        except Exception:
            return fallback
