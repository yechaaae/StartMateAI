"""기능(feature)별 Agent 발언권(power/weight) 테이블.

각 기능 리포트에서 Agent마다 결론에 주는 영향력을 다르게 둬서, 보조 Agent가
실패하거나 의견이 갈려도 lead Agent를 중심으로 결과가 항상 하나로 결정되게 한다.

- lead: 그 기능의 결론을 쥔 Agent. 이 Agent의 산출물(ITEM=아이템 후보,
  SUPPORT=지원사업 매칭, PLAN=사업계획 섹션)은 비어있지 않게 보장한다.
- weights: 보조 Agent의 점수 보정치에 곱하는 가중치. 값이 클수록 발언권이 세다.
  lead Agent는 보통 1.0(기본 점수의 지배항).

운영 피드백(OPERATION)·창업 시뮬레이션(SIMULATOR)·SNS(SNS)는 이번 범위에서
제외이므로 테이블에 포함하지 않는다(가중치 미적용 = 기존 동작 유지).
"""

from __future__ import annotations

from typing import Any


FEATURE_AGENT_POWER: dict[str, dict[str, Any]] = {
    "ITEM": {
        "lead": "idea",
        "weights": {
            "idea": 1.0,
            "finance": 0.7,
            "commercial_area": 0.6,
            "policy": 0.5,
            "profile": 0.3,
        },
    },
    "SUPPORT": {
        "lead": "policy",
        "weights": {
            "policy": 1.0,
            "finance": 0.5,
            "profile": 0.4,
            "idea": 0.3,
        },
    },
    "PLAN": {
        "lead": "plan",
        "weights": {
            "plan": 1.0,
            "idea": 0.6,
            "finance": 0.6,
            "policy": 0.5,
            "commercial_area": 0.4,
            "profile": 0.3,
        },
    },
}


def feature_weights(feature_key: str) -> dict[str, float]:
    """기능별 Agent 가중치 dict를 반환한다(미정의 기능/Agent는 1.0 기본)."""
    entry = FEATURE_AGENT_POWER.get(str(feature_key or "").upper())
    if not entry:
        return {}
    return dict(entry.get("weights") or {})


def feature_lead(feature_key: str) -> str:
    """기능에서 결론을 쥔 lead Agent intent를 반환한다(없으면 빈 문자열)."""
    entry = FEATURE_AGENT_POWER.get(str(feature_key or "").upper())
    if not entry:
        return ""
    return str(entry.get("lead") or "")


def agent_weight(feature_key: str, intent: str, default: float = 1.0) -> float:
    """특정 기능에서 특정 Agent의 가중치를 반환한다(없으면 default)."""
    weights = feature_weights(feature_key)
    if not weights:
        return default
    return float(weights.get(intent, default))
