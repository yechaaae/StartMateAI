# Agent Output Contract

모든 에이전트는 `AgentResponse.data` 안에 아래 공통 필드를 포함한다.

```json
{
  "agent_contract_version": "1.0",
  "position": "이 에이전트의 핵심 판단",
  "evidence": "판단 근거",
  "score": 0,
  "risks": [],
  "assumptions": [],
  "missing_inputs": [],
  "recommendation": "다음 실행 제안"
}
```

## 필드 의미

- `position`: 에이전트의 관점에서 내린 한 줄 판단
- `evidence`: 판단에 사용한 근거. 리스트, 객체, 문자열 모두 가능
- `score`: 현재 판단의 적합도/확신도. 0~100
- `risks`: 주요 위험 요인
- `assumptions`: 계산/판단에 사용한 가정
- `missing_inputs`: 더 정확한 판단에 필요한 입력
- `recommendation`: 사용자가 다음에 해야 할 행동

## Orchestrator 사용 방식

`OrchestratorAgent`는 각 에이전트의 공통 필드를 모아 `agent_contracts`와 `debate.agent_positions`를 만든다.

```text
ProfileAgent
IdeaAgent
PolicyAgent
FinanceAgent
MarketingAgent
OperationAgent
-> OrchestratorAgent
-> agent_contracts + debate + final decision
```

## 에이전트별 특화 필드

공통 필드 외에도 각 에이전트는 기존 특화 필드를 유지한다.

- `IdeaAgent`: `recommendations`, `ranking_basis`
- `PolicyAgent`: `matches`, `checklist`, `top_policy`
- `FinanceAgent`: `monthly_revenue_krw`, `break_even_units_per_day`, `what_if_scenarios`
- `SimulationAgent`: `session_id`, `current_event`, `metrics`, `history_tail`, `final_report`
- `MarketingAgent`: `reels_hook`, `storyboard_15s`, `caption`, `hashtags`, `upload_schedule`, `ab_test`
- `OperationAgent`: `detected_risks`, `recommended_actions`, `next_week_plan`
