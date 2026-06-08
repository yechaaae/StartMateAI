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

`OrchestratorAgent`는 각 에이전트의 공통 필드를 모아 `agent_contracts`, `round1_synthesis`, `debate.agent_positions`를 만든다.

```text
ProfileAgent
IdeaAgent
PolicyAgent
FinanceAgent
MarketingAgent
OperationAgent
-> OrchestratorAgent
-> round1_synthesis + agent_contracts + debate + final decision
```

## 에이전트별 특화 필드

공통 필드 외에도 각 에이전트는 기존 특화 필드를 유지한다.

- `IdeaAgent`: `recommendations`, `ranking_basis`, `score_breakdown`, `matched_keywords`, `why_recommended`
- `PolicyAgent`: `matches`, `checklist`, `top_policy`, `score_breakdown`, `retrieval`, `source_chunks`, `eligibility_gaps`, `required_documents`, `application_strategy`
- `FinanceAgent`: `monthly_revenue_krw`, `break_even_units_per_day`, `what_if_scenarios`
- `SimulationAgent`: `session_id`, `current_event`, `metrics`, `history_tail`, `final_report`
- `MarketingAgent`: `reels_hook`, `storyboard_15s`, `caption`, `hashtags`, `upload_schedule`, `ab_test`
- `OperationAgent`: `detected_risks`, `recommended_actions`, `next_week_plan`

## Round 1 Synthesis

협업형 상담의 1차 라운드 결과는 `AgentResponse.data.round1_synthesis`에 들어간다.

```json
{
  "selected_direction": {
    "idea_title": "1순위 아이템",
    "policy_title": "1순위 지원사업",
    "decision": "2라운드로 넘길 기준 판단"
  },
  "agent_votes": [],
  "profile_snapshot": {},
  "top_idea": {},
  "top_policy": {},
  "round1_scores": {},
  "agreement": [],
  "tensions": [],
  "missing_inputs": [],
  "handoff_to_round2": []
}
```
