from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas import StartupProfile


class SupportProgramRetriever:
    def __init__(self, programs: list[dict[str, Any]]):
        self.programs = programs

    @classmethod
    def from_default(cls) -> "SupportProgramRetriever":
        data_path = Path(__file__).resolve().parents[1] / "data" / "support_programs.sample.json"
        return cls(json.loads(data_path.read_text(encoding="utf-8")))

    def search(self, *, profile: StartupProfile, query: str, limit: int) -> list[dict[str, Any]]:
        scored = []
        query_terms = self._terms(query)
        profile_terms = self._terms(
            " ".join(
                [
                    profile.region or "",
                    profile.startup_stage,
                    profile.major or "",
                    " ".join(profile.interests),
                    " ".join(profile.experiences),
                ]
            )
        )
        terms = query_terms | profile_terms

        for program in self.programs:
            haystack = self._terms(
                " ".join(
                    [
                        program.get("title", ""),
                        program.get("region", ""),
                        program.get("stage", ""),
                        " ".join(program.get("keywords", [])),
                        program.get("summary", ""),
                    ]
                )
            )
            score = len(terms & haystack) * 12
            if profile.region and program.get("region") in {profile.region, "전국"}:
                score += 25
            if profile.startup_stage and profile.startup_stage in program.get("stage", ""):
                score += 20
            if profile.budget_krw is not None and profile.budget_krw <= 3_000_000:
                score += 5

            item = dict(program)
            item["eligibility_score"] = min(score, 100)
            item["why_matched"] = self._why(profile, program)
            scored.append(item)

        scored.sort(key=lambda item: item["eligibility_score"], reverse=True)
        return scored[:limit]

    def _terms(self, text: str) -> set[str]:
        normalized = text.replace(",", " ").replace("/", " ").lower()
        return {term.strip() for term in normalized.split() if term.strip()}

    def _why(self, profile: StartupProfile, program: dict[str, Any]) -> list[str]:
        reasons = []
        if profile.region and program.get("region") in {profile.region, "전국"}:
            reasons.append("지역 조건 적합")
        if profile.startup_stage and profile.startup_stage in program.get("stage", ""):
            reasons.append("창업 단계 적합")
        overlap = set(profile.interests) & set(program.get("keywords", []))
        if overlap:
            reasons.append("관심 분야 일치: " + ", ".join(sorted(overlap)))
        return reasons or ["기본 조건 검토 필요"]
