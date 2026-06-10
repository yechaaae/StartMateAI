from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings


class BackendToolClient:
    def __init__(self, settings: Settings):
        self.base_url = settings.backend_internal_base_url.rstrip("/")
        self.token = settings.internal_tool_token
        self.timeout_seconds = settings.backend_tool_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.token)

    async def sync_support_programs(self, source: str = "all") -> dict[str, Any]:
        return await self._post(
            "/api/internal/ai-tools/support-programs/sync",
            params={"source": source},
            json_body={},
        )

    async def recommend_support_programs(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        response = await self._post("/api/internal/ai-tools/support-programs/recommend", json_body=payload)
        return response if isinstance(response, list) else []

    async def list_support_programs(self) -> list[dict[str, Any]]:
        response = await self._get("/api/internal/ai-tools/support-programs")
        return response if isinstance(response, list) else []

    async def analyze_commercial_area(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = await self._post("/api/internal/ai-tools/commercial-areas/analyze", json_body=payload)
        return response if isinstance(response, dict) else {}

    async def _get(self, path: str, *, params: dict[str, Any] | None = None):
        if not self.is_configured:
            raise RuntimeError("Backend tool client is not configured.")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers={"X-Startmate-Internal-Token": self.token},
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def _post(
        self,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ):
        if not self.is_configured:
            raise RuntimeError("Backend tool client is not configured.")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers={"X-Startmate-Internal-Token": self.token},
                params=params,
                json=json_body or {},
            )
            response.raise_for_status()
            return response.json()
