from __future__ import annotations

import json
from typing import Any

from app.core.gms_client import GMSClient


class BaseAgent:
    name = "base"

    def __init__(self, llm: GMSClient):
        self.llm = llm

    async def polish_summary(self, *, task: str, data: dict[str, Any], fallback: str) -> str:
        if not self.llm.is_enabled:
            return fallback

        prompt = (
            "아래 JSON 결과를 바탕으로 사용자가 바로 이해할 수 있는 한국어 요약을 "
            "2문장 이내로 작성하세요. 과장하지 말고 다음 행동을 포함하세요.\n\n"
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
