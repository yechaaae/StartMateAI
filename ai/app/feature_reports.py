from __future__ import annotations

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


def build_feature_result(
    *,
    request: ChatRequest,
    response: AgentResponse,
    results: dict[str, AgentResponse],
    agent_review: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    feature_key = feature_key_from_request(request)
    if feature_key not in FEATURE_REPORT_TEAMS:
        return None

    report_data = _report_data(feature_key, request, results)
    if not report_data:
        return None
    report_data = _with_agent_review(feature_key, report_data, results, agent_review)

    payload = {
        "featureId": FEATURE_IDS[feature_key],
        "reportData": report_data,
        "agentSummary": response.summary,
        "selectedAgents": [item.agent for item in results.values()],
        "agentResults": {intent: item.data for intent, item in results.items()},
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

    items = []
    for index, item in enumerate(recommendations[:3], start=1):
        items.append({
            "rank": index,
            "title": str(item.get("title") or f"추천 아이템 {index}"),
            "score": int(item.get("match_score") or item.get("score") or max(70, 94 - index * 5)),
            "reason": str(item.get("reason") or item.get("validation_method") or idea.get("recommendation") or "현재 프로필과 예산에 맞는 후보입니다."),
            "category": str(item.get("business_type") or item.get("category") or "AI 추천 아이템"),
            "estimatedInitialCost": item.get("estimated_initial_cost_krw"),
        })

    region = request.profile.region or _nested(request.context, "currentResult", "location") or "선택 지역"
    return {
        "location": region,
        "analysis": [
            ["프로필 적합도", f"{int(idea.get('score') or 82)}점"],
            ["예상 초기자금", _money(finance.get("initial_cash_needed_krw"))],
            ["손익분기", f"하루 {finance.get('break_even_units_per_day') or '-'}건"],
            ["주요 리스크", _first(_list(idea.get("risks")), "초기 고객 검증 필요")],
        ],
        "items": items or [
            {"rank": 1, "title": "AI 추천 창업 아이템", "score": 80, "reason": idea.get("recommendation") or "추가 정보 입력 후 더 정교하게 추천할 수 있습니다."},
        ],
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
        title = str(item.get("title") or "지원사업 후보")
        items.append({
            "id": item.get("id") or title,
            "title": title,
            "score": int(item.get("eligibility_score") or item.get("score") or 70),
            "region": str(item.get("region") or item.get("source_note") or "전국"),
            "due": str(item.get("due") or item.get("deadline") or "일정 확인"),
            "docs": _list(item.get("required_documents")) or ["사업계획서", "자격 증빙"],
            "summary": item.get("summary"),
            "url": item.get("url"),
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
    return {
        "competition_level": (
            payload.get("competition_level")
            or area.get("competitionLevel")
            or data.get("competition_level")
        ),
        "direct_competitors": (
            payload.get("direct_competitors")
            or area.get("directCompetitors")
            or data.get("direct_competitors")
        ),
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
