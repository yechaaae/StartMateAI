from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, IdeaRequest, StartupProfile


class IdeaAgent(BaseAgent):
    name = "IdeaAgent"

    async def run(self, request: IdeaRequest) -> AgentResponse:
        profile = request.profile
        budget = profile.budget_krw or 3_000_000
        candidate_limit = max(5, min(8, request.count + 3))
        raw_candidates, generation, warnings = await self._candidate_pool(profile, candidate_limit)
        candidates = [self._score_candidate(profile, budget, candidate) for candidate in raw_candidates]
        candidates.sort(key=lambda item: item["match_score"], reverse=True)

        selected = self._select_diverse_candidates(candidates, request.count)
        if not selected:
            selected = candidates[: request.count]
        if not selected:
            return await self._empty_recommendation_response(profile, budget, generation, warnings)
        top = selected[0]
        missing_inputs = self._missing_inputs(profile)
        ranking_basis = [
            "경험/전공 적합도",
            "관심 분야 적합도",
            "초기비용 적합도",
            "채널 적합도",
            "리스크 성향",
            "지역성",
            "투입 시간 적합도",
            "30일 검증 가능성",
        ]

        data = self.agent_data(
            position=f"{top['title']}이 현재 조건에서 가장 실행 가능성이 높습니다.",
            evidence={
                "top_idea": top,
                "ranking_basis": ranking_basis,
                "generation": generation,
                "quality_checks": self._quality_checks(selected),
            },
            score=int(top["match_score"]),
            risks=top["risks"],
            assumptions=[
                f"초기 예산은 {budget:,}원으로 계산했습니다.",
                "아이디어 생성은 LLM 후보를 우선 사용하고, 코드는 예산/시간/리스크/검증 가능성을 재점수화합니다.",
                "고객 검증 전에는 고정비를 최소화하는 실행안을 우선했습니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation=f"{top['title']}을 1순위로 두고 비용 시뮬레이션과 30일 체험을 실행하세요.",
            payload={
                "recommendations": selected,
                "all_candidates": candidates,
                "generation": generation,
                "ranking_basis": ranking_basis,
                "quality_checks": self._quality_checks(selected),
                "decision_rules": [
                    "예산 초과 후보는 감점",
                    "전공/경험/관심 키워드가 겹치면 가점",
                    "낮은 리스크 성향이면 고정비가 낮은 아이템 가점",
                    "선호 채널과 판매 방식이 맞으면 가점",
                    "30일 안에 실제 고객 반응을 볼 수 있으면 가점",
                    "주당 투입 가능 시간이 부족하면 운영 난이도가 높은 후보 감점",
                ],
            },
        )
        fallback = f"{len(selected)}개의 창업 아이템을 실행 가능성 기준으로 추천했습니다."
        summary = await self.polish_summary(
            task="startup idea recommendation",
            data=data,
            fallback=fallback,
            instructions=(
                "IdeaAgent 요약 규칙:\n"
                "- 아이디어 이름만 나열하지 말고 왜 이 사용자에게 맞는지 말하세요.\n"
                "- 1순위 아이템과 바로 검증할 첫 행동을 포함하세요.\n"
                "- LLM 생성 후보를 과장하지 말고 예산/경험/리스크 제약을 같이 언급하세요."
            ),
        )

        return AgentResponse(
            intent="idea",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "1순위 아이템의 예상 비용과 손익분기점 계산",
                "지역 지원사업 매칭으로 초기 비용 보완",
                "30일 테스트 계획을 할 일 목록으로 전환",
            ],
            warnings=warnings,
        )

    async def _candidate_pool(
        self,
        profile: StartupProfile,
        count: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
        warnings: list[str] = []
        llm_diagnostics: dict[str, Any] | None = None
        if self.llm.is_enabled:
            candidates, llm_diagnostics = await self._generate_candidates_with_llm(profile, count)
            if candidates:
                return (
                    candidates,
                    {
                        "generated_by": "llm",
                        "fallback_used": False,
                        "requested_count": count,
                        "candidate_count": len(candidates),
                        "diagnostics": llm_diagnostics,
                    },
                    warnings,
                )
            warnings.extend(llm_diagnostics.get("warnings", []) if llm_diagnostics else [])
            warnings.append("idea_llm_generation_failed_no_recommendations")
        else:
            warnings.append("idea_llm_disabled_no_recommendations")

        generation = {
            "generated_by": "none",
            "fallback_used": False,
            "llm_enabled": self.llm.is_enabled,
            "requested_count": count,
            "candidate_count": 0,
            "rule_fallback_disabled": True,
        }
        if llm_diagnostics:
            generation["llm_diagnostics"] = llm_diagnostics
        return ([], generation, warnings)

    async def _empty_recommendation_response(
        self,
        profile: StartupProfile,
        budget: int,
        generation: dict[str, Any],
        warnings: list[str],
    ) -> AgentResponse:
        missing_inputs = self._missing_inputs(profile)
        data = self.agent_data(
            position="아이템 후보를 생성할 수 없어 추천을 확정하지 않았습니다.",
            evidence={
                "generation": generation,
                "ranking_basis": [],
                "quality_checks": {
                    "count": 0,
                    "strategies": [],
                    "within_budget": 0,
                    "needs_trimmed_mvp": 0,
                    "quality_flags": ["no_generated_candidates"],
                },
            },
            score=0,
            risks=[
                "LLM 후보 생성 결과가 없어 템플릿 아이템을 추천처럼 노출하지 않았습니다.",
                *warnings,
            ],
            assumptions=[
                f"초기 예산은 {budget:,}원으로 확인했습니다.",
                "근거 없는 rule fallback 후보는 저장 리포트와 화면 추천에 사용하지 않습니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation="지역, 예산, 관심 분야를 확인한 뒤 AI 생성 설정 또는 외부 LLM 응답을 점검하고 다시 추천을 요청하세요.",
            payload={
                "recommendations": [],
                "all_candidates": [],
                "generation": generation,
                "ranking_basis": [],
                "quality_checks": {
                    "count": 0,
                    "strategies": [],
                    "within_budget": 0,
                    "needs_trimmed_mvp": 0,
                    "quality_flags": ["no_generated_candidates"],
                },
                "decision_rules": [
                    "LLM 후보가 없으면 템플릿 후보를 추천처럼 만들지 않음",
                    "후보 제목, 고객, 검증 방법이 실제 생성 결과에 있을 때만 추천",
                    "상권/지원사업 근거는 리포트 단계에서 후보 점수 보정에만 사용",
                ],
            },
        )
        summary = await self.polish_summary(
            task="startup idea recommendation unavailable",
            data=data,
            fallback=(
                "아이템 후보를 만들 수 있는 LLM 결과가 없어 추천을 확정하지 않았습니다. "
                "예전처럼 템플릿 후보를 목업처럼 보여주지 않고, 생성 설정과 입력 조건을 확인한 뒤 다시 요청해야 합니다."
            ),
        )
        return AgentResponse(
            intent="idea",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "LLM/API 설정과 응답 로그 확인",
                "지역, 예산, 관심 분야를 구체화한 뒤 다시 추천 요청",
                "상권/지원사업 데이터가 붙는지 리포트 생성 로그 확인",
            ],
            warnings=data["risks"],
        )

    async def _generate_candidates_with_llm(
        self,
        profile: StartupProfile,
        count: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        diagnostics: dict[str, Any] = {
            "attempted": True,
            "warnings": [],
            "requested_count": count,
        }
        prompt = (
            "너는 창업 아이템 발굴 에이전트다. 사용자의 프로필을 보고 30일 안에 검증 가능한 창업 아이템 후보를 생성해라.\n"
            "반드시 JSON object 하나만 출력해라. Markdown, 설명문, 주석은 출력하지 마라.\n\n"
            "생성 규칙:\n"
            "- 사용자의 전공, 경험, 지역, 예산, 관심 분야, 선호 채널, 투입 가능 시간을 반영해라.\n"
            "- 없는 경험을 지어내지 마라. confirmed_absent_fields에 experiences가 있으면 경험 기반 아이디어라고 쓰지 마라.\n"
            "- 예산 안에서 작게 검증 가능한 형태를 우선해라.\n"
            "- 고정비가 큰 매장 창업은 바로 추천하지 말고 팝업, 예약판매, 공유공간, 위탁, 파일럿 형태로 낮춰라.\n"
            "- 각 아이템은 실제 고객 반응을 30일 안에 볼 수 있어야 한다.\n"
            "- 법률/인허가/위생/상표/개인정보 리스크가 있으면 risks에 명시해라.\n"
            "- 후보는 서로 충분히 달라야 한다.\n\n"
            "출력 schema:\n"
            "{\n"
            '  "ideas": [\n'
            "    {\n"
            '      "title": string,\n'
            '      "business_type": "cafe"|"commerce"|"content"|"popup"|"service"|"food"|"other",\n'
            '      "target_customer": string,\n'
            '      "reason": string,\n'
            '      "why_fit": string[],\n'
            '      "keywords": string[],\n'
            '      "channels": string[],\n'
            '      "estimated_initial_cost_krw": number,\n'
            '      "fixed_cost_level": "low"|"medium"|"high",\n'
            '      "difficulty": "낮음"|"중간"|"높음",\n'
            '      "first_30_days": string[],\n'
            '      "validation_method": string,\n'
            '      "risks": string[]\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            f"candidate_count: {count}\n"
            f"profile: {json.dumps(profile.model_dump(), ensure_ascii=False)}"
        )
        last_error: Exception | None = None
        for attempt in range(1, 3):
            diagnostics["attempt"] = attempt
            try:
                raw = await self.llm.complete(
                    system_prompt="You are a strict JSON startup idea generation engine.",
                    user_prompt=prompt,
                    temperature=0.45,
                    fallback="{}",
                )
                diagnostics["raw_preview"] = self._debug_preview(raw)
                parsed = self._parse_json_object(raw)
                diagnostics["parsed_type"] = type(parsed).__name__
                ideas = parsed.get("ideas") if isinstance(parsed, dict) else None
                if not isinstance(ideas, list):
                    diagnostics["failure_reason"] = "missing_or_invalid_ideas_array"
                    diagnostics["parsed_keys"] = sorted(parsed) if isinstance(parsed, dict) else []
                    if attempt == 1:
                        continue
                    diagnostics["warnings"].append("idea_llm_generation_missing_ideas_array")
                    return [], diagnostics

                prompt_guardrails = self._idea_prompt_guardrails()
                if prompt_guardrails and isinstance(parsed, dict):
                    diagnostics["guardrails"] = prompt_guardrails
                candidates = self._sanitize_candidates(ideas, profile, source="llm")[:count]
                diagnostics["parsed_idea_count"] = len(ideas)
                diagnostics["sanitized_candidate_count"] = len(candidates)
                if candidates:
                    diagnostics["attempts"] = attempt
                    return candidates, diagnostics
                diagnostics["failure_reason"] = "no_valid_candidates_after_sanitize"
                if attempt == 1:
                    continue
                diagnostics["warnings"].append("idea_llm_generation_no_valid_candidates")
                return [], diagnostics
            except Exception as error:
                last_error = error
                if attempt == 1:
                    continue

        diagnostics["failure_reason"] = "exception"
        diagnostics["attempts"] = 2
        diagnostics["error_type"] = last_error.__class__.__name__ if last_error else "UnknownError"
        diagnostics["error_message"] = self._debug_preview(str(last_error or ""), limit=1000)
        diagnostics["warnings"].append(f"idea_llm_generation_error:{diagnostics['error_type']}")
        return [], diagnostics

    def _idea_prompt_guardrails(self) -> list[str]:
        return [
            "Use the user's major as execution capability, not as a forced product theme.",
            "Prefer low-fixed-cost MVPs that can collect customer evidence within 30 days.",
            "Titles must sound like real customer-facing offers.",
            "Do not recommend full offline stores when the budget only supports a test.",
        ]

    def _debug_preview(self, value: Any, *, limit: int = 800) -> str:
        text = self._redact_sensitive(str(value)).replace("\r", "\\r").replace("\n", "\\n")
        if len(text) <= limit:
            return text
        return text[:limit] + "...<truncated>"

    def _redact_sensitive(self, text: str) -> str:
        settings = getattr(self.llm, "settings", None)
        api_key = getattr(settings, "gms_api_key", "") if settings else ""
        if api_key:
            text = text.replace(api_key, "<redacted>")
        return text

    def _sanitize_candidates(
        self,
        items: list[Any],
        profile: StartupProfile,
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        candidates = []
        seen_titles = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title or title in seen_titles:
                continue
            title = self._normalize_forced_major_title(title, item, profile)
            seen_titles.add(title)

            estimated_cost = self._coerce_money(item.get("estimated_initial_cost_krw"))
            candidate = {
                "title": title,
                "business_type": self._normalize_business_type(item.get("business_type"), item),
                "target_customer": str(item.get("target_customer") or self._default_target_customer(profile)).strip(),
                "reason": str(item.get("reason") or "사용자 프로필과 30일 검증 가능성을 기준으로 생성했습니다.").strip(),
                "why_fit": self._to_list(item.get("why_fit")),
                "keywords": self._ordered_unique(
                    [
                        *self._to_list(item.get("keywords")),
                        *self._keywords_from_candidate(item),
                    ]
                ),
                "channels": self._normalize_channels(item.get("channels"), profile),
                "estimated_initial_cost_krw": estimated_cost or self._default_cost_estimate(profile, item),
                "fixed_cost_level": self._normalize_fixed_cost(item.get("fixed_cost_level"), estimated_cost),
                "difficulty": self._normalize_difficulty(item.get("difficulty")),
                "first_30_days": self._normalize_first_30_days(item.get("first_30_days"), title),
                "validation_method": str(item.get("validation_method") or "30일 안에 예약/문의/구매 의사를 측정합니다.").strip(),
                "risks": self._normalize_risks(item.get("risks")),
                "generated_by": source,
            }
            candidate.update(self._candidate_enrichment(candidate, profile))
            if not candidate["keywords"]:
                candidate["keywords"] = self._keywords_from_candidate(candidate)
            candidates.append(candidate)
        return candidates

    def _select_diverse_candidates(self, candidates: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
        selected: list[dict[str, Any]] = []
        used_types: set[str] = set()
        used_strategies: set[str] = set()
        major_driven_count = 0
        for candidate in candidates:
            strategy = str(candidate.get("strategy") or "")
            business_type = str(candidate.get("business_type") or "")
            if self._is_major_driven_candidate(candidate) and major_driven_count >= 1:
                continue
            if len(selected) < count and strategy not in used_strategies:
                selected.append(candidate)
                used_strategies.add(strategy)
                used_types.add(business_type)
                if self._is_major_driven_candidate(candidate):
                    major_driven_count += 1
        for candidate in candidates:
            if len(selected) >= count:
                break
            business_type = str(candidate.get("business_type") or "")
            if candidate in selected:
                continue
            if self._is_major_driven_candidate(candidate) and major_driven_count >= 1:
                continue
            if business_type in used_types and len(selected) < max(2, count - 1):
                continue
            selected.append(candidate)
            used_types.add(business_type)
            if self._is_major_driven_candidate(candidate):
                major_driven_count += 1
        for candidate in candidates:
            if len(selected) >= count:
                break
            if candidate not in selected:
                if self._is_major_driven_candidate(candidate) and major_driven_count >= 1:
                    continue
                selected.append(candidate)
                if self._is_major_driven_candidate(candidate):
                    major_driven_count += 1
        for candidate in candidates:
            if len(selected) >= count:
                break
            if candidate not in selected:
                selected.append(candidate)
        return selected[:count]

    def _is_major_driven_candidate(self, candidate: dict[str, Any]) -> bool:
        text = " ".join(
            [
                str(candidate.get("title") or ""),
                str(candidate.get("reason") or ""),
                " ".join(map(str, candidate.get("keywords") or [])),
                " ".join(map(str, candidate.get("why_fit") or [])),
            ]
        ).lower()
        return any(
            keyword in text
            for keyword in ["전자", "공학", "전기", "ai", "스마트", "로봇", "부품", "기기", "자동화", "소프트웨어"]
        )

    def _candidate_enrichment(self, candidate: dict[str, Any], profile: StartupProfile) -> dict[str, Any]:
        budget = profile.budget_krw or 3_000_000
        estimated_cost = int(candidate.get("estimated_initial_cost_krw") or budget)
        business_type = str(candidate.get("business_type") or "other")
        fixed_cost = str(candidate.get("fixed_cost_level") or "medium")
        difficulty = str(candidate.get("difficulty") or "")
        if estimated_cost <= budget and fixed_cost == "low":
            strategy = "safe"
        elif estimated_cost <= int(budget * 1.6):
            strategy = "growth"
        else:
            strategy = "experiment"

        if estimated_cost <= budget:
            feasibility_label = "within_budget"
        elif estimated_cost <= int(budget * 1.5):
            feasibility_label = "needs_trimmed_mvp"
        else:
            feasibility_label = "needs_support_or_pivot"

        return {
            "strategy": strategy,
            "feasibility_label": feasibility_label,
            "customer_problem": self._customer_problem(candidate),
            "mvp_variant": self._mvp_variant(candidate, budget),
            "execution_note": self._execution_note(candidate, profile),
            "quality_flags": self._candidate_quality_flags(candidate, profile),
            "difficulty": difficulty or candidate.get("difficulty"),
            "business_type": business_type,
        }

    def _guardrail_candidates(self, profile: StartupProfile, budget: int) -> list[dict[str, Any]]:
        region = profile.region or "로컬"
        channels = profile.preferred_channels or ["SNS", "오프라인"]
        items: list[dict[str, Any]] = [
            {
                "title": f"{region} 소상공인 SNS 숏폼 대행",
                "business_type": "content",
                "target_customer": f"{region} 소상공인",
                "reason": "초기 장비와 재고 부담이 낮고, 샘플 콘텐츠로 30일 안에 유료 전환 가능성을 확인할 수 있습니다.",
                "why_fit": ["소자본으로 시작 가능", "지역 매장 네트워크와 결합 가능"],
                "keywords": ["SNS", "콘텐츠", "로컬", "소상공인"],
                "channels": channels,
                "estimated_initial_cost_krw": min(max(500_000, int(budget * 0.6)), 1_200_000),
                "fixed_cost_level": "low",
                "difficulty": "쉬움",
                "first_30_days": ["가게 20곳 리스트업", "샘플 콘텐츠 3개 제작", "유료 패키지 1건 제안"],
                "validation_method": "상담 전환율과 유료 패키지 제안 수락률을 봅니다.",
                "risks": ["초기 포트폴리오가 약하면 전환이 낮을 수 있습니다."],
            },
            {
                "title": f"{region} 직장인 대상 소량 예약 도시락",
                "business_type": "food",
                "target_customer": f"{region} 직장인과 1인 가구",
                "reason": "매장 임대 없이 사전 예약 수량만큼 테스트해 재고와 고정비를 줄일 수 있습니다.",
                "why_fit": ["예약판매로 수요 검증 가능", "초기 메뉴를 작게 시작 가능"],
                "keywords": ["푸드", "예약판매", "로컬"],
                "channels": channels,
                "estimated_initial_cost_krw": min(max(700_000, int(budget * 0.9)), 1_500_000),
                "fixed_cost_level": "low",
                "difficulty": "중간",
                "first_30_days": ["메뉴 2개 선정", "사전예약 폼 오픈", "20식 판매 여부 확인"],
                "validation_method": "예약 수량, 재구매 의사, 원가율을 측정합니다.",
                "risks": ["식품 제조/판매 신고와 위생 요건 확인이 필요합니다."],
            },
            {
                "title": f"{region} 예비창업자 지원사업 서류 체크 서비스",
                "business_type": "service",
                "target_customer": "예비창업자와 초기 창업자",
                "reason": "지식 기반 서비스라 초기 비용이 낮고, 무료 체크리스트로 고객 반응을 빠르게 볼 수 있습니다.",
                "why_fit": ["온라인 판매 가능", "지원사업 데이터와 연결 가능"],
                "keywords": ["지원사업", "서류", "체크리스트", "창업"],
                "channels": ["온라인", "SNS"],
                "estimated_initial_cost_krw": min(max(300_000, int(budget * 0.5)), 900_000),
                "fixed_cost_level": "low",
                "difficulty": "중간",
                "first_30_days": ["공고 10개 분석", "체크리스트 템플릿 제작", "예비창업자 5명 인터뷰"],
                "validation_method": "템플릿 다운로드와 유료 상담 신청 수를 봅니다.",
                "risks": ["공고 정보 정확도와 책임 범위를 명확히 고지해야 합니다."],
            },
        ]
        if profile.major and any(term in profile.major.lower() for term in ["전자", "공학", "컴퓨터", "소프트웨어", "ai"]):
            items.append(
                {
                    "title": f"{region} 소상공인 디지털 운영 진단",
                    "business_type": "service",
                    "target_customer": f"{region} 작은 매장",
                    "reason": "전공 역량을 상품명에 억지로 붙이지 않고, 예약/결제/홍보 동선 개선이라는 실제 문제 해결에 씁니다.",
                    "why_fit": ["전공은 실행 역량으로 활용", "방문 인터뷰로 빠른 검증 가능"],
                    "keywords": ["운영진단", "디지털", "소상공인", "로컬"],
                    "channels": channels,
                    "estimated_initial_cost_krw": min(max(400_000, int(budget * 0.7)), 1_000_000),
                    "fixed_cost_level": "low",
                    "difficulty": "중간",
                    "first_30_days": ["매장 10곳 인터뷰", "문제 체크리스트 제작", "유료 진단 1건 제안"],
                    "validation_method": "진단 제안 수락률과 반복 요청 여부를 봅니다.",
                    "risks": ["서비스 범위를 좁히지 않으면 작업량이 커질 수 있습니다."],
                }
            )
        return self._sanitize_candidates(items, profile, source="guardrail")

    def _customer_problem(self, candidate: dict[str, Any]) -> str:
        business_type = str(candidate.get("business_type") or "")
        if business_type in {"food", "cafe", "popup"}:
            return "가까운 곳에서 믿고 살 수 있는 간편한 메뉴가 필요합니다."
        if business_type == "content":
            return "작은 매장이 꾸준히 홍보할 콘텐츠와 실행 시간이 부족합니다."
        if business_type == "service":
            return "창업자나 소상공인이 반복 업무를 혼자 정리하기 어렵습니다."
        if business_type == "commerce":
            return "작게 검증 가능한 틈새 상품과 구매 채널이 필요합니다."
        return "고객의 반복 불편을 작게 해결할 수 있는지 검증해야 합니다."

    def _mvp_variant(self, candidate: dict[str, Any], budget: int) -> dict[str, Any]:
        estimated = int(candidate.get("estimated_initial_cost_krw") or budget)
        if estimated <= budget:
            return {
                "name": "원안 MVP",
                "budget_krw": estimated,
                "change": "현재 예산 안에서 30일 테스트를 바로 설계할 수 있습니다.",
            }
        trimmed = max(300_000, min(budget, int(estimated * 0.55)))
        return {
            "name": "축소 MVP",
            "budget_krw": trimmed,
            "change": "재고, 장비, 공간비를 줄이고 예약/상담/샘플 판매로 먼저 검증합니다.",
        }

    def _execution_note(self, candidate: dict[str, Any], profile: StartupProfile) -> str:
        major = profile.major or ""
        if major and any(term in major.lower() for term in ["전자", "공학", "컴퓨터", "소프트웨어", "ai"]):
            return "전공은 상품 컨셉이 아니라 자동화, 데이터 정리, 운영 개선 역량으로 반영했습니다."
        if profile.experiences:
            return "기존 경험은 고객 접점과 실행 속도를 높이는 근거로 반영했습니다."
        return "경험 정보가 부족해 30일 고객 반응 검증 가능성을 더 크게 반영했습니다."

    def _candidate_quality_flags(self, candidate: dict[str, Any], profile: StartupProfile) -> list[str]:
        flags: list[str] = []
        budget = profile.budget_krw or 3_000_000
        estimated = int(candidate.get("estimated_initial_cost_krw") or 0)
        if estimated > budget:
            flags.append("budget_over_mvp_needed")
        if candidate.get("fixed_cost_level") == "high":
            flags.append("high_fixed_cost")
        if not candidate.get("validation_method"):
            flags.append("missing_validation_method")
        if self._looks_like_forced_major_blend(str(candidate.get("title") or ""), candidate, profile):
            flags.append("forced_major_blend")
        return flags

    def _quality_checks(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(candidates),
            "strategies": self._ordered_unique([str(item.get("strategy") or "") for item in candidates]),
            "within_budget": sum(1 for item in candidates if item.get("feasibility_label") == "within_budget"),
            "needs_trimmed_mvp": sum(1 for item in candidates if item.get("feasibility_label") == "needs_trimmed_mvp"),
            "quality_flags": self._ordered_unique(
                [
                    flag
                    for item in candidates
                    for flag in item.get("quality_flags", [])
                ]
            ),
        }

    def _fallback_candidates(self, profile: StartupProfile, count: int) -> list[dict[str, Any]]:
        region = profile.region or "거주 지역"
        interests = set(profile.interests + profile.preferred_business_types)
        major_text = profile.major or ""
        base_items: list[dict[str, Any]] = []

        if {"푸드", "카페", "cafe", "food"} & interests:
            base_items.extend(
                [
                    {
                        "title": f"{region} 한식 소량 예약 판매",
                        "business_type": "food",
                        "target_customer": f"{region} 1인 가구와 직장인",
                        "reason": "매장 임대 전에 메뉴 반응과 재구매 의사를 작게 검증할 수 있습니다.",
                        "why_fit": ["요식업 관심 분야와 연결", "초기 고정비를 낮출 수 있음"],
                        "keywords": ["푸드", "한식", "예약판매", "로컬", "오프라인"],
                        "channels": ["SNS", "오프라인"],
                        "estimated_initial_cost_krw": 2_500_000,
                        "fixed_cost_level": "low",
                        "difficulty": "중간",
                        "first_30_days": ["메뉴 3개 선정", "원가표 작성", "지인/SNS 예약 테스트"],
                        "validation_method": "예약 수, 재구매 의사, 원가율을 측정합니다.",
                        "risks": ["식품 제조/판매 신고와 위생 요건 확인 필요", "재구매율 검증 필요"],
                    },
                    {
                        "title": f"{region} 공유주방 팝업 메뉴 테스트",
                        "business_type": "popup",
                        "target_customer": f"{region} 점심/저녁 수요가 있는 직장인",
                        "reason": "상권과 메뉴 반응을 짧게 확인한 뒤 정식 매장 여부를 판단할 수 있습니다.",
                        "why_fit": ["요식업 관심과 지역 테스트에 적합", "매장 임대 전 검증 가능"],
                        "keywords": ["푸드", "팝업", "공유주방", "상권", "로컬"],
                        "channels": ["오프라인", "SNS"],
                        "estimated_initial_cost_krw": 4_000_000,
                        "fixed_cost_level": "medium",
                        "difficulty": "중간",
                        "first_30_days": ["공유주방 후보 조사", "시식/예약 이벤트", "고객 피드백 수집"],
                        "validation_method": "팝업 방문자 수, 객단가, 피드백을 측정합니다.",
                        "risks": ["장소비와 재료비가 늘 수 있음", "영업신고/위생 요건 확인 필요"],
                    },
                ]
            )

        if "전자공학" in major_text or "공학" in major_text:
            base_items.append(
                {
                    "title": f"{region} 소상공인 스마트 운영 점검 서비스",
                    "business_type": "service",
                    "target_customer": f"{region} 음식점과 소형 매장",
                    "reason": "전자공학 기반 문제 해결력을 매장 운영 개선 서비스로 전환할 수 있습니다.",
                    "why_fit": ["전공 역량 활용 가능", "재고 부담이 낮은 서비스형 모델"],
                    "keywords": ["전자공학", "소상공인", "운영", "서비스", "로컬"],
                    "channels": ["오프라인", "SNS"],
                    "estimated_initial_cost_krw": 1_500_000,
                    "fixed_cost_level": "low",
                    "difficulty": "중간",
                    "first_30_days": ["매장 10곳 인터뷰", "불편사항 체크리스트 제작", "유료 점검 1건 제안"],
                    "validation_method": "매장 인터뷰 수와 유료 전환 의사를 측정합니다.",
                    "risks": ["초기 신뢰 확보가 필요", "서비스 범위를 좁히지 않으면 납품 난이도가 커짐"],
                }
            )

        base_items.extend(
            [
                {
                    "title": f"{region} 로컬 매장 SNS 홍보 대행",
                    "business_type": "content",
                    "target_customer": f"{region} 소상공인",
                    "reason": "재고 없이 샘플 콘텐츠로 수요를 검증할 수 있습니다.",
                    "why_fit": ["고정비가 낮음", "SNS 채널 검증에 적합"],
                    "keywords": ["SNS", "콘텐츠", "홍보", "로컬", "소상공인"],
                    "channels": ["SNS", "오프라인"],
                    "estimated_initial_cost_krw": 1_200_000,
                    "fixed_cost_level": "low",
                    "difficulty": "낮음",
                    "first_30_days": ["상권 20곳 리스트업", "샘플 콘텐츠 3개 제작", "무료 진단 후 유료 패키지 제안"],
                    "validation_method": "상담 전환율과 유료 패키지 의사를 측정합니다.",
                    "risks": ["성과를 보여줄 샘플이 필요", "초기 고객 확보가 관건"],
                },
                {
                    "title": "지원사업 서류 체크리스트 서비스",
                    "business_type": "service",
                    "target_customer": "예비창업자와 초기창업자",
                    "reason": "지원사업 준비의 반복 업무를 템플릿과 코칭으로 서비스화할 수 있습니다.",
                    "why_fit": ["고정비가 낮음", "온라인으로 검증 가능"],
                    "keywords": ["지원사업", "체크리스트", "서류", "창업", "서비스"],
                    "channels": ["온라인", "SNS"],
                    "estimated_initial_cost_krw": 800_000,
                    "fixed_cost_level": "low",
                    "difficulty": "중간",
                    "first_30_days": ["지원사업 10개 분석", "체크리스트 템플릿 제작", "예비창업자 인터뷰 5명"],
                    "validation_method": "템플릿 다운로드와 상담 신청 수를 측정합니다.",
                    "risks": ["정책 정보 정확도가 낮으면 신뢰가 떨어짐"],
                },
            ]
        )

        return self._sanitize_candidates(base_items, profile, source="rule_fallback")[:count]

    def _score_candidate(
        self,
        profile: StartupProfile,
        budget: int,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        profile_terms = self._profile_terms(profile)
        candidate_terms = self._candidate_terms(candidate)
        keyword_overlap = sorted(profile_terms & candidate_terms)
        channel_overlap = sorted(set(profile.preferred_channels) & set(candidate.get("channels", [])))

        experience_terms = self._expand_profile_terms(self._terms([profile.major or "", *profile.experiences]))
        interest_terms = self._expand_profile_terms(self._terms([*profile.interests, *profile.preferred_business_types]))
        experience_fit = min(100, 38 + len(experience_terms & candidate_terms) * 16)
        if not profile.experiences and "experiences" in profile.confirmed_absent_fields:
            experience_fit = min(experience_fit, 55)
        interest_fit = min(100, 42 + len(interest_terms & candidate_terms) * 16)
        business_type_fit = self._business_type_fit(profile, candidate)
        interest_fit = max(interest_fit, business_type_fit)
        channel_fit = min(100, 52 + len(channel_overlap) * 18)
        if not profile.preferred_channels:
            channel_fit = 58
        budget_fit = self._budget_fit(budget, candidate["estimated_initial_cost_krw"])
        risk_fit = self._risk_fit(profile.risk_tolerance, candidate["fixed_cost_level"])
        local_opportunity = self._local_opportunity(profile, candidate)
        execution_fit = self._execution_fit(candidate["difficulty"])
        time_fit = self._time_fit(profile.available_hours_per_week, candidate)
        testability = self._testability_score(candidate)
        policy_fit = self._policy_fit(profile, candidate)

        score_breakdown = {
            "experience_fit": experience_fit,
            "interest_fit": interest_fit,
            "business_type_fit": business_type_fit,
            "budget_fit": budget_fit,
            "channel_fit": channel_fit,
            "risk_fit": risk_fit,
            "local_opportunity": local_opportunity,
            "execution_fit": execution_fit,
            "time_fit": time_fit,
            "testability": testability,
            "policy_fit": policy_fit,
        }
        weighted_score = int(
            experience_fit * 0.13
            + interest_fit * 0.20
            + budget_fit * 0.16
            + channel_fit * 0.11
            + risk_fit * 0.11
            + local_opportunity * 0.09
            + execution_fit * 0.08
            + time_fit * 0.07
            + testability * 0.05
        )
        result = dict(candidate)
        realism_penalty = self._realism_penalty(profile, candidate)
        result.update(
            {
                "match_score": max(0, min(100, weighted_score - realism_penalty)),
                "score_breakdown": score_breakdown,
                "matched_keywords": keyword_overlap,
                "matched_channels": channel_overlap,
                "why_recommended": self._why_recommended(candidate, keyword_overlap, channel_overlap, budget_fit),
                "risk": " / ".join(candidate["risks"]),
            }
        )
        if realism_penalty:
            result["score_breakdown"]["realism_penalty"] = realism_penalty
            result["risks"] = self._ordered_unique(
                [
                    *result.get("risks", []),
                    "전공/경험 키워드가 아이템 컨셉에 과하게 섞이지 않도록 고객 관점의 상품명과 판매 방식을 다시 좁혀야 합니다.",
                ]
            )
        return result

    def _normalize_forced_major_title(
        self,
        title: str,
        item: dict[str, Any],
        profile: StartupProfile,
    ) -> str:
        if not self._looks_like_forced_major_blend(title, item, profile):
            return title
        business_type = self._normalize_business_type(item.get("business_type"), item)
        region = profile.region or "로컬"
        if business_type in {"food", "cafe", "popup"}:
            if "도시락" in title or "식사" in title or "lunch" in title.lower():
                return f"{region} 직장인 대상 소량 예약 도시락"
            if "디저트" in title or "카페" in title or "음료" in title:
                return f"{region} 카페 메뉴 소량 예약판매"
            return f"{region} 소량 예약판매형 푸드 테스트"
        if business_type == "service":
            return f"{region} 소상공인 운영 문제 진단 서비스"
        return title

    def _looks_like_forced_major_blend(
        self,
        title: str,
        item: dict[str, Any],
        profile: StartupProfile,
    ) -> bool:
        major_text = f"{profile.major or ''} {' '.join(profile.experiences)}".lower()
        if not any(keyword in major_text for keyword in ["전자", "공학", "전기", "컴퓨터", "소프트웨어", "ai", "개발"]):
            return False
        title_text = title.lower()
        has_major_word = any(keyword in title_text for keyword in ["전자", "공학", "전기", "ai", "스마트", "테크", "기술"])
        if not has_major_word:
            return False
        consumer_food_words = ["도시락", "식사", "반찬", "디저트", "음료", "카페", "베이커리", "lunch", "dessert"]
        service_words = ["수리", "진단", "자동화", "개발", "설치", "교육", "컨설팅", "튜터링"]
        is_food = any(keyword in title_text for keyword in consumer_food_words)
        is_actual_tech_service = any(keyword in title_text for keyword in service_words)
        business_type = self._normalize_business_type(item.get("business_type"), item)
        return is_food and business_type in {"food", "cafe", "popup"} and not is_actual_tech_service

    def _realism_penalty(self, profile: StartupProfile, candidate: dict[str, Any]) -> int:
        penalty = 0
        if self._looks_like_forced_major_blend(str(candidate.get("title") or ""), candidate, profile):
            penalty += 28
        title = str(candidate.get("title") or "").lower()
        reason = str(candidate.get("reason") or "").lower()
        text = f"{title} {reason}"
        if any(keyword in text for keyword in ["컨셉", "테마"]) and any(keyword in text for keyword in ["전자", "공학", "기술"]):
            penalty += 12
        if candidate.get("business_type") in {"food", "cafe", "popup"} and "식품" not in " ".join(candidate.get("risks", [])):
            penalty += 4
        return min(45, penalty)

    def _missing_inputs(self, profile: StartupProfile) -> list[str]:
        missing_inputs = []
        if not profile.region:
            missing_inputs.append("지역")
        if profile.budget_krw is None:
            missing_inputs.append("초기 자금")
        if not profile.experiences and "experiences" not in profile.confirmed_absent_fields:
            missing_inputs.append("경험")
        if not profile.interests and not profile.preferred_business_types:
            missing_inputs.append("관심 분야")
        if not profile.preferred_channels:
            missing_inputs.append("판매/홍보 채널")
        return missing_inputs

    def _profile_terms(self, profile: StartupProfile) -> set[str]:
        raw = [
            profile.major or "",
            *profile.experiences,
            *profile.interests,
            *profile.preferred_channels,
            *profile.preferred_business_types,
            *profile.owned_assets,
            *profile.customer_network,
        ]
        terms = self._terms(raw)
        return self._expand_profile_terms(terms)

    def _expand_profile_terms(self, terms: set[str]) -> set[str]:
        expanded = set(terms)
        synonyms = {
            "디자인": ["브랜딩"],
            "카페": ["푸드"],
            "식당": ["푸드"],
            "한식당": ["푸드", "한식"],
            "cafe": ["푸드", "카페"],
            "food": ["푸드"],
            "popup": ["팝업", "오프라인"],
            "아르바이트": ["오프라인"],
            "알바": ["오프라인"],
            "sns": ["콘텐츠"],
            "전자공학": ["기술"],
            "공학": ["기술"],
        }
        for term, mapped_values in synonyms.items():
            if term in expanded:
                expanded.update(mapped_values)
        return expanded

    def _candidate_terms(self, candidate: dict[str, Any]) -> set[str]:
        raw = [
            candidate.get("title", ""),
            candidate.get("business_type", ""),
            candidate.get("target_customer", ""),
            candidate.get("reason", ""),
            candidate.get("validation_method", ""),
            *candidate.get("keywords", []),
            *candidate.get("channels", []),
            *candidate.get("why_fit", []),
        ]
        return self._terms(raw)

    def _terms(self, values: list[str]) -> set[str]:
        text = " ".join(str(value) for value in values).lower().replace(",", " ")
        tokens = {term.strip() for term in re.split(r"\s+|/|·|\||-", text) if term.strip()}
        for keyword in [
            "푸드",
            "한식",
            "식당",
            "카페",
            "요식업",
            "sns",
            "콘텐츠",
            "전자공학",
            "기술",
            "로컬",
            "오프라인",
            "온라인",
            "서비스",
            "팝업",
            "예약판매",
            "food",
            "cafe",
            "popup",
            "지원사업",
        ]:
            if keyword.lower() in text:
                tokens.add(keyword.lower())
        return tokens

    def _budget_fit(self, budget: int, estimated_cost: int) -> int:
        if estimated_cost <= budget:
            return 95
        over_ratio = estimated_cost / max(budget, 1)
        if over_ratio <= 1.25:
            return 70
        if over_ratio <= 1.6:
            return 45
        return 20

    def _business_type_fit(self, profile: StartupProfile, candidate: dict[str, Any]) -> int:
        desired = {str(item).lower() for item in [*profile.interests, *profile.preferred_business_types]}
        candidate_type = str(candidate.get("business_type", "")).lower()
        wants_food = bool({"푸드", "카페", "요식업", "외식업", "cafe", "food"} & desired)
        if wants_food and candidate_type in {"food", "cafe", "popup"}:
            return 90
        if candidate_type in desired:
            return 88
        if wants_food and candidate_type == "service":
            return 62
        return 50

    def _risk_fit(self, risk_tolerance: str, fixed_cost_level: str) -> int:
        table = {
            "low": {"low": 95, "medium": 65, "high": 30},
            "medium": {"low": 85, "medium": 80, "high": 55},
            "high": {"low": 75, "medium": 85, "high": 85},
        }
        return table.get(risk_tolerance, table["medium"]).get(fixed_cost_level, 60)

    def _local_opportunity(self, profile: StartupProfile, candidate: dict[str, Any]) -> int:
        score = 62
        terms = self._candidate_terms(candidate)
        if profile.region:
            score += 12
        if {"로컬", "오프라인", "상권"} & terms:
            score += 10
        if "오프라인" in candidate.get("channels", []) and "오프라인" in profile.preferred_channels:
            score += 8
        return min(100, score)

    def _execution_fit(self, difficulty: str) -> int:
        return {"낮음": 88, "중간": 72, "높음": 54}.get(difficulty, 68)

    def _time_fit(self, hours: int | None, candidate: dict[str, Any]) -> int:
        if hours is None:
            return 58
        difficulty = candidate.get("difficulty")
        fixed_cost = candidate.get("fixed_cost_level")
        if hours >= 30:
            return 90
        if hours >= 10:
            return 78 if difficulty != "높음" else 62
        score = 60 if fixed_cost == "low" else 45
        return max(20, score)

    def _testability_score(self, candidate: dict[str, Any]) -> int:
        score = 55
        if len(candidate.get("first_30_days", [])) >= 3:
            score += 20
        if candidate.get("validation_method"):
            score += 15
        if candidate.get("fixed_cost_level") == "low":
            score += 8
        return min(100, score)

    def _policy_fit(self, profile: StartupProfile, candidate: dict[str, Any]) -> int:
        score = 55
        terms = self._candidate_terms(candidate)
        if profile.startup_stage == "예비창업":
            score += 10
        if {"로컬", "콘텐츠", "창업", "기술", "소상공인"} & terms:
            score += 15
        return min(100, score)

    def _why_recommended(
        self,
        candidate: dict[str, Any],
        keyword_overlap: list[str],
        channel_overlap: list[str],
        budget_fit: int,
    ) -> list[str]:
        reasons = [candidate["reason"]]
        reasons.extend(candidate.get("why_fit", [])[:2])
        if keyword_overlap:
            reasons.append("프로필 키워드 일치: " + ", ".join(keyword_overlap[:5]))
        if channel_overlap:
            reasons.append("선호 채널 일치: " + ", ".join(channel_overlap))
        if budget_fit >= 90:
            reasons.append("현재 예산 안에서 30일 테스트가 가능합니다.")
        return self._ordered_unique(reasons)

    def _parse_json_object(self, raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end < start:
                return {}
            parsed = json.loads(text[start : end + 1])
        return parsed if isinstance(parsed, dict) else {}

    def _to_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        return [str(value).strip()]

    def _ordered_unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            item = str(value).strip()
            key = item.lower()
            if item and key not in seen:
                seen.add(key)
                result.append(item)
        return result

    def _coerce_money(self, value: Any) -> int | None:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        text = str(value).replace(",", "").strip()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)?", text)
        if not match:
            return None
        amount = float(match.group(1))
        unit = match.group(2)
        if unit == "억":
            return int(amount * 100_000_000)
        if unit == "천만":
            return int(amount * 10_000_000)
        if unit == "백만":
            return int(amount * 1_000_000)
        if unit in {"만원", "만"}:
            return int(amount * 10_000)
        return int(amount)

    def _normalize_business_type(self, value: Any, item: dict[str, Any]) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"cafe", "commerce", "content", "popup", "service", "food", "other"}:
            return raw
        text = json.dumps(item, ensure_ascii=False).lower()
        if any(keyword in text for keyword in ["식당", "요식", "푸드", "반찬", "음식", "한식"]):
            return "food"
        if any(keyword in text for keyword in ["팝업", "공유주방"]):
            return "popup"
        if any(keyword in text for keyword in ["sns", "콘텐츠", "릴스"]):
            return "content"
        if any(keyword in text for keyword in ["판매", "커머스", "스마트스토어"]):
            return "commerce"
        if any(keyword in text for keyword in ["서비스", "대행", "컨설팅"]):
            return "service"
        return "other"

    def _normalize_channels(self, value: Any, profile: StartupProfile) -> list[str]:
        channels = self._ordered_unique(self._to_list(value))
        if channels:
            return channels
        if profile.preferred_channels:
            return profile.preferred_channels
        return ["SNS", "오프라인"]

    def _normalize_fixed_cost(self, value: Any, estimated_cost: int | None) -> str:
        raw = str(value or "").strip().lower()
        mapping = {
            "low": "low",
            "낮음": "low",
            "medium": "medium",
            "중간": "medium",
            "high": "high",
            "높음": "high",
        }
        if raw in mapping:
            return mapping[raw]
        if estimated_cost is not None:
            if estimated_cost <= 2_000_000:
                return "low"
            if estimated_cost <= 7_000_000:
                return "medium"
        return "high"

    def _normalize_difficulty(self, value: Any) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"낮음", "easy", "low"}:
            return "낮음"
        if raw in {"높음", "hard", "high"}:
            return "높음"
        return "중간"

    def _normalize_first_30_days(self, value: Any, title: str) -> list[str]:
        steps = self._to_list(value)
        if len(steps) >= 3:
            return steps[:6]
        return [
            f"{title}의 고객 가설 1개 정의",
            "예상 고객 5명 인터뷰",
            "예약/문의/구매 의사로 1차 검증",
        ]

    def _normalize_risks(self, value: Any) -> list[str]:
        risks = self._to_list(value)
        if risks:
            return risks[:5]
        return ["초기 고객 반응이 약할 수 있습니다.", "실제 비용과 운영 난이도 검증이 필요합니다."]

    def _keywords_from_candidate(self, item: dict[str, Any]) -> list[str]:
        text = json.dumps(item, ensure_ascii=False).lower()
        keywords = []
        rules = [
            ("푸드", ["푸드", "음식", "식당", "요식", "한식", "반찬"]),
            ("기술", ["전자", "공학", "기술", "스마트", "자동화"]),
            ("SNS", ["sns", "인스타", "릴스", "콘텐츠"]),
            ("로컬", ["로컬", "지역", "상권", "소상공인"]),
            ("오프라인", ["오프라인", "매장", "팝업", "공유주방"]),
            ("온라인", ["온라인", "스마트스토어", "커머스"]),
            ("서비스", ["서비스", "대행", "컨설팅", "점검"]),
        ]
        for keyword, needles in rules:
            if any(needle in text for needle in needles):
                keywords.append(keyword)
        return keywords

    def _default_target_customer(self, profile: StartupProfile) -> str:
        if profile.region:
            return f"{profile.region} 지역 초기 고객"
        return "초기 검증 가능한 고객군"

    def _default_cost_estimate(self, profile: StartupProfile, item: dict[str, Any]) -> int:
        budget = profile.budget_krw or 3_000_000
        raw_fixed = str(item.get("fixed_cost_level") or "").lower()
        ratio = 0.2 if raw_fixed in {"low", "낮음"} else 0.35
        return max(500_000, min(8_000_000, int(budget * ratio)))
