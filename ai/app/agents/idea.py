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

        selected = candidates[: request.count]
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
            warnings.append("idea_llm_generation_failed_fallback_used")

        fallback_candidates = self._fallback_candidates(profile, count)
        generation = {
            "generated_by": "rule_fallback",
            "fallback_used": True,
            "llm_enabled": self.llm.is_enabled,
            "requested_count": count,
            "candidate_count": len(fallback_candidates),
        }
        if llm_diagnostics:
            generation["llm_diagnostics"] = llm_diagnostics
        return (fallback_candidates, generation, warnings)

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
                diagnostics["warnings"].append("idea_llm_generation_missing_ideas_array")
                return [], diagnostics

            candidates = self._sanitize_candidates(ideas, profile, source="llm")[:count]
            diagnostics["parsed_idea_count"] = len(ideas)
            diagnostics["sanitized_candidate_count"] = len(candidates)
            if not candidates:
                diagnostics["failure_reason"] = "no_valid_candidates_after_sanitize"
                diagnostics["warnings"].append("idea_llm_generation_no_valid_candidates")
            return candidates, diagnostics
        except Exception as error:
            diagnostics["failure_reason"] = "exception"
            diagnostics["error_type"] = error.__class__.__name__
            diagnostics["error_message"] = self._debug_preview(str(error), limit=1000)
            diagnostics["warnings"].append(f"idea_llm_generation_error:{error.__class__.__name__}")
            return [], diagnostics

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
            if not candidate["keywords"]:
                candidate["keywords"] = self._keywords_from_candidate(candidate)
            candidates.append(candidate)
        return candidates

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
        result.update(
            {
                "match_score": max(0, min(100, weighted_score)),
                "score_breakdown": score_breakdown,
                "matched_keywords": keyword_overlap,
                "matched_channels": channel_overlap,
                "why_recommended": self._why_recommended(candidate, keyword_overlap, channel_overlap, budget_fit),
                "risk": " / ".join(candidate["risks"]),
            }
        )
        return result

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
