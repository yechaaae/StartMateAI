from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings


class GMSClient:
    """Small adapter around the hackathon GMS LLM API.

    GMS can proxy OpenAI-compatible chat completions and Gemini
    `generateContent` endpoints.
    If the hackathon gateway changes the request contract, only
    `_build_payload`, `_build_headers`, and `_extract_content` should need
    changes.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.gms_api_key and self.settings.gms_base_url)

    @property
    def is_enabled(self) -> bool:
        return self.is_configured and not self.settings.use_mock_llm

    async def complete(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        fallback: str = "",
    ) -> str:
        if not self.is_enabled:
            return fallback

        url = self.settings.gms_base_url.rstrip("/") + "/" + self.settings.gms_chat_path.lstrip("/")
        payload = self._build_payload(system_prompt, user_prompt, temperature)

        async with httpx.AsyncClient(timeout=self.settings.gms_timeout_seconds) as client:
            response = await client.post(
                url,
                params=self._build_query_params(),
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            if not response.content:
                return fallback
            try:
                data = response.json()
            except ValueError:
                return fallback
            content = self._extract_content(data).strip()
            return content or fallback

    def _build_payload(self, system_prompt: str, user_prompt: str, temperature: float) -> dict[str, Any]:
        if self._uses_gemini_generate_content():
            return {
                "systemInstruction": {
                    "parts": [{"text": system_prompt}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                },
            }

        payload = {
            "model": self.settings.gms_model,
            "messages": [
                {"role": "developer", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if not self._uses_default_only_temperature_model() and temperature != 1:
            payload["temperature"] = temperature
        return payload

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        key_header = self.settings.gms_api_key_header
        if not key_header:
            return headers
        if key_header.lower() == "authorization":
            scheme = self.settings.gms_auth_scheme.strip()
            headers[key_header] = f"{scheme} {self.settings.gms_api_key}".strip()
        else:
            headers[key_header] = self.settings.gms_api_key
        return headers

    def _build_query_params(self) -> dict[str, str]:
        query_param = self.settings.gms_api_key_query_param.strip()
        if not query_param:
            return {}
        return {query_param: self.settings.gms_api_key}

    def _extract_content(self, data: dict[str, Any]) -> str:
        candidates = data.get("candidates")
        if candidates:
            content = candidates[0].get("content") or {}
            parts = content.get("parts") or []
            texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
            text = "\n".join(item for item in texts if item)
            if text:
                return text

        choices = data.get("choices")
        if choices:
            first = choices[0]
            message = first.get("message") or {}
            if isinstance(message, dict) and message.get("content"):
                return str(message["content"])
            if first.get("text"):
                return str(first["text"])

        for key in ("output_text", "content", "message", "answer"):
            value = data.get(key)
            if isinstance(value, str):
                return value

        return json.dumps(data, ensure_ascii=False)

    def _uses_gemini_generate_content(self) -> bool:
        return self.settings.gms_chat_path.endswith(":generateContent")

    def _uses_default_only_temperature_model(self) -> bool:
        return self.settings.gms_model.startswith("gpt-5")
