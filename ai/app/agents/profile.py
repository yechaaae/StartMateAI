from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.schemas import AgentResponse, ProfileRequest, StartupProfile


class ProfileAgent(BaseAgent):
    name = "ProfileAgent"

    def build_effective_profile(self, profile: StartupProfile, question: str | None = None) -> StartupProfile:
        return self._merge_profile(profile, self._extract_profile_patch(question or ""))

    async def build_effective_profile_async(self, profile: StartupProfile, question: str | None = None) -> StartupProfile:
        patch = await self._extract_profile_patch_hybrid(question or "", profile)
        return self._merge_profile(profile, patch)

    async def run(self, request: ProfileRequest) -> AgentResponse:
        if request.use_llm_extraction:
            inferred_patch = await self._extract_profile_patch_hybrid(request.question or "", request.profile)
        else:
            inferred_patch = self._extract_profile_patch(request.question or "")
        public_inferred_patch = self._public_patch(inferred_patch)
        effective_profile = self._merge_profile(request.profile, inferred_patch)
        analysis = self._analyze_profile(effective_profile)
        missing_inputs = self._missing_inputs(effective_profile)
        clarifying_questions = self._clarifying_questions(effective_profile, missing_inputs)
        requested_explanations = self._requested_explanations(request.question or "")
        readiness_scores = self._readiness_scores(effective_profile, missing_inputs, analysis)
        score = int(readiness_scores["overall"])
        needs_clarification = bool(clarifying_questions)
        recommendation = self._recommendation(analysis["recommended_first_step"], requested_explanations)
        confirmed_items = self._confirmed_items(effective_profile)

        data = self.agent_data(
            position=self._position(effective_profile, analysis, clarifying_questions, requested_explanations),
            evidence={
                "strengths": analysis["strengths"],
                "constraints": analysis["constraints"],
                "readiness_scores": readiness_scores,
                "inferred_profile_patch": public_inferred_patch,
            },
            score=score,
            risks=analysis["constraints"],
            assumptions=self._assumptions(public_inferred_patch),
            missing_inputs=missing_inputs,
            recommendation=recommendation,
            payload={
                **analysis,
                "needs_clarification": needs_clarification,
                "clarifying_questions": clarifying_questions,
                "requested_explanations": requested_explanations,
                "confirmed_items": confirmed_items,
                "answer_request": self._answer_request(clarifying_questions, requested_explanations),
                "readiness_scores": readiness_scores,
                "input_profile": request.profile.model_dump(),
                "inferred_profile_patch": public_inferred_patch,
                "effective_profile": effective_profile.model_dump(),
                "startup_stage": effective_profile.startup_stage,
                "profile_summary": self._profile_summary(effective_profile, analysis),
            },
        )
        fallback = self._fallback_summary(
            effective_profile,
            analysis,
            needs_clarification,
            clarifying_questions,
            requested_explanations,
        )
        summary = await self.polish_summary(
            task="profile analysis",
            data=data,
            fallback=fallback,
            instructions=(
                "ProfileAgent 요약 규칙:\n"
                "- 분석 보고서처럼 쓰지 말고 채팅에서 사용자가 바로 답할 수 있게 작성하세요.\n"
                "- 1문장은 확인된 정보를 짧게 말하세요.\n"
                "- 추가 정보가 필요하면 2문장 안에 질문 1~3개를 직접 물어보세요.\n"
                "- '성향으로 보입니다' 같은 평가 문장보다 '아래만 더 알려주세요' 형식을 우선하세요.\n"
                "- 사용자가 용어를 모르겠다고 하면 뜻과 예시를 먼저 설명하세요."
            ),
        )
        explanation_actions = [item["follow_up"] for item in requested_explanations]
        explained_fields = {item["field"] for item in requested_explanations}
        follow_up_questions = [
            question["question"] for question in clarifying_questions if question["field"] not in explained_fields
        ]

        return AgentResponse(
            intent="profile",
            agent=self.name,
            summary=summary,
            data=data,
            next_actions=[
                *explanation_actions,
                *follow_up_questions[:2],
                "초기 자금 기준으로 아이템 추천 실행",
                "거주 지역 기준 지원사업 매칭 실행",
            ],
        )

    def _extract_profile_patch(self, text: str) -> dict[str, Any]:
        if not text:
            return {}

        normalized = text.lower()
        patch: dict[str, Any] = {}

        region = self._extract_region(text)
        if region:
            patch["region"] = region

        budget = self._extract_money(text, keywords=["예산", "자금", "돈", "비용", "소자본"])
        if budget:
            patch["budget_krw"] = budget

        target_income = self._extract_money(text, keywords=["월수익", "수익", "매출", "목표"], require_keyword=True)
        if target_income:
            patch["target_income_krw"] = target_income

        hours = self._extract_hours(text)
        if hours is not None:
            patch["available_hours_per_week"] = hours

        major = self._extract_major(text)
        if major:
            patch["major"] = major

        if self._has_no_experience(text):
            patch["experiences"] = []
            patch["confirmed_absent_fields"] = ["experiences"]
            patch["_clear_fields"] = ["experiences"]
        elif not self._asks_about_field_meaning(text, ["보유경험", "관련 경험", "경험"]):
            experiences = self._extract_experiences(text)
            if experiences:
                patch["experiences"] = experiences

        interests = self._extract_interests(text)
        if interests:
            patch["interests"] = interests

        preferred_channels = (
            []
            if self._asks_about_field_meaning(text, ["선호 판매 채널", "판매 채널", "홍보 채널", "채널"])
            else self._extract_channels(text)
        )
        if preferred_channels:
            patch["preferred_channels"] = preferred_channels

        business_types = self._extract_business_types(text)
        if business_types:
            patch["preferred_business_types"] = business_types

        owned_assets = self._extract_assets(text)
        if owned_assets:
            patch["owned_assets"] = owned_assets

        customer_network = self._extract_customer_network(text)
        if customer_network:
            patch["customer_network"] = customer_network

        if any(keyword in normalized for keyword in ["혼자", "1인", "원맨"]):
            patch["has_team"] = False
        elif any(keyword in normalized for keyword in ["팀", "동료", "친구랑", "파트너", "공동창업"]):
            patch["has_team"] = True

        if any(keyword in normalized for keyword in ["운영중", "운영 중", "이미 창업", "사업자"]):
            patch["startup_stage"] = "운영중"
        elif any(keyword in normalized for keyword in ["초기창업", "창업한 지", "오픈한 지"]):
            patch["startup_stage"] = "초기창업"
        elif any(keyword in normalized for keyword in ["예비창업", "창업 준비", "시작하려고", "준비중"]):
            patch["startup_stage"] = "예비창업"

        if any(keyword in normalized for keyword in ["안전", "저위험", "리스크 낮", "보수적"]):
            patch["risk_tolerance"] = "low"
        elif any(keyword in normalized for keyword in ["공격적", "고위험", "리스크 감수", "크게"]):
            patch["risk_tolerance"] = "high"

        return patch

    async def _extract_profile_patch_hybrid(self, text: str, profile: StartupProfile) -> dict[str, Any]:
        rule_patch = self._extract_profile_patch(text)
        llm_patch = await self._extract_profile_patch_with_llm(text, profile)
        return self._merge_extraction_patches(llm_patch, rule_patch)

    async def _extract_profile_patch_with_llm(self, text: str, profile: StartupProfile) -> dict[str, Any]:
        if not text or not self.llm.is_enabled:
            return {}

        prompt = (
            "사용자 발화에서 창업 상담용 프로필 정보를 추출하세요.\n"
            "반드시 JSON object 하나만 출력하세요. Markdown, 설명문, 주석은 출력하지 마세요.\n\n"
            "규칙:\n"
            "- 사용자가 명시했거나 강하게 의미한 정보만 추출하세요.\n"
            "- 추측하지 마세요. 모르는 값은 null 또는 빈 배열로 두세요.\n"
            "- '없다', '없습니다', '해본 적 없다' 같은 부정 표현은 confirmed_absent_fields에 넣으세요.\n"
            "- 사용자가 이전 정보를 정정하면 최신 발화를 우선하세요.\n"
            "- 예산은 원 단위 정수 budget_krw로 변환하세요.\n"
            "- 시간은 주당 시간 available_hours_per_week로 변환하세요. 전업/풀타임/모든 시간은 40으로 해석하세요.\n"
            "- 경험이 없다는 문장을 경험으로 만들지 마세요.\n"
            "- 포트폴리오가 없다고 했으면 디자인 경험을 만들지 마세요.\n"
            "- 출력 필드는 아래 schema에 있는 키만 사용하세요.\n\n"
            "schema:\n"
            "{\n"
            '  "age": number|null,\n'
            '  "major": string|null,\n'
            '  "experiences": string[],\n'
            '  "confirmed_absent_fields": string[],\n'
            '  "region": string|null,\n'
            '  "budget_krw": number|null,\n'
            '  "available_hours_per_week": number|null,\n'
            '  "target_income_krw": number|null,\n'
            '  "has_team": boolean|null,\n'
            '  "owned_assets": string[],\n'
            '  "customer_network": string[],\n'
            '  "interests": string[],\n'
            '  "preferred_channels": string[],\n'
            '  "preferred_business_types": string[],\n'
            '  "avoid_business_types": string[],\n'
            '  "startup_stage": string|null,\n'
            '  "risk_tolerance": "low"|"medium"|"high"|null\n'
            "}\n\n"
            f"current_profile: {json.dumps(profile.model_dump(), ensure_ascii=False)}\n"
            f"user_utterance: {text}"
        )
        try:
            raw = await self.llm.complete(
                system_prompt="You are a strict JSON profile extraction engine for Korean startup counseling.",
                user_prompt=prompt,
                temperature=0,
                fallback="{}",
            )
            parsed = self._parse_json_object(raw)
            return self._sanitize_llm_patch(parsed)
        except Exception:
            return {}

    def _merge_extraction_patches(self, llm_patch: dict[str, Any], rule_patch: dict[str, Any]) -> dict[str, Any]:
        merged: dict[str, Any] = dict(llm_patch)
        list_fields = {
            "experiences",
            "owned_assets",
            "customer_network",
            "confirmed_absent_fields",
            "interests",
            "preferred_channels",
            "preferred_business_types",
            "avoid_business_types",
            "_clear_fields",
        }

        for key, value in rule_patch.items():
            if key in list_fields:
                if key == "_clear_fields":
                    merged[key] = self._ordered_unique([*(merged.get(key) or []), *(value or [])])
                elif key in (merged.get("_clear_fields") or []):
                    merged[key] = []
                else:
                    merged[key] = self._ordered_unique([*(merged.get(key) or []), *(value or [])])
            elif value is not None:
                merged[key] = value

        for field in merged.get("_clear_fields", []):
            if field in list_fields:
                merged[field] = []
        return merged

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

    def _sanitize_llm_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        scalar_fields = {
            "age",
            "major",
            "region",
            "budget_krw",
            "available_hours_per_week",
            "target_income_krw",
            "has_team",
            "startup_stage",
            "risk_tolerance",
            "memo",
        }
        list_fields = {
            "experiences",
            "owned_assets",
            "customer_network",
            "confirmed_absent_fields",
            "interests",
            "preferred_channels",
            "preferred_business_types",
            "avoid_business_types",
        }

        for field in scalar_fields:
            value = patch.get(field)
            if value in {None, ""}:
                continue
            if field in {"age", "budget_krw", "available_hours_per_week", "target_income_krw"}:
                number = self._coerce_int(value)
                if number is not None:
                    sanitized[field] = number
            elif field == "has_team":
                if isinstance(value, bool):
                    sanitized[field] = value
            elif field == "risk_tolerance":
                if value in {"low", "medium", "high"}:
                    sanitized[field] = value
            else:
                sanitized[field] = str(value).strip()

        for field in list_fields:
            values = patch.get(field)
            if isinstance(values, list):
                sanitized[field] = self._ordered_unique([str(item).strip() for item in values if str(item).strip()])

        absent_fields = set(sanitized.get("confirmed_absent_fields", []))
        clear_fields = []
        if "experiences" in absent_fields:
            sanitized["experiences"] = []
            clear_fields.append("experiences")
        if clear_fields:
            sanitized["_clear_fields"] = clear_fields
        return sanitized

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            digits = re.sub(r"[^\d.]", "", value)
            if not digits:
                return None
            try:
                return int(float(digits))
            except ValueError:
                return None
        return None

    def _merge_profile(self, profile: StartupProfile, patch: dict[str, Any]) -> StartupProfile:
        data = profile.model_dump()
        scalar_fields = [
            "age",
            "major",
            "region",
            "budget_krw",
            "available_hours_per_week",
            "target_income_krw",
            "has_team",
            "startup_stage",
            "risk_tolerance",
            "memo",
        ]
        list_fields = [
            "experiences",
            "owned_assets",
            "customer_network",
            "confirmed_absent_fields",
            "interests",
            "preferred_channels",
            "preferred_business_types",
            "avoid_business_types",
        ]
        for field in patch.get("_clear_fields", []):
            if field in list_fields:
                data[field] = []

        for field in scalar_fields:
            value = patch.get(field)
            if value is None:
                continue
            data[field] = value

        for field in list_fields:
            values = patch.get(field, [])
            if values:
                data[field] = self._ordered_unique([*data.get(field, []), *values])
                if field == "experiences":
                    data[field] = self._dedupe_experiences(data[field])
                    data["confirmed_absent_fields"] = [
                        item for item in data.get("confirmed_absent_fields", []) if item != "experiences"
                    ]

        return StartupProfile.model_validate(data)

    def _analyze_profile(self, profile: StartupProfile) -> dict[str, object]:
        strengths: list[str] = []
        constraints: list[str] = []
        tags = self._ordered_unique(
            profile.interests
            + profile.preferred_channels
            + profile.preferred_business_types
            + profile.owned_assets
            + profile.customer_network
        )
        capability_tags = self._capability_tags(profile)
        budget_band = self._budget_band(profile.budget_krw)

        if profile.major:
            strengths.append(f"{profile.major} 기반 역량")
        if profile.experiences:
            strengths.append("경험: " + ", ".join(profile.experiences[:3]))
        if profile.region:
            strengths.append(f"{profile.region} 지역 기반 실행 가능성")
        if profile.available_hours_per_week is not None:
            if profile.available_hours_per_week >= 15:
                strengths.append(f"주 {profile.available_hours_per_week}시간 투입 가능")
            elif profile.available_hours_per_week < 7:
                constraints.append("주당 투입 시간이 낮아 자동화/소규모 검증 위주로 시작 필요")
        if profile.owned_assets:
            strengths.append("보유 자산: " + ", ".join(profile.owned_assets[:3]))
        if profile.customer_network:
            strengths.append("초기 고객 접점: " + ", ".join(profile.customer_network[:3]))
        if profile.has_team is True:
            strengths.append("팀/파트너 기반 실행 가능")
        elif profile.has_team is False:
            constraints.append("1인 실행 기준으로 업무 범위를 작게 잡아야 함")
        if "experiences" in profile.confirmed_absent_fields:
            constraints.append("관련 경험/포트폴리오가 없어 초기에는 샘플 제작과 작은 검증이 필요함")

        if profile.budget_krw is not None:
            if profile.budget_krw <= 3_000_000:
                constraints.append("초기 자금이 낮아 재고/임대 부담이 작은 모델 우선")
            else:
                strengths.append(f"초기 자금 {profile.budget_krw:,}원 활용 가능")
        if profile.target_income_krw and profile.budget_krw:
            if profile.target_income_krw >= profile.budget_krw:
                constraints.append("목표 수익이 초기 예산 대비 높아 단계적 검증 계획 필요")
        if profile.risk_tolerance == "low":
            constraints.append("낮은 리스크 선호: 테스트형/위탁형 모델 우선")
        elif profile.risk_tolerance == "high":
            strengths.append("높은 리스크 감수 성향: 확장형 실험도 검토 가능")
        if "offline" not in capability_tags and "online_content" not in capability_tags and not profile.customer_network:
            constraints.append("검증 가능한 고객 접점 정보가 부족함")

        user_type = self._user_type(capability_tags, budget_band, profile.risk_tolerance)
        return {
            "user_type": user_type,
            "budget_band": budget_band,
            "strengths": strengths or ["입력 정보가 부족해 기본 예비창업자 프로필로 분석"],
            "constraints": constraints,
            "tags": tags,
            "capability_tags": capability_tags,
            "next_questions": [question["question"] for question in self._clarifying_questions(profile, self._missing_inputs(profile))],
            "recommended_first_step": self._recommended_first_step(profile, constraints),
            "agent_hints": self._agent_hints(profile, capability_tags, budget_band),
        }

    def _capability_tags(self, profile: StartupProfile) -> list[str]:
        text = " ".join(
            [
                profile.major or "",
                *profile.experiences,
                *profile.interests,
                *profile.preferred_channels,
                *profile.preferred_business_types,
                *profile.owned_assets,
                *profile.customer_network,
            ]
        ).lower()
        tags: list[str] = []
        rules = [
            ("engineering", ["전자공학", "기계공학", "컴퓨터공학", "공학", "하드웨어", "회로", "iot"]),
            ("design", ["디자인", "브랜딩", "로고", "굿즈", "시각"]),
            ("fnb", ["카페", "푸드", "음식", "외식", "요식업", "외식업", "식당", "쿠키", "팝업", "디저트"]),
            ("online_content", ["sns", "콘텐츠", "릴스", "영상", "마케팅", "홍보", "인스타"]),
            ("offline", ["오프라인", "알바", "매장", "상권", "팝업", "플리마켓"]),
            ("local", ["로컬", "지역", "부산", "구미", "동네", "소상공인"]),
            ("commerce", ["커머스", "굿즈", "판매", "온라인", "쇼핑몰", "스마트스토어"]),
            ("networked", ["지인", "팔로워", "단골", "동아리", "학교", "커뮤니티"]),
        ]
        for tag, keywords in rules:
            if any(keyword in text for keyword in keywords):
                tags.append(tag)
        return tags

    def _readiness_scores(
        self,
        profile: StartupProfile,
        missing_inputs: list[str],
        analysis: dict[str, object],
    ) -> dict[str, int]:
        data_completeness = self._data_completeness_score(profile)
        execution_capacity = self._execution_capacity_score(profile)
        budget_safety = self._budget_safety_score(profile)
        market_access = self._market_access_score(profile)
        risk_fit = self._risk_fit_score(profile)
        profile_confidence = max(25, min(100, data_completeness - len(missing_inputs) * 3 + len(analysis["strengths"]) * 4))
        overall = int(
            data_completeness * 0.18
            + execution_capacity * 0.22
            + budget_safety * 0.18
            + market_access * 0.18
            + risk_fit * 0.14
            + profile_confidence * 0.10
        )
        return {
            "overall": max(0, min(100, overall)),
            "data_completeness": data_completeness,
            "execution_capacity": execution_capacity,
            "budget_safety": budget_safety,
            "market_access": market_access,
            "risk_fit": risk_fit,
            "profile_confidence": profile_confidence,
        }

    def _clarifying_questions(
        self,
        profile: StartupProfile,
        missing_inputs: list[str],
    ) -> list[dict[str, object]]:
        candidates = [
            (
                "region",
                "창업을 먼저 테스트할 지역은 어디인가요?",
                "정책/RAG 매칭과 로컬 상권 판단에 필요합니다.",
                ["부산", "서울", "구미"],
            ),
            (
                "budget_krw",
                "초기 예산은 어느 정도까지 사용할 수 있나요?",
                "아이템 규모와 손익분기점 계산에 필요합니다.",
                ["100만원 이하", "300만원", "1000만원 이상"],
            ),
            (
                "available_hours_per_week",
                "주당 몇 시간을 창업 준비와 운영에 쓸 수 있나요?",
                "1인 실행 가능 범위와 운영 리스크 판단에 필요합니다.",
                ["5시간 이하", "10시간", "20시간 이상"],
            ),
            (
                "interests",
                "관심 있는 창업 분야는 무엇인가요?",
                "아이템 후보를 좁히는 데 필요합니다.",
                ["카페/디저트", "콘텐츠/SNS", "굿즈/커머스"],
            ),
            (
                "preferred_channels",
                "오프라인, SNS, 온라인 판매 중 어떤 채널이 편한가요?",
                "홍보/판매 전략과 초기 검증 방식을 정하는 데 필요합니다.",
                ["SNS", "오프라인", "온라인 판매"],
            ),
            (
                "experiences",
                "바로 활용 가능한 경험이나 포트폴리오가 있나요?",
                "아이템 적합도와 지원사업 서류 준비도를 판단합니다.",
                ["아르바이트", "콘텐츠 제작", "프로젝트 경험"],
            ),
        ]

        missing_field_map = {
            "창업 희망 지역": "region",
            "초기 자금": "budget_krw",
            "주당 투입 가능 시간": "available_hours_per_week",
            "관심 분야": "interests",
            "선호 판매/홍보 채널": "preferred_channels",
            "관련 경험": "experiences",
        }
        missing_fields = {missing_field_map[item] for item in missing_inputs if item in missing_field_map}
        questions = []
        for priority, (field, question, reason, options) in enumerate(candidates, start=1):
            if field in missing_fields:
                questions.append(
                    {
                        "field": field,
                        "question": question,
                        "reason": reason,
                        "priority": priority,
                        "options": options,
                    }
                )
        return questions[:3]

    def _profile_summary(self, profile: StartupProfile, analysis: dict[str, object]) -> dict[str, Any]:
        return {
            "age": profile.age,
            "region": profile.region,
            "budget_krw": profile.budget_krw,
            "available_hours_per_week": profile.available_hours_per_week,
            "target_income_krw": profile.target_income_krw,
            "risk_tolerance": profile.risk_tolerance,
            "startup_stage": profile.startup_stage,
            "has_team": profile.has_team,
            "tags": analysis["tags"],
            "capability_tags": analysis["capability_tags"],
            "user_type": analysis["user_type"],
            "budget_band": analysis["budget_band"],
            "owned_assets": profile.owned_assets,
            "customer_network": profile.customer_network,
            "preferred_business_types": profile.preferred_business_types,
            "confirmed_absent_fields": profile.confirmed_absent_fields,
        }

    def _agent_hints(
        self,
        profile: StartupProfile,
        capability_tags: list[str],
        budget_band: str,
    ) -> dict[str, dict[str, object]]:
        return {
            "idea": {
                "priority": "소자본/저위험/30일 검증 가능 아이템 우선",
                "capability_tags": capability_tags,
                "budget_band": budget_band,
                "preferred_business_types": profile.preferred_business_types,
                "avoid_fixed_cost": budget_band == "micro" or profile.risk_tolerance == "low",
            },
            "policy": {
                "region": profile.region,
                "startup_stage": profile.startup_stage,
                "keywords": self._ordered_unique([*profile.interests, *capability_tags]),
                "needs_budget_support": profile.budget_krw is not None and profile.budget_krw <= 3_000_000,
            },
            "finance": {
                "budget_krw": profile.budget_krw,
                "target_income_krw": profile.target_income_krw,
                "risk_tolerance": profile.risk_tolerance,
                "available_hours_per_week": profile.available_hours_per_week,
                "prefer_low_fixed_cost": budget_band == "micro",
            },
            "marketing": {
                "channels": profile.preferred_channels,
                "customer_network": profile.customer_network,
                "tone": "실행 가능성과 신뢰 중심" if profile.risk_tolerance == "low" else "성장 가능성 중심",
            },
        }

    def _position(
        self,
        profile: StartupProfile,
        analysis: dict[str, object],
        clarifying_questions: list[dict[str, object]],
        requested_explanations: list[dict[str, object]],
    ) -> str:
        confirmed = self._confirmed_items(profile)
        questions = self._answer_request(clarifying_questions, requested_explanations)
        confirmed_text = ", ".join(confirmed[:4]) if confirmed else "기본 예비창업자 정보"
        if questions:
            return f"확인된 정보: {confirmed_text}. 다음으로 {questions[0]}"
        return f"확인된 정보: {confirmed_text}. 현재 정보만으로 {analysis['user_type']} 기준 1차 추천을 진행할 수 있습니다."

    def _fallback_summary(
        self,
        profile: StartupProfile,
        analysis: dict[str, object],
        needs_clarification: bool,
        clarifying_questions: list[dict[str, object]],
        requested_explanations: list[dict[str, object]],
    ) -> str:
        confirmed = self._confirmed_items(profile)
        confirmed_text = ", ".join(confirmed[:5]) if confirmed else "기본 정보"
        questions = self._answer_request(clarifying_questions, requested_explanations)
        if requested_explanations:
            explanation = "; ".join(
                f"{item['label']}은 {self._trim_sentence_end(str(item['meaning']))}(예: {', '.join(item['examples'][:3])})"
                for item in requested_explanations[:2]
            )
            next_question = " / ".join(questions[:2]) if questions else "해당되는 항목만 골라서 알려주세요."
            return f"{explanation}. 지금은 {next_question}"
        if needs_clarification and questions:
            return f"{confirmed_text}까지 확인했습니다. 추천을 정확히 하려면 {', '.join(questions[:3])}"
        return f"{analysis['user_type']} 프로필로 분석했습니다. 아이템 추천과 지원사업 매칭을 이어서 실행할 수 있습니다."

    def _confirmed_items(self, profile: StartupProfile) -> list[str]:
        items = []
        if profile.region:
            items.append(f"지역 {profile.region}")
        if profile.budget_krw is not None:
            items.append(f"예산 {profile.budget_krw:,}원")
        if profile.major:
            items.append(f"전공 {profile.major}")
        if profile.available_hours_per_week is not None:
            items.append(f"주 {profile.available_hours_per_week}시간")
        if profile.interests:
            items.append("관심 분야 " + ", ".join(profile.interests[:3]))
        if profile.preferred_channels:
            items.append("채널 " + ", ".join(profile.preferred_channels[:3]))
        if profile.experiences:
            items.append("경험 " + ", ".join(profile.experiences[:3]))
        elif "experiences" in profile.confirmed_absent_fields:
            items.append("관련 경험 없음")
        if profile.has_team is False:
            items.append("1인 창업")
        elif profile.has_team is True:
            items.append("팀 창업")
        return items

    def _answer_request(
        self,
        clarifying_questions: list[dict[str, object]],
        requested_explanations: list[dict[str, object]],
    ) -> list[str]:
        explained_fields = {item["field"] for item in requested_explanations}
        explanation_questions = [str(item["follow_up"]) for item in requested_explanations]
        profile_questions = [
            str(question["question"]) for question in clarifying_questions if question["field"] not in explained_fields
        ]
        return [*explanation_questions, *profile_questions]

    def _recommendation(self, default_recommendation: object, requested_explanations: list[dict[str, object]]) -> str:
        if requested_explanations:
            return "헷갈린 항목은 예시를 보고 선택하면 됩니다. 모르는 항목은 비워두고 아이템 추천을 먼저 진행해도 됩니다."
        return str(default_recommendation)

    def _requested_explanations(self, text: str) -> list[dict[str, object]]:
        explanations: list[dict[str, object]] = []
        if self._asks_about_field_meaning(text, ["선호 판매 채널", "판매 채널", "홍보 채널", "채널"]):
            explanations.append(
                {
                    "field": "preferred_channels",
                    "label": "선호 판매/홍보 채널",
                    "meaning": "어디에서 고객을 만나고 팔거나 홍보할지가 편한지를 뜻합니다.",
                    "examples": ["오프라인 매장/팝업", "SNS", "온라인몰/스마트스토어", "배달앱"],
                    "follow_up": "판매/홍보 채널은 오프라인, SNS, 온라인몰, 배달앱 중 어디가 가장 편한가요?",
                }
            )
        if self._asks_about_field_meaning(text, ["보유경험", "관련 경험", "경험"]):
            explanations.append(
                {
                    "field": "experiences",
                    "label": "보유 경험",
                    "meaning": "창업에 바로 써먹을 수 있는 과거 경험이나 포트폴리오를 뜻합니다.",
                    "examples": ["아르바이트", "전공 프로젝트", "동아리/팀 프로젝트", "판매/마케팅 경험", "자격증"],
                    "follow_up": "보유 경험은 아르바이트, 전공 프로젝트, 판매 경험, 자격증 중 해당되는 것이 있나요?",
                }
            )
        return explanations

    def _trim_sentence_end(self, text: str) -> str:
        return text.rstrip().rstrip(".。.!！?？")

    def _public_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in patch.items() if not key.startswith("_")}

    def _has_no_experience(self, text: str) -> bool:
        normalized = text.lower().replace(" ", "")
        has_experience_term = any(term in normalized for term in ["경험", "포트폴리오", "활용가능"])
        has_negation = any(
            marker in normalized
            for marker in [
                "없",
                "없습니다",
                "없어요",
                "없어",
                "없네요",
                "해본적없",
                "해본적은없",
            ]
        )
        return has_experience_term and has_negation

    def _recommended_first_step(self, profile: StartupProfile, constraints: list[str]) -> str:
        if not profile.region or profile.budget_krw is None:
            return "지역과 초기 예산을 먼저 확정한 뒤 아이템 추천과 지원사업 매칭을 실행하세요."
        if profile.available_hours_per_week is None:
            return "주당 투입 가능 시간을 확인한 뒤 30일 검증 계획을 잡으세요."
        if constraints:
            return "고정비가 낮은 30일 검증형 아이템을 먼저 추천받고, 지원사업 매칭으로 비용 부담을 낮추세요."
        return "아이템 추천, 지원사업 매칭, 비용 검증을 바로 병렬 실행하세요."

    def _assumptions(self, inferred_patch: dict[str, Any]) -> list[str]:
        assumptions = ["입력되지 않은 항목은 예비창업자 기본값으로 해석했습니다."]
        if inferred_patch:
            assumptions.append("사용자 질문 문장에서 일부 프로필 값을 규칙 기반으로 추출했습니다.")
        return assumptions

    def _missing_inputs(self, profile: StartupProfile) -> list[str]:
        missing = []
        if not profile.major and not profile.owned_assets:
            missing.append("전공/핵심 역량")
        if not profile.experiences and "experiences" not in profile.confirmed_absent_fields:
            missing.append("관련 경험")
        if not profile.region:
            missing.append("창업 희망 지역")
        if profile.budget_krw is None:
            missing.append("초기 자금")
        if profile.available_hours_per_week is None:
            missing.append("주당 투입 가능 시간")
        if not profile.interests and not profile.preferred_business_types:
            missing.append("관심 분야")
        if not profile.preferred_channels:
            missing.append("선호 판매/홍보 채널")
        return missing

    def _data_completeness_score(self, profile: StartupProfile) -> int:
        checks = [
            bool(profile.major or profile.owned_assets),
            bool(profile.experiences or "experiences" in profile.confirmed_absent_fields),
            bool(profile.region),
            profile.budget_krw is not None,
            profile.available_hours_per_week is not None,
            bool(profile.interests or profile.preferred_business_types),
            bool(profile.preferred_channels),
            profile.has_team is not None,
            bool(profile.customer_network),
        ]
        return int(sum(checks) / len(checks) * 100)

    def _execution_capacity_score(self, profile: StartupProfile) -> int:
        score = 42
        if profile.experiences:
            score += min(24, len(profile.experiences) * 8)
        if profile.available_hours_per_week is not None:
            if profile.available_hours_per_week >= 20:
                score += 24
            elif profile.available_hours_per_week >= 10:
                score += 16
            elif profile.available_hours_per_week >= 5:
                score += 8
            else:
                score -= 8
        if profile.owned_assets:
            score += min(14, len(profile.owned_assets) * 5)
        if profile.has_team:
            score += 10
        return max(0, min(100, score))

    def _budget_safety_score(self, profile: StartupProfile) -> int:
        if profile.budget_krw is None:
            return 45
        if profile.budget_krw <= 1_000_000:
            score = 45
        elif profile.budget_krw <= 3_000_000:
            score = 64
        elif profile.budget_krw <= 10_000_000:
            score = 76
        else:
            score = 84
        if profile.risk_tolerance == "low" and profile.budget_krw <= 3_000_000:
            score += 8
        if profile.target_income_krw and profile.target_income_krw > max(profile.budget_krw * 2, 1):
            score -= 15
        return max(0, min(100, score))

    def _market_access_score(self, profile: StartupProfile) -> int:
        score = 35
        if profile.region:
            score += 16
        if profile.preferred_channels:
            score += min(22, len(profile.preferred_channels) * 9)
        if profile.customer_network:
            score += min(20, len(profile.customer_network) * 7)
        if profile.interests:
            score += min(14, len(profile.interests) * 5)
        return max(0, min(100, score))

    def _risk_fit_score(self, profile: StartupProfile) -> int:
        score = 65
        if profile.risk_tolerance == "low":
            score += 10
            if profile.budget_krw is not None and profile.budget_krw <= 3_000_000:
                score += 8
        elif profile.risk_tolerance == "high":
            score += 4
            if profile.budget_krw is not None and profile.budget_krw <= 3_000_000:
                score -= 10
        if profile.available_hours_per_week is not None and profile.available_hours_per_week < 7:
            score -= 10
        return max(0, min(100, score))

    def _budget_band(self, budget_krw: int | None) -> str:
        if budget_krw is None:
            return "unknown"
        if budget_krw <= 3_000_000:
            return "micro"
        if budget_krw <= 10_000_000:
            return "small"
        return "growth"

    def _user_type(self, capability_tags: list[str], budget_band: str, risk_tolerance: str) -> str:
        if "online_content" in capability_tags and "design" in capability_tags:
            base = "콘텐츠 실행형"
        elif "engineering" in capability_tags and "fnb" in capability_tags:
            base = "기술 접목 F&B 탐색형"
        elif "engineering" in capability_tags:
            base = "기술 기반 탐색형"
        elif "fnb" in capability_tags and "offline" in capability_tags:
            base = "오프라인 경험형"
        elif "fnb" in capability_tags:
            base = "F&B 테스트형"
        elif "commerce" in capability_tags:
            base = "커머스 테스트형"
        elif "networked" in capability_tags:
            base = "고객접점 활용형"
        else:
            base = "소자본 탐색형"

        if budget_band == "micro":
            return f"소자본 안정 {base}"
        if risk_tolerance == "low":
            return f"안정형 {base}"
        if budget_band == "growth":
            return f"확장 지향 {base}"
        return base

    def _extract_region(self, text: str) -> str | None:
        regions = [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "경기",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
            "구미",
        ]
        for region in regions:
            if region in text:
                return region
        return None

    def _extract_money(self, text: str, *, keywords: list[str], require_keyword: bool = False) -> int | None:
        keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
        if require_keyword:
            patterns = [
                rf"(?:{keyword_pattern})[^\d]{{0,12}}(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)",
                rf"(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)[^\n]{{0,12}}(?:{keyword_pattern})",
            ]
        else:
            patterns = [
                rf"(?:{keyword_pattern})?[^\d]{{0,8}}(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)",
                rf"(\d+(?:\.\d+)?)\s*(억|천만|백만|만원|만|원)[^\n]{{0,8}}(?:{keyword_pattern})",
            ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
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
                if unit == "원":
                    return int(amount)
        return None

    def _extract_hours(self, text: str) -> int | None:
        normalized = text.replace(" ", "")
        if any(keyword in normalized for keyword in ["모든시간", "전업으로", "풀타임", "하루종일"]):
            return 40
        patterns = [
            r"주\s*(?:당|에)?\s*(\d+)\s*시간",
            r"일주일에\s*(\d+)\s*시간",
            r"(\d+)\s*시간\s*(?:정도)?\s*(?:가능|투입|쓸 수)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None

    def _extract_major(self, text: str) -> str | None:
        rules = [
            ("전자공학", ["전자공학", "전자공학과", "전자과"]),
            ("컴퓨터공학", ["컴퓨터공학", "컴퓨터공학과", "컴공"]),
            ("기계공학", ["기계공학", "기계공학과"]),
            ("산업공학", ["산업공학", "산업공학과"]),
            ("디자인", ["디자인", "디자인과"]),
            ("경영", ["경영", "경영학", "경영학과"]),
            ("마케팅", ["마케팅"]),
            ("식품", ["식품", "식품영양", "식품공학"]),
            ("조리", ["조리", "조리학"]),
            ("영상", ["영상", "영상학"]),
            ("미디어", ["미디어", "미디어학"]),
        ]
        for major, keywords in rules:
            if any(keyword in text for keyword in keywords):
                return major
        return None

    def _extract_experiences(self, text: str) -> list[str]:
        if self._has_no_experience(text):
            return []
        rules = [
            ("카페 알바", ["카페 알바", "카페에서", "카페 경험"]),
            (
                "식당 아르바이트",
                [
                    "식당 알바",
                    "식당 아르바이트",
                    "식당에서",
                    "한식당",
                    "음식점 알바",
                    "음식점 아르바이트",
                    "요식업 알바",
                    "요식업 아르바이트",
                    "서빙 알바",
                    "주방 알바",
                ],
            ),
            ("아르바이트 경험", ["알바 경험", "아르바이트 경험", "알바한 경험", "아르바이트한 경험"]),
            ("SNS 콘텐츠 제작", ["sns 콘텐츠", "릴스", "인스타", "콘텐츠 제작", "영상 제작"]),
            ("디자인 프로젝트", ["디자인 프로젝트", "로고 제작", "브랜딩 프로젝트", "포트폴리오"]),
            ("판매 경험", ["판매 경험", "판매해본", "판매해 봄", "스마트스토어 운영", "플리마켓 운영", "장사 경험"]),
            ("마케팅 경험", ["마케팅 경험", "홍보 경험", "광고 운영", "광고 집행"]),
        ]
        return self._dedupe_experiences(self._extract_by_rules(text, rules))

    def _dedupe_experiences(self, experiences: list[str]) -> list[str]:
        result = self._ordered_unique(experiences)
        if "아르바이트 경험" in result and any(item.endswith("아르바이트") for item in result):
            result = [item for item in result if item != "아르바이트 경험"]
        if any("한식당" in item for item in result) and "식당 아르바이트" in result:
            result = [item for item in result if item != "식당 아르바이트"]
        return result

    def _extract_interests(self, text: str) -> list[str]:
        rules = [
            ("브랜딩", ["브랜딩", "브랜드", "로고"]),
            ("카페", ["카페", "디저트", "커피"]),
            ("로컬", ["로컬", "지역", "동네", "소상공인"]),
            ("콘텐츠", ["콘텐츠", "릴스", "영상", "sns"]),
            ("굿즈", ["굿즈", "소품"]),
            ("커머스", ["커머스", "온라인 판매", "스마트스토어"]),
            ("푸드", ["푸드", "음식", "외식", "요식업", "외식업", "식당", "레스토랑", "쿠키"]),
        ]
        return self._extract_by_rules(text, rules)

    def _extract_channels(self, text: str) -> list[str]:
        rules = [
            ("SNS", ["sns", "인스타", "릴스", "틱톡", "유튜브"]),
            ("오프라인", ["오프라인", "매장", "상권", "팝업", "플리마켓"]),
            ("온라인 판매", ["온라인 판매", "스마트스토어", "커머스", "쇼핑몰"]),
            ("배달", ["배달", "배민", "요기요"]),
        ]
        return self._extract_by_rules(text, rules)

    def _extract_business_types(self, text: str) -> list[str]:
        rules = [
            ("cafe", ["카페", "디저트", "커피", "쿠키", "요식업", "외식업", "식당", "음식"]),
            ("content", ["콘텐츠", "sns", "릴스", "영상", "브랜딩"]),
            ("commerce", ["커머스", "굿즈", "온라인 판매", "스마트스토어"]),
            ("popup", ["팝업", "플리마켓", "행사"]),
            ("service", ["컨설팅", "서비스", "대행"]),
        ]
        return self._extract_by_rules(text, rules)

    def _extract_assets(self, text: str) -> list[str]:
        rules = [
            ("노트북", ["노트북", "pc", "컴퓨터"]),
            ("카메라", ["카메라", "촬영 장비"]),
            ("디자인 툴", ["포토샵", "일러스트", "피그마", "디자인 툴"]),
            ("작업 공간", ["작업 공간", "공간", "사무실", "스튜디오"]),
            ("SNS 계정", ["팔로워", "인스타 계정", "sns 계정"]),
        ]
        return self._extract_by_rules(text, rules)

    def _extract_customer_network(self, text: str) -> list[str]:
        rules = [
            ("지인", ["지인", "친구", "주변 사람"]),
            ("SNS 팔로워", ["팔로워", "인스타", "sns 계정"]),
            ("학교/동아리", ["학교", "동아리", "캠퍼스", "대학생"]),
            ("단골/매장 고객", ["단골", "고객", "매장 손님"]),
            ("지역 커뮤니티", ["지역 커뮤니티", "동네", "소상공인"]),
        ]
        return self._extract_by_rules(text, rules)

    def _asks_about_field_meaning(self, text: str, field_terms: list[str]) -> bool:
        normalized = text.lower().replace(" ", "")
        asks_meaning = any(marker in normalized for marker in ["무슨말", "뭔말", "모르겠", "뜻이", "의미가"])
        if not asks_meaning:
            return False
        return any(term.lower().replace(" ", "") in normalized for term in field_terms)

    def _extract_by_rules(self, text: str, rules: list[tuple[str, list[str]]]) -> list[str]:
        normalized = text.lower()
        result = []
        for value, keywords in rules:
            if any(keyword.lower() in normalized for keyword in keywords):
                result.append(value)
        return self._ordered_unique(result)

    def _ordered_unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            item = value.strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result
