from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas import AgentResponse, ChatRequest


FEATURE_REPORT_TEAMS: dict[str, list[str]] = {
    "ITEM": ["profile", "idea", "finance", "policy", "commercial_area"],
    "SIMULATOR": ["idea", "finance", "simulation"],
    "SUPPORT": ["profile", "idea", "policy", "finance"],
    "PLAN": ["profile", "idea", "policy", "plan", "finance", "commercial_area"],
    "OPERATION": ["operation", "finance", "marketing"],
    "SNS": ["marketing", "operation", "profile"],
}

FEATURE_REVIEW_FEATURES = {"ITEM", "SUPPORT", "PLAN"}

FEATURE_RESULT_TYPES: dict[str, str] = {
    "ITEM": "IDEA_REPORT",
    "SIMULATOR": "SIMULATION_REPORT",
    "SUPPORT": "SUPPORT_REPORT",
    "PLAN": "PLAN_REPORT",
    "OPERATION": "OPERATION_REPORT",
    "SNS": "SNS_REPORT",
}

FEATURE_IDS: dict[str, str] = {
    "ITEM": "item",
    "SIMULATOR": "simulator",
    "SUPPORT": "support",
    "PLAN": "plan",
    "OPERATION": "operation",
    "SNS": "sns",
}

FEATURE_REPORT_TYPES: dict[str, str] = {
    "ITEM": "idea_recommendation",
    "SIMULATOR": "simulation",
    "SUPPORT": "support_program",
    "PLAN": "business_plan",
    "OPERATION": "operation_feedback",
    "SNS": "sns_marketing",
}

FEATURE_CTA_LABELS: dict[str, str] = {
    "ITEM": "아이템 추천 리포트 보기",
    "SIMULATOR": "시뮬레이션 리포트 보기",
    "SUPPORT": "지원사업 리포트 보기",
    "PLAN": "사업계획 리포트 보기",
    "OPERATION": "운영 피드백 리포트 보기",
    "SNS": "SNS 마케팅 리포트 보기",
}

SUPPORT_MATCH_STOP_TERMS = {
    "사업",
    "사업화",
    "창업",
    "예비창업",
    "예비창업자",
    "지원",
    "지원사업",
    "정부",
    "정부지원",
    "공고",
    "모집",
    "기업",
    "대상",
    "참가",
    "선정",
    "프로그램",
    "자금",
    "지역",
    "기반",
    "관련",
    "조건",
    "사용자",
    "아이템",
    "서비스",
    "운영",
    "검토",
    "가능",
    "필요",
    "grant",
    "mentoring",
    "startup",
    "business",
    "program",
    "support",
}


def feature_key_from_request(request: ChatRequest) -> str:
    context = request.context or {}
    for value in (
        _nested(context, "featureContext", "featureKey"),
        _nested(context, "conversation", "targetFeature"),
        _nested(context, "rabbitmq", "targetFeature"),
        context.get("featureKey"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    return ""


def feature_key_for_result(
    *,
    request: ChatRequest,
    response: AgentResponse,
    results: dict[str, AgentResponse],
    explicit_override: str | None = None,
) -> str:
    # 오케스트레이터 게이트가 결정한 기능키를 우선 사용한다. ""면 페이지 기능을 강제하지 않고 내용 기반 추론으로.
    explicit = explicit_override if explicit_override is not None else feature_key_from_request(request)
    if explicit:
        return explicit

    intents = {key for key in results.keys() if key}
    response_intent = (response.intent or "").lower()

    if "idea" in intents and _is_idea_recommendation_request(request.message):
        return "ITEM"
    if response_intent in {"collaboration", "roadmap"} or len(intents) >= 4:
        return "PLAN"
    if "simulation" in intents or response_intent == "simulation":
        return "SIMULATOR"
    if "operation" in intents and ("finance" in intents or "marketing" in intents or len(intents) == 1):
        return "OPERATION"
    if "marketing" in intents and ("operation" in intents or "profile" in intents or len(intents) == 1):
        return "SNS"
    if "policy" in intents and ("profile" in intents or "finance" in intents or len(intents) == 1):
        return "SUPPORT"
    if "idea" in intents:
        return "ITEM"
    if response_intent in {"idea", "policy", "operation", "marketing", "finance"}:
        return {
            "idea": "ITEM",
            "policy": "SUPPORT",
            "operation": "OPERATION",
            "marketing": "SNS",
            "finance": "SIMULATOR",
        }.get(response_intent, "")
    return ""


def _is_idea_recommendation_request(message: str) -> bool:
    text = (message or "").lower()
    if any(keyword in text for keyword in ["사업계획", "사업 계획", "계획서", "business plan"]):
        return False
    if any(keyword in text for keyword in ["지원사업", "정부지원", "정부 지원", "공고", "보조금", "지원금"]):
        if not ("아니라" in text and any(item in text for item in ["아이템", "사업 아이템", "창업 아이템"])):
            return False
    return any(
        keyword in text
        for keyword in [
            "아이템 추천",
            "창업 아이템",
            "사업아이템",
            "사업 아이템",
            "뭐 창업",
            "무슨 창업",
            "추천해줘",
            "추천 해줘",
        ]
    )


def build_feature_result(
    *,
    request: ChatRequest,
    response: AgentResponse,
    results: dict[str, AgentResponse],
    agent_review: dict[str, Any] | None = None,
    feature_key_override: str | None = None,
) -> dict[str, Any] | None:
    feature_key = feature_key_for_result(
        request=request,
        response=response,
        results=results,
        explicit_override=feature_key_override,
    )
    if feature_key not in FEATURE_REPORT_TEAMS:
        return _custom_report_result(request, response)

    report_data = _report_data(feature_key, request, results)
    if not report_data:
        return None
    report_data = _with_agent_review(feature_key, report_data, results, agent_review)
    report_data = _with_cross_agent_conflicts(feature_key, report_data, results, agent_review)

    payload = {
        "reportType": FEATURE_REPORT_TYPES[feature_key],
        "featureId": FEATURE_IDS[feature_key],
        "reportData": report_data,
        "primaryReport": report_data,
        "chatCard": _chat_card(feature_key, response, report_data),
        "agentSummary": response.summary,
        "selectedAgents": [item.agent for item in results.values()],
        "agentResults": {intent: deepcopy(item.data) for intent, item in results.items()},
    }
    review = _dict(agent_review)
    if review and feature_key in FEATURE_REVIEW_FEATURES:
        payload["agentReview"] = report_data.get("agentReview")
        payload["agentDiscussion"] = _agent_discussion(review)
        warnings = _list(review.get("warnings"))
        if warnings:
            payload["warnings"] = warnings

    return {
        "targetFeature": feature_key,
        "resultType": FEATURE_RESULT_TYPES[feature_key],
        "resultTitle": _result_title(feature_key, report_data),
        "shouldCreateResult": True,
        "routeKey": f"{FEATURE_IDS[feature_key]}-report",
        "referenceId": _nested(request.context, "rabbitmq", "roomId"),
        "payload": payload,
    }


def _with_cross_agent_conflicts(
    feature_key: str,
    report_data: dict[str, Any],
    results: dict[str, AgentResponse],
    agent_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if feature_key != "ITEM":
        return report_data
    items = [item for item in _list(report_data.get("items")) if isinstance(item, dict)]
    if not items:
        return report_data

    adjustment = _item_conflict_adjustment(results, agent_review)
    penalty = int(adjustment.get("penalty") or 0)
    if penalty <= 0:
        return report_data

    target_title = str(adjustment.get("target_title") or "").strip()
    notes = _list(adjustment.get("notes"))
    applied = False
    for index, item in enumerate(items):
        title = str(item.get("title") or "")
        should_apply = index == 0
        if target_title:
            should_apply = target_title in title or title in target_title or index == 0
        if not should_apply:
            continue
        original = int(item.get("originalScore") or item.get("score") or 0)
        item["originalScore"] = original
        item["score"] = max(0, original - penalty)
        item["conflictPenalty"] = penalty
        item["conflictNotes"] = notes
        item["validationStatus"] = "needs_validation"
        if notes:
            reason = str(item.get("reason") or "").strip()
            if notes[0] not in reason:
                item["reason"] = f"{reason} 단, {notes[0]}".strip()
        applied = True
        break

    if applied:
        items.sort(key=lambda item: int(item.get("score") or 0), reverse=True)
        for rank, item in enumerate(items, start=1):
            item["rank"] = rank
        report_data["items"] = items

        analysis = _list(report_data.get("analysis"))
        if notes:
            _append_metric(analysis, "Agent 충돌 반영", notes[0])
        report_data["analysis"] = analysis
    return report_data


def _item_conflict_adjustment(
    results: dict[str, AgentResponse],
    agent_review: dict[str, Any] | None,
) -> dict[str, Any]:
    finance = _data(results, "finance")
    review = _dict(agent_review)
    challenges = _list(review.get("challenges"))
    penalty = 0
    notes: list[str] = []
    target_title = str(finance.get("item_name") or "").strip()

    monthly_profit = finance.get("monthly_profit_krw")
    if isinstance(monthly_profit, (int, float)) and monthly_profit < 0:
        penalty += 15
        notes.append(f"재무 Agent가 월 손익 {_money(monthly_profit)}으로 음수를 감지했습니다.")

    break_even = finance.get("break_even_units_per_day")
    expected = finance.get("expected_daily_customers")
    if isinstance(break_even, (int, float)) and isinstance(expected, (int, float)) and expected > 0 and break_even > expected:
        penalty += 10 if break_even <= expected * 2 else 15
        notes.append(f"손익분기 {int(break_even)}개/day가 현재 예상 {int(expected)}개/day보다 높습니다.")

    budget = _dict(finance.get("budget_analysis"))
    funding_gap = budget.get("funding_gap_krw")
    if isinstance(funding_gap, (int, float)) and funding_gap > 0:
        penalty += 10
        notes.append(f"예산 대비 부족액 {_money(funding_gap)}이 있습니다.")

    if str(finance.get("risk_grade") or "").upper() == "C":
        penalty += 8
        notes.append("재무 Agent 위험 등급이 C라 보수적으로 조정했습니다.")

    for challenge in challenges:
        if not isinstance(challenge, dict):
            continue
        source = str(challenge.get("source_intent") or "")
        target = str(challenge.get("target_intent") or "")
        if source == "finance" and target in {"idea", "orchestrator"}:
            penalty += 10
            issue = str(challenge.get("issue") or "").strip()
            proposal = str(challenge.get("proposal") or "").strip()
            if issue:
                notes.append(issue)
            if proposal:
                notes.append(proposal)
            break

    return {
        "penalty": min(35, penalty),
        "notes": _unique_text(notes)[:4],
        "target_title": target_title,
    }


def _unique_text(values: list[Any]) -> list[str]:
    seen = set()
    result: list[str] = []
    for value in values:
        text = " ".join(str(value or "").split())
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _chat_card(feature_key: str, response: AgentResponse, report_data: dict[str, Any]) -> dict[str, Any]:
    title = _result_title(feature_key, report_data)
    bullets = _chat_card_bullets(feature_key, report_data, response)
    summary = _chat_card_summary(feature_key, response, report_data)
    if not summary and bullets:
        summary = bullets[0]
    return {
        "kind": "feature_report",
        "reportType": FEATURE_REPORT_TYPES[feature_key],
        "featureId": FEATURE_IDS[feature_key],
        "targetFeature": feature_key,
        "resultType": FEATURE_RESULT_TYPES[feature_key],
        "title": title,
        "summary": summary or title,
        "bullets": bullets[:4],
        "ctaLabel": FEATURE_CTA_LABELS[feature_key],
        "routeKey": f"{FEATURE_IDS[feature_key]}-report",
    }


def _chat_card_summary(
    feature_key: str,
    response: AgentResponse,
    report_data: dict[str, Any],
) -> str:
    if feature_key == "PLAN":
        target = report_data.get("target") or "창업 실행안"
        return f"{target} 기준으로 Agent들이 검토한 내용을 사업계획 리포트로 정리했어요."
    if feature_key == "ITEM":
        return "추천 아이템과 선정 근거를 리포트로 정리했어요."
    if feature_key == "SIMULATOR":
        return "초기 비용, 매출, 손익분기 흐름을 시뮬레이션 리포트로 정리했어요."
    if feature_key == "SUPPORT":
        return "지원사업 후보와 선정 근거를 리포트로 정리했어요."
    if feature_key == "OPERATION":
        return "운영 데이터와 개선 액션을 피드백 리포트로 정리했어요."
    if feature_key == "SNS":
        return "SNS 콘텐츠 방향과 실행안을 마케팅 리포트로 정리했어요."
    return _first_paragraph(response.summary)


def _chat_card_bullets(
    feature_key: str,
    report_data: dict[str, Any],
    response: AgentResponse,
) -> list[str]:
    if feature_key == "ITEM":
        items = [item for item in _list(report_data.get("items")) if isinstance(item, dict)]
        return [
            f"{item.get('rank', index + 1)}순위: {item.get('title')} ({item.get('score', '-')}점)"
            for index, item in enumerate(items[:3])
            if item.get("title")
        ]
    if feature_key == "SUPPORT":
        items = [item for item in _list(report_data.get("list")) if isinstance(item, dict)]
        return [
            f"{index + 1}. {item.get('title')} - 적합도 {item.get('score', '-')}점"
            for index, item in enumerate(items[:3])
            if item.get("title")
        ]
    if feature_key == "PLAN":
        sections = _list(report_data.get("sections"))
        return [
            _section_preview(section)
            for section in sections[:4]
            if isinstance(section, list) and section
        ]
    if feature_key == "OPERATION":
        return [
            f"{item[0]}: {item[1]}"
            for item in _list(report_data.get("suggestions"))[:3]
            if isinstance(item, list) and len(item) >= 2
        ]
    if feature_key == "SNS":
        return [
            f"채널: {report_data.get('channel')}",
            f"훅: {report_data.get('hook')}",
            f"CTA: {report_data.get('callToAction')}",
        ]
    if feature_key == "SIMULATOR":
        summary = _dict(report_data.get("summary"))
        bullets = []
        if summary.get("totalRevenue") is not None:
            bullets.append(f"30일 매출 {_money(summary.get('totalRevenue'))}")
        if summary.get("totalProfit") is not None:
            bullets.append(f"30일 손익 {_money(summary.get('totalProfit'))}")
        if summary.get("bepDay"):
            bullets.append(f"손익분기 {summary.get('bepDay')}일차")
        return bullets
    first = _first_paragraph(response.summary)
    return [first] if first else []


def _custom_report_result(request: ChatRequest, response: AgentResponse) -> dict[str, Any]:
    report_block = _custom_report_block(response)
    return {
        "targetFeature": "CUSTOM",
        "resultType": "CUSTOM_REPORT",
        "resultTitle": report_block["title"],
        "shouldCreateResult": False,
        "routeKey": "custom-report",
        "referenceId": _nested(request.context, "rabbitmq", "roomId"),
        "payload": {
            "reportType": "custom",
            "reportBlock": report_block,
        },
    }


def _custom_report_block(response: AgentResponse) -> dict[str, Any]:
    sections = _summary_to_sections(response.summary)
    next_actions = [str(item) for item in response.next_actions[:5] if item]
    if next_actions:
        sections.append({"title": "다음 행동", "items": next_actions})
    return {
        "kind": "custom_report",
        "reportType": "custom",
        "title": "AI 상담 리포트",
        "summary": _first_paragraph(response.summary),
        "sections": sections or [{"title": "요약", "body": response.summary}],
    }


def _summary_to_sections(summary: str) -> list[dict[str, Any]]:
    text = (summary or "").strip()
    if not text:
        return []
    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    if len(parts) <= 1:
        return [{"title": "상담 요약", "body": text}]
    sections: list[dict[str, Any]] = []
    for index, part in enumerate(parts[:6], start=1):
        lines = [line.strip() for line in part.splitlines() if line.strip()]
        title = lines[0].rstrip(":") if lines and len(lines[0]) <= 32 else f"{index}. 핵심 정리"
        body = "\n".join(lines[1:]) if len(lines) > 1 and title == lines[0].rstrip(":") else part
        sections.append({"title": title, "body": body})
    return sections


def _report_data(
    feature_key: str,
    request: ChatRequest,
    results: dict[str, AgentResponse],
) -> dict[str, Any]:
    if feature_key == "ITEM":
        return _item_report(request, results)
    if feature_key == "SIMULATOR":
        return _simulator_report(request, results)
    if feature_key == "SUPPORT":
        return _support_report(results)
    if feature_key == "PLAN":
        return _plan_report(results)
    if feature_key == "OPERATION":
        return _operation_report(request, results)
    if feature_key == "SNS":
        return _sns_report(request, results)
    return {}


def _item_report(request: ChatRequest, results: dict[str, AgentResponse]) -> dict[str, Any]:
    idea = _data(results, "idea")
    finance = _data(results, "finance")
    recommendations = _list(idea.get("recommendations")) or _list(idea.get("all_candidates"))
    if not recommendations and isinstance(idea.get("evidence"), dict):
        recommendations = [_dict(idea["evidence"].get("top_idea"))]

    grounding = _item_grounding(results)
    region = (
        grounding["commercial_area"].get("area_label")
        or request.profile.region
        or _nested(request.context, "currentResult", "location")
        or "선택 지역"
    )
    items = _ground_item_recommendations(
        recommendations=recommendations,
        idea=idea,
        request=request,
        grounding=grounding,
        region=region,
    )
    missing_evidence = list(grounding["missing_evidence"])
    if not items:
        missing_evidence.append("아이템 후보")
    elif grounding["support_matches"] and not any(item.get("supportPrograms") for item in items):
        missing_evidence.append("아이템-지원사업 직접 매칭")

    return {
        "location": region,
        "analysis": _item_report_analysis(idea, finance, grounding, items),
        "items": items,
        "dataSources": grounding["data_sources"],
        "missingEvidence": _unique_lines(missing_evidence),
    }


def _item_grounding(results: dict[str, AgentResponse]) -> dict[str, Any]:
    commercial = _commercial_area_metrics(_data(results, "commercial_area"))
    support_matches = _policy_matches(_data(results, "policy"))
    data_sources = []
    missing_evidence = []

    if commercial.get("available"):
        data_sources.append("상권 데이터")
    else:
        missing_evidence.append("상권 데이터")

    if support_matches:
        data_sources.append("지원사업 추천")
    else:
        missing_evidence.append("지원사업 추천")

    return {
        "commercial_area": commercial,
        "support_matches": support_matches,
        "data_sources": data_sources,
        "missing_evidence": missing_evidence,
    }


def _ground_item_recommendations(
    *,
    recommendations: list[Any],
    idea: dict[str, Any],
    request: ChatRequest,
    grounding: dict[str, Any],
    region: str,
) -> list[dict[str, Any]]:
    items = []
    for index, raw_item in enumerate(recommendations, start=1):
        item = _dict(raw_item)
        if _is_template_candidate(item):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue

        base_score = _safe_int(
            item.get("match_score")
            or item.get("score")
            or (idea.get("score") if index == 1 else None),
            0,
        )
        category = str(item.get("business_type") or item.get("category") or "AI 추천 아이템")
        score_data = _grounded_item_score(item, base_score, grounding)
        item_analysis = _item_analysis_for_candidate(item, score_data, grounding)
        support_programs = _matched_support_programs(item, grounding["support_matches"])
        evidence = _grounding_evidence(score_data, support_programs, grounding)
        reason = _grounded_item_reason(item, idea, evidence)

        items.append({
            "rank": index,
            "title": title,
            "score": score_data["grounded_score"],
            "baseScore": base_score,
            "reason": reason,
            "category": category,
            "location": str(item.get("location") or region),
            "estimatedInitialCost": item.get("estimated_initial_cost_krw"),
            "analysis": item_analysis,
            "evidence": evidence,
            "scoreBreakdown": score_data["breakdown"],
            "supportPrograms": support_programs,
            "commercialArea": _public_commercial_area(grounding["commercial_area"]),
            "generatedBy": item.get("generated_by"),
            "feasibilityLabel": item.get("feasibility_label"),
            "validationMethod": item.get("validation_method"),
            "first30Days": _list(item.get("first_30_days")),
            "risks": _list(item.get("risks")),
        })

    items.sort(key=lambda value: (value["score"], value["baseScore"]), reverse=True)
    for rank, item in enumerate(items[:3], start=1):
        item["rank"] = rank
    return items[:3]


def _grounded_item_score(
    item: dict[str, Any],
    base_score: int,
    grounding: dict[str, Any],
) -> dict[str, Any]:
    commercial = grounding["commercial_area"]
    support_matches = _matched_support_programs(item, grounding["support_matches"])
    commercial_adjustment = _commercial_area_adjustment(item, commercial)
    support_adjustment = _support_program_adjustment(support_matches)
    missing_evidence_adjustment = _missing_evidence_adjustment(item, grounding)
    grounded_score = max(0, min(100, base_score + commercial_adjustment + support_adjustment + missing_evidence_adjustment))
    return {
        "grounded_score": grounded_score,
        "breakdown": {
            "base_score": base_score,
            "commercial_area_adjustment": commercial_adjustment,
            "support_program_adjustment": support_adjustment,
            "missing_evidence_adjustment": missing_evidence_adjustment,
            "grounded_score": grounded_score,
        },
    }


def _is_template_candidate(item: dict[str, Any]) -> bool:
    generated_by = str(item.get("generated_by") or item.get("generatedBy") or "").strip().lower()
    return generated_by in {"rule_fallback", "guardrail"}


def _commercial_area_adjustment(item: dict[str, Any], commercial: dict[str, Any]) -> int:
    if not commercial.get("available"):
        return 0

    relevant = _commercial_area_relevant(item)
    level = str(commercial.get("competition_level") or "").lower()
    direct = _safe_int(commercial.get("direct_competitors"), 0)
    adjustment = 0

    if relevant:
        if level == "high":
            adjustment -= 14
        elif level == "medium":
            adjustment -= 6
        elif level == "low":
            adjustment += 5

        if direct >= 100:
            adjustment -= 6
        elif direct >= 30:
            adjustment -= 3
        elif 0 < direct <= 10:
            adjustment += 2
    elif level == "high":
        adjustment += 3

    return adjustment


def _support_program_adjustment(matches: list[dict[str, Any]]) -> int:
    if not matches:
        return 0
    top_score = _safe_int(matches[0].get("score"), 0)
    direct = bool(matches[0].get("keywordOverlap"))
    if top_score >= 85 and direct:
        return 7
    if top_score >= 70 and direct:
        return 5
    return 0


def _missing_evidence_adjustment(item: dict[str, Any], grounding: dict[str, Any]) -> int:
    penalty = 0
    if _commercial_area_relevant(item) and "상권 데이터" in grounding["missing_evidence"]:
        penalty -= 3
    if "지원사업 추천" in grounding["missing_evidence"]:
        penalty -= 2
    return penalty


def _item_analysis_for_candidate(
    item: dict[str, Any],
    score_data: dict[str, Any],
    grounding: dict[str, Any],
) -> list[list[str]]:
    analysis = [
        ["근거 반영 점수", f"{score_data['grounded_score']}점"],
        ["기본 적합도", f"{score_data['breakdown']['base_score']}점"],
    ]
    commercial = grounding["commercial_area"]
    if commercial.get("available"):
        analysis.append(["상권 경쟁도", str(commercial.get("competition_level") or "-")])
        direct = commercial.get("direct_competitors")
        if isinstance(direct, (int, float)):
            analysis.append(["직접 경쟁점", f"{int(direct):,}개"])
    else:
        analysis.append(["상권 근거", "데이터 없음"])

    matches = _matched_support_programs(item, grounding["support_matches"])
    if matches:
        analysis.append(["지원사업 근거", f"{matches[0]['title']} ({matches[0]['score']}점)"])
    else:
        analysis.append(["지원사업 근거", "매칭 없음"])
    return analysis


def _grounding_evidence(
    score_data: dict[str, Any],
    support_programs: list[dict[str, Any]],
    grounding: dict[str, Any],
) -> list[str]:
    evidence = []
    commercial = grounding["commercial_area"]
    commercial_delta = score_data["breakdown"]["commercial_area_adjustment"]
    support_delta = score_data["breakdown"]["support_program_adjustment"]
    missing_delta = score_data["breakdown"]["missing_evidence_adjustment"]

    if commercial.get("available"):
        level = commercial.get("competition_level") or "unknown"
        direct = commercial.get("direct_competitors")
        direct_text = f", 직접 경쟁점 {int(direct):,}개" if isinstance(direct, (int, float)) else ""
        evidence.append(f"상권 {level}{direct_text} 반영({commercial_delta:+d})")
    else:
        evidence.append("상권 데이터 없음")

    if support_programs:
        evidence.append(f"지원사업 {support_programs[0]['score']}점 매칭 반영({support_delta:+d})")
    else:
        evidence.append("지원사업 매칭 없음")

    if missing_delta:
        evidence.append(f"근거 부족 보정({missing_delta:+d})")
    return evidence


def _grounded_item_reason(item: dict[str, Any], idea: dict[str, Any], evidence: list[str]) -> str:
    base = str(
        item.get("reason")
        or item.get("validation_method")
        or idea.get("recommendation")
        or "아이템 후보입니다."
    ).strip()
    evidence_text = " / ".join(evidence[:3])
    if evidence_text:
        return _limit_text(f"{base} 근거: {evidence_text}", 420)
    return _limit_text(base, 420)


def _item_report_analysis(
    idea: dict[str, Any],
    finance: dict[str, Any],
    grounding: dict[str, Any],
    items: list[dict[str, Any]],
) -> list[list[str]]:
    analysis = [
        ["프로필 적합도", f"{int(idea.get('score') or 0)}점"],
        ["예상 초기자금", _money(finance.get("initial_cash_needed_krw"))],
        ["손익분기", f"하루 {finance.get('break_even_units_per_day') or '-'}건"],
    ]
    commercial = grounding["commercial_area"]
    if commercial.get("available"):
        analysis.append(["상권 경쟁도", str(commercial.get("competition_level") or "-")])
        direct = commercial.get("direct_competitors")
        if isinstance(direct, (int, float)):
            analysis.append(["직접 경쟁점", f"{int(direct):,}개"])

    support_matches = [
        program
        for item in items
        for program in _list(item.get("supportPrograms"))
    ]
    if support_matches:
        analysis.append(["지원사업 후보", f"{support_matches[0]['title']} ({support_matches[0]['score']}점)"])
    analysis.append(["주요 리스크", _first(_list(idea.get("risks")), "초기 고객 검증 필요")])
    if grounding["missing_evidence"]:
        analysis.append(["부족 근거", ", ".join(grounding["missing_evidence"])])
    return analysis


def _policy_matches(policy: dict[str, Any]) -> list[dict[str, Any]]:
    raw_matches = _list(policy.get("matches")) or _list(policy.get("match_summary"))
    matches = []
    for item in raw_matches:
        match = _dict(item)
        title = str(match.get("title") or "").strip()
        if not title:
            continue
        matches.append({
            "id": match.get("id") or title,
            "title": title,
            "score": _safe_int(match.get("eligibility_score") or match.get("score"), 0),
            "summary": str(match.get("summary") or "").strip(),
            "region": str(match.get("region") or match.get("region_condition") or "").strip(),
            "amount": match.get("support_amount"),
            "due": match.get("application_end_date") or match.get("deadline") or match.get("due"),
            "url": match.get("url"),
            "source": match.get("source_note"),
            "supportType": match.get("support_type"),
            "whyMatched": _list(match.get("why_matched")),
        })
    matches.sort(key=lambda value: value["score"], reverse=True)
    return matches


def _matched_support_programs(item: dict[str, Any], support_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not support_matches:
        return []
    item_terms = _item_terms(item)
    scored = []
    for match in support_matches:
        match_terms = _item_terms(match)
        overlap = _meaningful_support_overlap(item_terms, match_terms)
        if not overlap:
            continue
        score = _safe_int(match.get("score"), 0) + min(10, len(overlap) * 3)
        scored.append({
            **match,
            "score": max(0, min(100, score)),
            "keywordOverlap": overlap,
            "matchBasis": "아이템 키워드 일치",
        })
    scored.sort(key=lambda value: value["score"], reverse=True)
    return scored[:2]


def _meaningful_support_overlap(item_terms: set[str], match_terms: set[str]) -> list[str]:
    return sorted(
        term
        for term in item_terms & match_terms
        if _is_meaningful_support_term(term)
    )


def _is_meaningful_support_term(term: str) -> bool:
    normalized = str(term or "").strip().lower()
    if len(normalized) < 2:
        return False
    return normalized not in SUPPORT_MATCH_STOP_TERMS


def _item_terms(item: dict[str, Any]) -> set[str]:
    raw_values = [
        item.get("title"),
        item.get("summary"),
        item.get("reason"),
        item.get("category"),
        item.get("business_type"),
        item.get("supportType"),
        item.get("region"),
        item.get("target_customer"),
        *(_list(item.get("keywords"))),
        *(_list(item.get("why_fit"))),
        *(_list(item.get("whyMatched"))),
    ]
    text = " ".join(str(value or "") for value in raw_values).lower()
    tokens = {token for token in re_split_terms(text) if len(token) >= 2}
    for keyword in [
        "카페",
        "커피",
        "푸드",
        "외식",
        "한식",
        "디저트",
        "소상공인",
        "로컬",
        "sns",
        "콘텐츠",
        "마케팅",
        "기술",
        "서비스",
        "창업",
        "예비창업",
        "청년",
        "온라인",
        "오프라인",
        "팝업",
        "예약판매",
    ]:
        if keyword in text:
            tokens.add(keyword)
    return tokens


def re_split_terms(text: str) -> list[str]:
    separators = ",/|()[]{}<>·&+:-_\"'“”‘’\n\r\t"
    normalized = str(text or "")
    for separator in separators:
        normalized = normalized.replace(separator, " ")
    return [
        token.strip(" .!?;，。！？")
        for token in normalized.split()
        if token.strip(" .!?;，。！？")
    ]


def _commercial_area_relevant(item: dict[str, Any]) -> bool:
    business_type = str(item.get("business_type") or item.get("category") or "").lower()
    text = " ".join(
        str(value or "")
        for value in [
            item.get("title"),
            business_type,
            item.get("category"),
            item.get("target_customer"),
            item.get("reason"),
            " ".join(map(str, _list(item.get("channels")))),
            " ".join(map(str, _list(item.get("keywords")))),
        ]
    ).lower()
    if business_type in {"food", "cafe", "popup"}:
        return True
    if business_type in {"content", "service"}:
        return any(keyword in text for keyword in ["팝업", "공유주방", "매장 창업", "직접 매장", "오프라인 판매"])
    return any(
        keyword in text
        for keyword in ["food", "cafe", "popup", "카페", "커피", "푸드", "외식", "식당", "매장", "팝업", "오프라인", "공유주방", "상권"]
    )


def _public_commercial_area(commercial: dict[str, Any]) -> dict[str, Any] | None:
    if not commercial.get("available"):
        return None
    return {
        "areaLabel": commercial.get("area_label"),
        "industryLabel": commercial.get("industry_label"),
        "competitionLevel": commercial.get("competition_level"),
        "totalStores": commercial.get("total_stores"),
        "directCompetitors": commercial.get("direct_competitors"),
        "similarCompetitors": commercial.get("similar_competitors"),
        "source": commercial.get("source"),
    }


def _simulator_report(request: ChatRequest, results: dict[str, AgentResponse]) -> dict[str, Any]:
    current = _current_result(request)
    existing_report = _dict(current.get("report"))
    if existing_report.get("metrics") and existing_report.get("summary"):
        return existing_report

    finance = _data(results, "finance")
    item_name = finance.get("item_name") or _nested(current, "simulationInput", "item") or "선택한 창업 아이템"
    price = int(finance.get("price_per_unit_krw") or _nested(current, "simulationInput", "price") or 8000)
    daily = int(finance.get("expected_daily_customers") or _nested(current, "simulationInput", "startOrders") or 12)
    variable_rate = float(finance.get("variable_cost_rate") or 0.35)
    fixed_cost = int(finance.get("monthly_fixed_cost_krw") or 2_000_000)
    metrics = []
    cumulative = 0
    total_revenue = 0
    total_cost = 0
    bep_day = None
    for day in range(1, 31):
        orders = max(0, round(daily * (0.68 + day / 80)))
        revenue = orders * price
        variable_cost = round(revenue * variable_rate)
        fixed = round(fixed_cost / 26)
        profit = revenue - variable_cost - fixed
        cumulative += profit
        total_revenue += revenue
        total_cost += variable_cost + fixed
        if bep_day is None and cumulative >= 0:
            bep_day = day
        metrics.append({
            "day": day,
            "orders": orders,
            "revenue": revenue,
            "variableCost": variable_cost,
            "fixedCost": fixed,
            "profit": profit,
            "cumulativeProfit": cumulative,
            "cashBalance": int(finance.get("initial_cash_needed_krw") or 0) + cumulative,
        })
    return {
        "ideaTitle": item_name,
        "metrics": metrics,
        "summary": {
            "totalRevenue": total_revenue,
            "totalCost": total_cost,
            "totalProfit": total_revenue - total_cost,
            "bepDay": bep_day,
            "cashShortageRisk": "높음" if total_revenue < total_cost else "낮음",
        },
    }


def _support_report(results: dict[str, AgentResponse]) -> dict[str, Any]:
    policy = _data(results, "policy")
    matches = _list(policy.get("matches")) or _list(policy.get("match_summary"))
    items = []
    for item in matches[:5]:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        items.append({
            "id": item.get("id") or title,
            "title": title,
            "score": int(item.get("eligibility_score") or item.get("score") or 0),
            "region": str(item.get("region") or item.get("region_condition") or ""),
            "due": str(item.get("due") or item.get("deadline") or item.get("application_end_date") or ""),
            "docs": _list(item.get("required_documents")),
            "summary": item.get("summary"),
            "url": item.get("url"),
            "amount": item.get("support_amount"),
            "organization": item.get("organization"),
            "source": item.get("source_note"),
        })
    return {"list": items}


def _plan_report(results: dict[str, AgentResponse]) -> dict[str, Any]:
    plan = _data(results, "plan")
    sections = _list(plan.get("sections"))
    return {
        "target": str(plan.get("target") or "창업 지원사업"),
        "sections": [
            [str(item.get("title") or f"{index}. 섹션"), str(item.get("body") or "내용을 보완하세요.")]
            for index, item in enumerate(sections[:6], start=1)
            if isinstance(item, dict)
        ] or [
            ["1. 사업 개요", str(plan.get("recommendation") or "선택한 아이템을 기준으로 사업 개요를 정리하세요.")],
        ],
    }


def _plan_report(results: dict[str, AgentResponse]) -> dict[str, Any]:
    plan = _data(results, "plan")
    sections = _list(plan.get("sections"))
    generated_sections = [
        section
        for section in [
            _agent_section("추천 방향", results, "idea"),
            _agent_section("재무 검토", results, "finance"),
            _agent_section("지원사업 검토", results, "policy"),
            _agent_section("상권/입지 검토", results, "commercial_area"),
            _agent_section("마케팅 실행", results, "marketing"),
            _agent_section("운영 리스크", results, "operation"),
        ]
        if section
    ]
    generated_sections = [
        [f"{index}. {section[0]}", section[1]]
        for index, section in enumerate(generated_sections, start=1)
    ]
    return {
        "target": str(plan.get("target") or _plan_target(results)),
        "sections": [
            [str(item.get("title") or f"{index}. 섹션"), str(item.get("body") or "내용을 보완하세요.")]
            for index, item in enumerate(sections[:6], start=1)
            if isinstance(item, dict)
        ] or generated_sections or [
            ["1. 사업 개요", str(plan.get("recommendation") or "선택된 아이템과 검토 근거를 기준으로 사업 방향을 정리하세요.")],
        ],
    }


def _plan_target(results: dict[str, AgentResponse]) -> str:
    idea = _data(results, "idea")
    top = _first_idea(idea)
    if top.get("title"):
        return str(top["title"])
    finance = _data(results, "finance")
    if finance.get("item_name"):
        return str(finance["item_name"])
    return "AI 창업 실행안"


def _agent_section(title: str, results: dict[str, AgentResponse], intent: str) -> list[str] | None:
    response = results.get(intent)
    if response is None:
        return None
    data = response.data or {}
    lines: list[str] = []
    summary = str(response.summary or "").strip()
    if summary:
        lines.append(summary)

    if intent == "idea":
        top = _first_idea(data)
        if top.get("title"):
            lines.append(f"1순위 후보: {top.get('title')}")
        if top.get("match_score"):
            lines.append(f"적합도: {top.get('match_score')}점")
        reasons = _list(top.get("why_recommended")) or _list(top.get("reasons"))
        if reasons:
            lines.append(f"추천 근거: {', '.join(map(str, reasons[:3]))}")
    elif intent == "finance":
        for key, label in [
            ("initial_cash_needed_krw", "초기 필요 현금"),
            ("monthly_profit_krw", "월 예상 손익"),
            ("break_even_units_per_day", "손익분기 판매량"),
        ]:
            value = data.get(key)
            if value is not None:
                suffix = "원" if key.endswith("_krw") else "개/day"
                lines.append(f"{label}: {_number(value)}{suffix}")
    elif intent == "policy":
        matches = _list(data.get("matches"))
        if matches and isinstance(matches[0], dict):
            top = matches[0]
            if top.get("title"):
                lines.append(f"1순위 공고: {top.get('title')}")
            if top.get("eligibility_score") or top.get("score"):
                lines.append(f"적합도: {top.get('eligibility_score') or top.get('score')}점")
            if top.get("summary"):
                lines.append(f"공고 핵심: {top.get('summary')}")
    elif intent == "commercial_area":
        payload = _dict(data.get("payload")) or data
        for key, label in [
            ("region", "지역"),
            ("business_type", "업종"),
            ("total_stores", "전체 점포"),
            ("direct_competitors", "직접 경쟁점"),
            ("competition_level", "경쟁 강도"),
        ]:
            value = payload.get(key)
            if value not in (None, ""):
                lines.append(f"{label}: {value}")
    elif intent == "marketing":
        for key, label in [
            ("target_customer", "타깃"),
            ("channel", "채널"),
            ("objective", "목표"),
            ("reels_hook", "콘텐츠 훅"),
        ]:
            value = data.get(key)
            if value:
                lines.append(f"{label}: {value}")
    elif intent == "operation":
        missing = _list(data.get("missing_inputs"))
        risks = _list(data.get("risk_items")) or _list(data.get("risks"))
        if missing:
            lines.append(f"부족 데이터: {', '.join(map(str, missing[:4]))}")
        if risks:
            lines.append(f"우선 리스크: {_first_text(risks[0])}")

    body = "\n".join(_unique_lines(lines))
    return [title, body] if body else None


def _first_idea(data: dict[str, Any]) -> dict[str, Any]:
    recommendations = _list(data.get("recommendations")) or _list(data.get("all_candidates"))
    if recommendations and isinstance(recommendations[0], dict):
        return recommendations[0]
    evidence = _dict(data.get("evidence"))
    return _dict(evidence.get("top_idea"))


def _with_agent_review(
    feature_key: str,
    report_data: dict[str, Any],
    results: dict[str, AgentResponse],
    agent_review: dict[str, Any] | None,
) -> dict[str, Any]:
    review = _dict(agent_review)
    if feature_key not in FEATURE_REVIEW_FEATURES or not review:
        return report_data

    compact_review = {
        "summary": str(review.get("summary") or "Agent들이 리포트 초안을 검토했습니다."),
        "checks": _list(review.get("checks"))[:4],
        "revisions": _list(review.get("revisions"))[:4],
    }
    report_data["agentReview"] = compact_review

    if feature_key == "ITEM":
        _apply_item_review(report_data, results, compact_review)
    elif feature_key == "SUPPORT":
        _apply_support_review(report_data, compact_review)
    elif feature_key == "PLAN":
        _apply_plan_review(report_data, compact_review)
    return report_data


def _apply_item_review(
    report_data: dict[str, Any],
    results: dict[str, AgentResponse],
    review: dict[str, Any],
) -> None:
    analysis = _list(report_data.get("analysis"))
    commercial = _data(results, "commercial_area")
    metrics = _commercial_area_metrics(commercial)
    if metrics.get("competition_level"):
        _append_metric(analysis, "상권 경쟁도", str(metrics["competition_level"]))
    if isinstance(metrics.get("direct_competitors"), (int, float)):
        _append_metric(analysis, "직접 경쟁점", f"{int(metrics['direct_competitors']):,}개")
    if analysis:
        report_data["analysis"] = analysis

    revisions = _list(review.get("revisions"))
    items = _list(report_data.get("items"))
    if revisions and items and isinstance(items[0], dict):
        current_reason = str(items[0].get("reason") or "")
        if "Agent 검토" not in current_reason:
            items[0]["reason"] = f"{current_reason} Agent 검토: {revisions[0]}".strip()


def _apply_support_review(report_data: dict[str, Any], review: dict[str, Any]) -> None:
    revisions = _list(review.get("revisions"))
    items = [item for item in _list(report_data.get("list")) if isinstance(item, dict)]
    for item in items[:3]:
        docs = _list(item.get("docs"))
        if "자금 사용 계획" not in docs:
            item["docs"] = [*docs, "자금 사용 계획"] if docs else ["사업계획서", "자격 증빙", "자금 사용 계획"]
    if revisions and items and not items[0].get("summary"):
        items[0]["summary"] = f"Agent 검토 반영: {revisions[0]}"


def _apply_plan_review(report_data: dict[str, Any], review: dict[str, Any]) -> None:
    revisions = _list(review.get("revisions"))
    if not revisions:
        return
    sections = _list(report_data.get("sections"))
    if any(isinstance(section, list) and section and section[0] == "Agent 검토 반영사항" for section in sections):
        return
    sections.append(["Agent 검토 반영사항", " / ".join(map(str, revisions[:3]))])
    report_data["sections"] = sections[:7]


def _agent_discussion(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "rounds": _list(review.get("rounds")),
        "challenges": _list(review.get("challenges")),
        "revisions": _list(review.get("revisionMessages")),
        "consensus": _dict(review.get("consensus")),
    }


def _commercial_area_metrics(data: dict[str, Any]) -> dict[str, Any]:
    payload = _dict(data.get("payload"))
    area = _dict(payload.get("commercial_area"))
    available = bool(
        data.get("reference_data_used")
        or payload.get("reference_data_used")
        or area
        or payload.get("competition_level")
        or payload.get("direct_competitors") is not None
        or data.get("competition_level")
        or data.get("direct_competitors") is not None
    )
    return {
        "available": available,
        "area_label": (
            payload.get("area")
            or area.get("areaLabel")
            or area.get("area")
            or data.get("area")
        ),
        "industry_label": (
            payload.get("industry")
            or area.get("industryLabel")
            or area.get("industry")
            or data.get("industry")
        ),
        "total_stores": _safe_int(
            payload.get("total_stores")
            or area.get("totalStores")
            or data.get("total_stores"),
            0,
        ),
        "competition_level": (
            payload.get("competition_level")
            or area.get("competitionLevel")
            or data.get("competition_level")
        ),
        "direct_competitors": _safe_int(
            payload.get("direct_competitors")
            or area.get("directCompetitors")
            or data.get("direct_competitors"),
            0,
        ),
        "similar_competitors": _safe_int(
            payload.get("similar_competitors")
            or area.get("similarCompetitors")
            or data.get("similar_competitors"),
            0,
        ),
        "source": _first(_list(payload.get("reference_sources")), "backend.commercial_area") if available else None,
    }


def _append_metric(analysis: list[Any], label: str, value: str) -> None:
    if not value or any(isinstance(item, list) and item and item[0] == label for item in analysis):
        return
    analysis.append([label, value])


def _operation_report(request: ChatRequest, results: dict[str, AgentResponse]) -> dict[str, Any]:
    current = _current_result(request)
    input_data = _dict(current.get("operationInput"))
    operation = _data(results, "operation")
    risks = _list(operation.get("risk_items")) or _list(operation.get("risks"))
    actions = _list(operation.get("recommended_actions")) or _list(operation.get("next_week_plan")) or _list(operation.get("risks"))
    suggestions = []
    for index, item in enumerate(actions[:3], start=1):
        if isinstance(item, dict):
            title = str(item.get("action") or item.get("title") or f"개선 제안 {index}")
            body = str(item.get("reason") or item.get("body") or item.get("description") or title)
        else:
            title = str(item)
            body = str(item)
        suggestions.append([title, body, "sns" if index == 1 else None])
    if not suggestions:
        suggestions = [["운영 데이터 보강", operation.get("recommendation") or "매출, 주문, 재고, 고객 피드백을 주간 단위로 기록하세요.", None]]

    return {
        "period": str(input_data.get("period") or current.get("period") or "최근 30일"),
        "kpis": _list(input_data.get("kpis")) or [
            ["이번 달 매출", _money(operation.get("monthly_sales_krw")), "", None],
            ["주문 수", f"{operation.get('orders') or 0}건", "", None],
            ["광고 전환율", _percent(operation.get("conversion_rate")), "", None],
            ["운영 점수", f"{int(operation.get('score') or 75)}점", "", True],
        ],
        "products": _list(input_data.get("products")) or [["대표 상품", 60], ["보조 상품", 40]],
        "channels": _list(input_data.get("channels")) or [["AI 진단", _first(risks, "현재 입력 기준 큰 위험 신호는 제한적입니다.")]],
        "notes": str(input_data.get("notes") or current.get("notes") or operation.get("position") or ""),
        "suggestions": suggestions,
    }


def _sns_report(request: ChatRequest, results: dict[str, AgentResponse]) -> dict[str, Any]:
    marketing = _data(results, "marketing")
    current = _current_result(request)
    draft = _dict(current.get("campaignDraft"))
    hook = marketing.get("reels_hook") or _nested(marketing, "evidence", "reels_hook") or draft.get("hook")
    return {
        "topic": str(draft.get("topic") or marketing.get("product_name") or "AI 캠페인"),
        "hook": str(hook or marketing.get("caption") or "고객이 바로 반응할 한 문장으로 시작하세요."),
        "beats": _list(marketing.get("storyboard_15s")) or _list(draft.get("beats")) or [
            "0-3초: 제품/문제 상황 제시",
            "4-8초: 차별점 노출",
            "9-12초: 혜택과 장소 안내",
            "13-15초: CTA",
        ],
        "tags": _list(marketing.get("hashtags")) or _list(draft.get("tags")) or ["#청년창업", "#로컬브랜드"],
        "channel": _channel_code(marketing.get("channel") or draft.get("channel")),
        "tone": str(draft.get("tone") or "FRIENDLY"),
        "objective": _objective_code(marketing.get("objective") or draft.get("objective")),
        "callToAction": str(draft.get("callToAction") or "지금 문의하기"),
        "schedule": str(draft.get("schedule") or _first([item.get("when") for item in _list(marketing.get("upload_schedule")) if isinstance(item, dict)], "이번 주 오전")),
    }


def _result_title(feature_key: str, report_data: dict[str, Any]) -> str:
    if feature_key == "ITEM":
        return "AI 창업 아이템 추천 리포트"
    if feature_key == "SUPPORT":
        first = _first([item.get("title") for item in _list(report_data.get("list")) if isinstance(item, dict)], "")
        return f"{first} 지원사업 리포트" if first else "지원사업 추천 리포트"
    if feature_key == "PLAN":
        return f"{report_data.get('target') or '지원사업'} 사업계획서 초안"
    if feature_key == "OPERATION":
        return f"{report_data.get('period') or '운영'} 피드백 리포트"
    if feature_key == "SNS":
        return f"{report_data.get('topic') or 'SNS'} 캠페인 초안"
    return "AI 기능 리포트"


def _compact_text(value: Any, *, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text


def _first_paragraph(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return next((part.strip() for part in text.split("\n\n") if part.strip()), text)


def _number(value: Any) -> str:
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return str(value)


def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _limit_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _unique_lines(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _first_text(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("risk", "title", "summary", "description", "reason", "text"):
            text = str(value.get(key) or "").strip()
            if text:
                return text
        return ""
    if isinstance(value, list):
        for item in value:
            text = _first_text(item)
            if text:
                return text
        return ""
    return str(value or "").strip()


def _section_preview(section: list[Any]) -> str:
    title = str(section[0] if section else "").strip()
    body = str(section[1] if len(section) > 1 else "").strip()
    if not body:
        return title
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    preview = " ".join(lines[:3])
    if not preview:
        return title
    return f"{title}\n{preview}"


def _data(results: dict[str, AgentResponse], intent: str) -> dict[str, Any]:
    response = results.get(intent)
    return response.data if response else {}


def _current_result(request: ChatRequest) -> dict[str, Any]:
    context = request.context or {}
    current = context.get("currentResult")
    if isinstance(current, dict):
        return current
    result_context = _dict(context.get("resultContext"))
    return _dict(result_context.get("currentResult"))


def _nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first(values: list[Any], fallback: str) -> str:
    for value in values:
        if value:
            return str(value)
    return fallback


def _money(value: Any) -> str:
    try:
        return f"{int(float(value)):,}원"
    except (TypeError, ValueError):
        return "-"


def _percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if number <= 1:
        number *= 100
    return f"{number:.1f}%"


def _channel_code(value: Any) -> str:
    text = str(value or "").lower()
    if "short" in text or "쇼츠" in text:
        return "SHORTS"
    if "blog" in text or "블로그" in text:
        return "BLOG_POST"
    if "post" in text or "피드" in text:
        return "INSTAGRAM_POST"
    return "INSTAGRAM_REELS"


def _objective_code(value: Any) -> str:
    text = str(value or "").lower()
    if any(keyword in text for keyword in ["awareness", "인지", "브랜딩"]):
        return "AWARENESS"
    if any(keyword in text for keyword in ["revisit", "재방문"]):
        return "REVISIT"
    if any(keyword in text for keyword in ["event", "행사", "방문"]):
        return "EVENT"
    return "CONVERSION"
