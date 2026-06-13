from __future__ import annotations

import re
from typing import Any

from app.agents.base import BaseAgent
from app.core.backend_tools import BackendToolClient
from app.rag.retriever import SupportProgramRetriever
from app.schemas import AgentResponse, PolicyRequest, Source


class PolicyAgent(BaseAgent):
    name = "PolicyAgent"

    def __init__(self, llm, retriever: SupportProgramRetriever, backend_tools: BackendToolClient | None = None):
        super().__init__(llm)
        self.retriever = retriever
        self.backend_tools = backend_tools

    async def run(self, request: PolicyRequest) -> AgentResponse:
        reference_matches = self._reference_matches(request)
        tool_calls: list[dict[str, Any]] = []
        tool_warnings: list[str] = []
        tool_matches: list[dict[str, Any]] = []
        should_refresh = self._should_refresh(request)

        if self.backend_tools and (should_refresh or not reference_matches):
            tool_matches, tool_calls, tool_warnings = await self._fetch_backend_tool_matches(request)

        retrieval_matches = self.retriever.search(
            profile=request.profile,
            query=request.query or "",
            limit=request.limit,
        )
        matches = self._merge_matches(
            primary=tool_matches or reference_matches,
            secondary=retrieval_matches,
            limit=request.limit,
        )
        matches = self._rerank_for_query(matches, request)
        matches = matches[: request.limit]
        using_reference_data = bool(tool_matches or reference_matches or retrieval_matches)
        reference_sources = []
        if tool_matches:
            reference_sources.append("backend.tool.support_programs")
        elif reference_matches:
            reference_sources.append("backend.support_programs")
        if retrieval_matches:
            reference_sources.append(getattr(self.retriever, "retrieval_mode", "rag"))

        top = matches[0] if matches else None
        documents = self._documents_to_prepare(matches)
        match_summary = self._match_summary(matches)
        checklist = [
            "사업자 등록 여부 확인",
            "나이/지역/창업단계 자격 확인",
            "사업계획서와 개인정보 동의서 준비",
            "마감일 기준 3일 전 제출 목표 설정",
        ]
        risks = list(tool_warnings)
        if not using_reference_data:
            risks.append("지원사업 원천 데이터가 없어 실제 공고 후보를 생성하지 않았습니다.")
        if top and top.get("eligibility_gaps"):
            risks.extend(top["eligibility_gaps"][:2])
        missing_inputs = []
        if not request.profile.region:
            missing_inputs.append("지역")
        if not request.profile.startup_stage:
            missing_inputs.append("창업 단계")
        if not request.profile.interests:
            missing_inputs.append("관심 분야")

        position = (
            f"지원사업은 {top['title']}을 1순위로 검토하는 것이 좋습니다."
            if top
            else "현재 조건만으로는 확실한 지원사업 후보를 좁히기 어렵습니다."
        )
        recommendation = (
            f"{top['title']} 기준으로 자격 공백을 확인하고 사업계획서 초안을 준비하세요."
            if top
            else "지역, 단계, 관심 분야를 보강한 뒤 최신 공고 RAG로 다시 매칭하세요."
        )
        data = self.agent_data(
            position=position,
            evidence=self._policy_evidence(top),
            score=int(top.get("eligibility_score", 0)) if top else 0,
            risks=risks,
            assumptions=[
                self._data_source_assumption(tool_matches, reference_matches, retrieval_matches),
                "마감일과 자격 요건은 실제 공고에서 재확인해야 합니다.",
            ],
            missing_inputs=missing_inputs,
            recommendation=recommendation,
            payload={
                "matches": matches,
                "checklist": checklist,
                "top_policy": top,
                "match_summary": match_summary,
                "documents_to_prepare": documents,
                "application_strategy": top.get("application_strategy", []) if top else [],
                "reference_data_used": using_reference_data,
                "reference_sources": reference_sources,
                "tool_calls": tool_calls,
                "coverage": {
                    "total_matches": len(matches),
                    "high_fit_count": sum(1 for item in matches if item.get("fit_level") == "high"),
                    "medium_or_better_count": sum(
                        1 for item in matches if item.get("fit_level") in {"high", "medium"}
                    ),
                },
            },
        )
        fallback = f"사용자 조건에 맞는 지원사업 후보 {len(matches)}개를 찾았습니다."
        summary = self._detailed_summary(matches, request)

        sources = [
            Source(title=item.get("title") or "지원사업 후보", url=item.get("url"), note=item.get("source_note"))
            for item in matches
        ]
        warnings = risks

        return AgentResponse(
            intent="policy",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                "상위 공고의 모집 기간, 신청 대상, 지역 조건을 실제 공고에서 확인",
                "사업계획서에 30일 검증 계획과 예산 사용처 작성",
                "필수 서류와 마감일을 체크리스트로 정리",
            ],
            sources=sources,
            warnings=warnings,
        )

    def _reference_matches(self, request: PolicyRequest) -> list[dict]:
        support_programs = (
            request.context.get("reference", {})
            .get("externalData", {})
            .get("supportPrograms", {})
        )
        items = support_programs.get("items", [])
        if not isinstance(items, list) or not items:
            return []
        return [self._reference_item_to_match(item) for item in items[: request.limit] if isinstance(item, dict)]

    def _reference_item_to_match(self, item: dict) -> dict:
        return self._backend_item_to_match(item, source_note=item.get("source") or "backend.support_programs")

    def _backend_item_to_match(self, item: dict, *, source_note: str) -> dict:
        score = int(item.get("matchScore") or 0)
        caution_reasons = item.get("cautionReasons") or []
        match_reasons = item.get("matchReasons") or []
        return {
            "id": item.get("programId"),
            "title": item.get("title") or "지원사업 후보",
            "url": item.get("applyUrl"),
            "summary": item.get("summary"),
            "region_condition": item.get("regionCondition") or item.get("region_condition"),
            "support_amount": item.get("supportAmount") or item.get("support_amount"),
            "required_documents": self._document_list(item.get("requiredDocuments") or item.get("required_documents")),
            "organization": item.get("organization"),
            "support_type": item.get("supportType") or item.get("support_type"),
            "status": item.get("status"),
            "application_end_date": item.get("applicationEndDate") or item.get("application_end_date"),
            "source_note": source_note,
            "eligibility_score": score,
            "fit_level": self._fit_level(score),
            "score_breakdown": {"backend_match_score": score},
            "matched_keywords": [],
            "why_matched": match_reasons,
            "eligibility_gaps": caution_reasons,
            "application_strategy": [
                "백엔드 추천 점수와 주의사항을 기준으로 실제 공고 원문을 확인하세요.",
                "마감일과 신청 URL을 먼저 확인한 뒤 제출 서류를 정리하세요.",
            ],
            "retrieval": {"source": "backend_reference"},
            "source_chunks": [item.get("summary")] if item.get("summary") else [],
        }

    def _data_source_assumption(
        self,
        tool_matches: list[dict[str, Any]],
        reference_matches: list[dict[str, Any]],
        retrieval_matches: list[dict[str, Any]],
    ) -> str:
        if tool_matches:
            return "백엔드 지원사업 도구 추천 결과를 우선 사용했습니다."
        if reference_matches:
            return "백엔드 정규화 추천 결과를 우선 사용했습니다."
        if retrieval_matches:
            return "지원사업 RAG 인덱스 검색 결과를 사용했습니다."
        return "지원사업 원천 데이터가 없어 후보를 만들지 않았습니다."

    def _document_list(self, raw: Any) -> list[str]:
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        if not raw:
            return []
        return [item.strip() for item in re.split(r"[,/|]", str(raw)) if item.strip()]

    def _merge_matches(self, *, primary: list[dict], secondary: list[dict], limit: int) -> list[dict]:
        merged: dict[str, dict] = {}
        for item in [*secondary, *primary]:
            key = str(item.get("id") or item.get("title") or len(merged))
            existing = merged.get(key)
            if existing is None:
                merged[key] = dict(item)
                continue
            merged[key] = self._merge_match(existing, item)
        results = list(merged.values())
        results.sort(key=lambda item: int(item.get("eligibility_score") or 0), reverse=True)
        return results

    def _rerank_for_query(self, matches: list[dict], request: PolicyRequest) -> list[dict]:
        region_terms = self._region_terms(request)

        reranked = []
        for item in matches:
            adjusted = dict(item)
            base_score = int(adjusted.get("eligibility_score") or 0)
            score_breakdown = adjusted.get("score_breakdown") or {}
            haystack = self._match_text(adjusted)
            location_score = self._location_score(haystack, region_terms)
            domain_adjustment = self._domain_adjustment(haystack, request)

            if "backend_match_score" in score_breakdown:
                adjusted_score = max(0, min(100, base_score + domain_adjustment))
                adjusted["eligibility_score"] = adjusted_score
                adjusted["fit_level"] = self._fit_level(int(adjusted_score))
                adjusted["score_breakdown"] = {
                    **score_breakdown,
                    "location_fit": location_score,
                    "domain_adjustment": domain_adjustment,
                }
                adjusted["why_matched"] = self._unique([
                    *(adjusted.get("why_matched") or []),
                    self._location_reason(location_score, region_terms),
                    self._domain_reason(domain_adjustment),
                ])
                reranked.append(adjusted)
                continue

            final_score = base_score + location_score + domain_adjustment

            if location_score <= 0 and self._has_other_specific_region(haystack, region_terms):
                final_score = min(final_score, 45)
            elif location_score <= 0:
                final_score = min(final_score, 65)
            elif location_score == 25:
                final_score = min(final_score, 90)
            elif location_score < 20:
                final_score = min(final_score, 75)

            adjusted["eligibility_score"] = max(0, min(100, final_score))
            adjusted["fit_level"] = self._fit_level(int(adjusted["eligibility_score"]))
            adjusted["score_breakdown"] = {
                **score_breakdown,
                "location_fit": location_score,
                "domain_adjustment": domain_adjustment,
            }
            adjusted["why_matched"] = self._unique([
                *(adjusted.get("why_matched") or []),
                self._location_reason(location_score, region_terms),
                self._domain_reason(domain_adjustment),
            ])
            reranked.append(adjusted)

        reranked.sort(
            key=lambda item: (
                int(item.get("eligibility_score") or 0),
                int((item.get("score_breakdown") or {}).get("location_fit") or 0),
                float((item.get("score_breakdown") or {}).get("semantic_similarity") or 0),
            ),
            reverse=True,
        )
        return reranked[: request.limit]

    def _domain_adjustment(self, haystack: str, request: PolicyRequest) -> int:
        query = f"{request.query or ''} {' '.join(request.profile.interests)} {' '.join(request.profile.preferred_business_types)}".lower()
        food_intent = any(keyword in query for keyword in ["카페", "디저트", "메뉴", "도시락", "식품", "요식", "음식", "f&b", "food"])
        content_intent = any(keyword in query for keyword in ["sns", "콘텐츠", "마케팅", "홍보", "브랜딩"])
        tech_intent = any(keyword in query for keyword in ["전자", "공학", "ai", "로봇", "소프트웨어", "앱", "기술"])
        text = haystack.lower()
        tech_program = any(keyword in text for keyword in ["로봇", "공간컴퓨팅", "항공우주", "ict", "ai", "sw", "소프트웨어", "디바이스"])
        food_program = any(keyword in text for keyword in ["식품", "외식", "푸드", "카페", "로컬", "소상공인", "전통시장"])
        content_program = any(keyword in text for keyword in ["콘텐츠", "마케팅", "브랜딩", "홍보", "크리에이터"])

        if food_intent and tech_program and not food_program:
            return -28
        if content_intent and tech_program and not content_program:
            return -18
        if tech_intent and tech_program:
            return 12
        if food_intent and food_program:
            return 12
        if content_intent and content_program:
            return 12
        return 0

    def _domain_reason(self, adjustment: int) -> str:
        if adjustment <= -20:
            return "추천 아이템 도메인과 공고 분야가 달라 보조 후보로 낮췄습니다."
        if adjustment < 0:
            return "아이템-공고 분야 적합도가 높지 않아 점수를 보수적으로 조정했습니다."
        if adjustment > 0:
            return "아이템/프로필 분야와 공고 분야가 일부 일치합니다."
        return "아이템-공고 분야 적합도는 중립으로 보았습니다."

    def _detailed_summary(self, matches: list[dict], request: PolicyRequest) -> str:
        if not matches:
            return (
                "현재 조건으로는 추천할 지원사업 공고를 찾지 못했습니다. "
                "지역, 창업 단계, 업종, 필요한 지원 유형을 알려주면 다시 검색하겠습니다."
            )

        top = matches[0]
        title = top.get("title") or "지원사업 후보"
        score = top.get("eligibility_score")
        details = self._program_details(top)
        reasons = self._clean_reasons(top.get("why_matched") or [])
        reason_text = "; ".join(reasons[:2]) if reasons else "질문과 공고 내용의 유사도 및 자격 조건을 기준으로 선정했습니다"
        next_step = self._next_step_for_policy(top, request)
        writing_guide = self._writing_guide(top, request)
        alternatives = [item.get("title") for item in matches[1:3] if item.get("title")]
        alternative_text = f" 함께 비교할 후보는 {', '.join(alternatives)}입니다." if alternatives else ""

        lines = [
            f"1순위: {title}{f' (적합도 {score}점)' if score is not None else ''}",
            "",
            "선정 근거",
            f"- {reason_text}",
            "",
            "공고 핵심 내용",
            details,
            "",
            "작성방법",
            writing_guide,
            "",
            "다음 행동",
            f"- {next_step}",
        ]
        if alternative_text:
            lines.extend(["", alternative_text.strip()])
        return "\n".join(lines)

    def _program_details(self, item: dict) -> str:
        parts = []
        for label, key in [
            ("주관", "organization"),
            ("지원유형", "support_type"),
            ("지원금", "support_amount"),
            ("대상", "summary"),
            ("지역조건", "region_condition"),
            ("창업단계", "business_stage_condition"),
            ("마감", "application_end_date"),
        ]:
            value = item.get(key)
            if value:
                parts.append(f"- {label}: {self._plain_text(value)}")
        if parts:
            return "\n".join(parts)
        chunks = item.get("source_chunks") or []
        if chunks:
            return "\n".join(f"- 원문 요약: {self._plain_text(chunk)}" for chunk in chunks[:3] if chunk)
        return "상세 조건은 공고 원문 확인이 필요합니다"

    def _plain_text(self, value: Any) -> str:
        text = str(value or "")
        text = re.sub(r"<[^>]+>", " ", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        return re.sub(r"\s+", " ", text).strip()

    def _next_step_for_policy(self, item: dict, request: PolicyRequest) -> str:
        documents = item.get("required_documents") or []
        doc_text = f" 필요 서류({', '.join(documents[:3])})를 준비하고" if documents else ""
        region = request.profile.region or self._first_region_term(request.query or "")
        region_text = f" {region} 조건이 실제 공고 대상에 포함되는지 확인한 뒤" if region else " 지역/대상 조건을 확인한 뒤"
        return f"공고 URL에서 모집 기간과{region_text}{doc_text} 사업계획서 초안을 작성하세요"

    def _writing_guide(self, item: dict, request: PolicyRequest) -> str:
        title = item.get("title") or "해당 공고"
        region = request.profile.region or self._first_region_term(request.query or "")
        support_amount = item.get("support_amount")
        support_type = item.get("support_type")
        stage = item.get("business_stage_condition")
        guide = [
            f"사업계획서 첫 문단에 '{title}'의 지원 대상과 내 조건이 맞는 이유를 적으세요",
            "문제-해결책-고객-검증계획-예산사용처 순서로 작성하세요",
            "30일 안에 확인할 지표를 매출, 고객 수, 재구매 또는 문의 수처럼 숫자로 쓰세요",
        ]
        if region:
            guide.append(f"{region} 소재/이전/활동 계획을 증빙 가능한 방식으로 넣으세요")
        if support_amount:
            guide.append(f"지원금({support_amount})은 항목별 사용처로 쪼개 쓰세요")
        elif support_type:
            guide.append(f"지원유형({support_type})에 맞춰 필요한 멘토링, 공간, 마케팅, 자금 항목을 분리하세요")
        if stage:
            guide.append(f"창업단계 조건({stage})에 맞춰 현재 상태와 다음 마일스톤을 연결하세요")
        return "\n".join(f"- {item}" for item in guide)

    def _clean_reasons(self, reasons: list[Any]) -> list[str]:
        cleaned = []
        for reason in reasons:
            text = str(reason).strip()
            if not text:
                continue
            if "諛" in text or "吏" in text or "?" in text:
                continue
            cleaned.append(text.rstrip(".。"))
        return cleaned

    def _region_terms(self, request: PolicyRequest) -> list[str]:
        joined = " ".join([request.profile.region or "", request.query or ""])
        terms = []
        stopwords = {"지원사업", "알려줘", "추천해줘", "창업", "예비창업", "사업"}
        for match in re.findall(r"[가-힣]{2,}(?:시|군|구|도)?", joined):
            if match in stopwords:
                continue
            if match.endswith(("시", "군", "구", "도")) or match in {"구미", "서울", "부산", "대구", "경기", "경북", "경상북도"}:
                terms.append(match)
                if match.endswith("시"):
                    terms.append(match[:-1])
        return self._unique(terms)

    def _first_region_term(self, text: str) -> str:
        for match in re.findall(r"[가-힣]{2,}(?:시|군|구|도)?", text):
            if match.endswith(("시", "군", "구", "도")) or match in {"구미", "서울", "부산", "대구", "경기", "경북", "경상북도"}:
                return match
        return ""

    def _match_text(self, item: dict) -> str:
        chunks = " ".join(str(chunk) for chunk in item.get("source_chunks") or [])
        return " ".join(
            str(item.get(key) or "")
            for key in [
                "title",
                "summary",
                "region_condition",
                "organization",
                "source_note",
                "support_type",
                "business_stage_condition",
                "industry_condition",
            ]
        ) + " " + chunks

    def _location_score(self, haystack: str, region_terms: list[str]) -> int:
        if not region_terms:
            return 0
        if any(term and term in haystack for term in region_terms):
            return 40
        if any(term in region_terms for term in ["구미", "구미시"]) and any(term in haystack for term in ["경북", "경상북도"]):
            return 25
        if "전국" in haystack:
            return 10
        return -20

    def _location_reason(self, location_score: int, region_terms: list[str]) -> str:
        if not region_terms:
            return "지역 정보가 없어 지역 적합도는 중립으로 보았습니다."
        region = region_terms[0] if region_terms else "요청 지역"
        if location_score >= 40:
            return f"공고명 또는 조건에 {region} 지역 관련 표현이 직접 포함되어 있습니다."
        if location_score >= 25:
            return f"{region}와 같은 광역권 조건이 공고와 맞을 가능성이 있습니다."
        if location_score >= 10:
            return "전국 대상 공고라 지역 제한 리스크가 낮습니다."
        return f"{region} 직접 대상 공고가 아니어서 우선순위를 낮췄습니다."

    def _has_other_specific_region(self, haystack: str, region_terms: list[str]) -> bool:
        known_regions = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
        return any(region in haystack for region in known_regions if region not in region_terms)

    def _merge_match(self, left: dict, right: dict) -> dict:
        merged = dict(left)
        left_score = int(left.get("eligibility_score") or 0)
        right_score = int(right.get("eligibility_score") or 0)
        if right_score >= left_score:
            merged.update({key: value for key, value in right.items() if value not in (None, "", [])})
        merged["eligibility_score"] = max(left_score, right_score)
        merged["fit_level"] = self._fit_level(int(merged["eligibility_score"]))
        merged["score_breakdown"] = {
            **(left.get("score_breakdown") or {}),
            **(right.get("score_breakdown") or {}),
        }
        merged["why_matched"] = self._unique([*(left.get("why_matched") or []), *(right.get("why_matched") or [])])
        merged["eligibility_gaps"] = self._unique([
            *(left.get("eligibility_gaps") or []),
            *(right.get("eligibility_gaps") or []),
        ])
        merged["source_chunks"] = self._unique([*(left.get("source_chunks") or []), *(right.get("source_chunks") or [])])
        merged["retrieval"] = {
            "sources": self._unique([
                str((left.get("retrieval") or {}).get("source") or ""),
                str((right.get("retrieval") or {}).get("source") or ""),
            ]),
            "semantic_similarity": max(
                float((left.get("retrieval") or {}).get("semantic_similarity") or 0),
                float((right.get("retrieval") or {}).get("semantic_similarity") or 0),
            ),
        }
        return merged

    async def _fetch_backend_tool_matches(
        self,
        request: PolicyRequest,
    ) -> tuple[list[dict], list[dict[str, Any]], list[str]]:
        if not self.backend_tools:
            return [], [], []

        tool_calls: list[dict[str, Any]] = []
        warnings: list[str] = []
        try:
            if self._should_refresh(request):
                await self.backend_tools.sync_support_programs("all")
                tool_calls.append({"name": "support_programs.sync", "status": "success"})

            items = await self.backend_tools.recommend_support_programs(self._recommend_payload(request))
            tool_calls.append({"name": "support_programs.recommend", "status": "success", "count": len(items)})
            matches = [
                self._backend_item_to_match(item, source_note="backend.tool.support_programs")
                for item in items[: request.limit]
                if isinstance(item, dict)
            ]
            return matches, tool_calls, warnings
        except Exception as error:  # noqa: BLE001
            tool_calls.append({
                "name": "support_programs.tool",
                "status": "failed",
                "error": error.__class__.__name__,
            })
            warnings.append(f"백엔드 지원사업 도구 호출 실패: {str(error)[:160]}")
            return [], tool_calls, warnings

    def _recommend_payload(self, request: PolicyRequest) -> dict[str, Any]:
        query = request.query or ""
        region = request.profile.region or query
        industry_text = " ".join([*request.profile.interests, query])
        return {
            "age": request.profile.age or self._age_from(query),
            "residenceSido": self._sido_from(request.profile.region),
            "desiredSido": self._sido_from(region),
            "desiredSigungu": self._sigungu_from(region),
            "founderType": "pre_founder",
            "businessRegistered": False,
            "businessStartDate": None,
            "businessStage": self._business_stage(request.profile.startup_stage),
            "industryLarge": self._industry_large(industry_text),
            "industryMedium": self._industry_medium(industry_text),
            "industrySmall": self._industry_small(industry_text),
            "requiredFundingAmount": request.profile.budget_krw,
            "interestedSupportTypes": ["grant", "education", "mentoring", "space"],
        }

    def _should_refresh(self, request: PolicyRequest) -> bool:
        text = (request.query or "").lower()
        return any(keyword in text for keyword in ["최신", "새 공고", "새로운", "지금", "현재", "모집중", "모집 중"])

    def _business_stage(self, value: str | None) -> str:
        text = value or ""
        if "초기" in text:
            return "mvp"
        if "매출" in text:
            return "revenue"
        return "idea"

    def _industry_large(self, raw: str) -> str | None:
        return "음식점업" if self._contains_any(raw, ["카페", "커피", "음식", "식당", "디저트"]) else None

    def _industry_medium(self, raw: str) -> str | None:
        return "커피점/카페" if self._contains_any(raw, ["카페", "커피"]) else None

    def _industry_small(self, raw: str) -> str | None:
        return "카페" if self._contains_any(raw, ["카페", "커피"]) else None

    def _sido_from(self, raw: str | None) -> str | None:
        text = raw or ""
        for sido in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]:
            if sido in text:
                return sido
        return None

    def _sigungu_from(self, raw: str | None) -> str | None:
        text = raw or ""
        if "마포" in text:
            return "마포구"
        for token in text.replace(",", " ").split():
            if token.endswith(("구", "군")):
                return token
        return None

    def _age_from(self, raw: str) -> int | None:
        for token in raw.replace(",", " ").split():
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                age = int(digits)
                if 19 <= age <= 80:
                    return age
        return None

    def _contains_any(self, raw: str, keywords: list[str]) -> bool:
        return any(keyword in raw for keyword in keywords)

    def _unique(self, values: list) -> list:
        seen = set()
        result = []
        for value in values:
            if value in (None, ""):
                continue
            key = str(value)
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    def _fit_level(self, score: int) -> str:
        if score >= 80:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    def _policy_evidence(self, top: dict | None) -> dict | str:
        if not top:
            return "매칭 후보 없음"
        return {
            "title": top.get("title"),
            "eligibility_score": top.get("eligibility_score"),
            "fit_level": top.get("fit_level"),
            "score_breakdown": top.get("score_breakdown", {}),
            "retrieval": top.get("retrieval", {}),
            "source_chunks": top.get("source_chunks", []),
            "why_matched": top.get("why_matched", []),
            "eligibility_gaps": top.get("eligibility_gaps", []),
        }

    def _match_summary(self, matches: list[dict]) -> list[dict[str, object]]:
        return [
            {
                "title": item.get("title"),
                "eligibility_score": item.get("eligibility_score"),
                "fit_level": item.get("fit_level"),
                "matched_keywords": item.get("matched_keywords", []),
                "semantic_similarity": item.get("retrieval", {}).get("semantic_similarity"),
                "why_matched": item.get("why_matched", []),
                "eligibility_gaps": item.get("eligibility_gaps", []),
            }
            for item in matches
        ]

    def _documents_to_prepare(self, matches: list[dict]) -> list[str]:
        documents: list[str] = []
        seen = set()
        for item in matches[:3]:
            for document in item.get("required_documents", item.get("documents", [])):
                if document not in seen:
                    seen.add(document)
                    documents.append(document)
        return documents

