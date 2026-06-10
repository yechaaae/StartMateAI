# StartMate AI Agent Notes

This file is for continuing AI-server work from another machine.

## Runtime

Run the AI API from this directory:

```powershell
cd c:\ssafy\해커톤\StartMateAI\ai
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Use `8001` for local testing. During recent work, port `8000` had an old `uvicorn --reload` process that kept serving stale code. If behavior differs by port, trust `8001` or fully kill/restart the old `8000` process.

Health check:

```text
http://127.0.0.1:8001/health
```

## Main Files

- `app/api/routes.py`
  - FastAPI endpoints.
  - `/ai/chat` returns full JSON response.
  - `/ai/chat/stream` returns NDJSON events used by the HTML test page.

- `app/agents/orchestrator.py`
  - Main agent router/orchestrator.
  - Current structure is intentionally close to future LangGraph nodes:
    - `_build_orchestration_state`
    - `plan_agents`
    - `_run_agents`
    - `_plan_followups`
    - `_synthesize_selective_response`
    - `_annotate_response`

- `app/agents/finance.py`
  - Finance simulation.
  - Calculates revenue, variable/fixed cost, BEP, initial cash, budget fit, scenarios, cash flow, and support handoff.

## Current Orchestration Design

The AI server does not always run every agent.

For `intent=auto`:

```text
User message
-> LLM planner selects minimal initial agents
-> selected agents run
-> follow-up planner checks results
-> additional agents run if needed
-> Orchestrator synthesizes final response
```

Example:

```text
구미에서 예산 300만원으로 수제 쿠키 팝업을 해보고 싶어.
객단가는 3500원 정도고 하루 40명 정도 팔 수 있을 것 같은데 재정적으로 가능할까?
```

Expected flow:

```text
FinanceAgent
-> funding/support need detected
-> PolicyAgent follow-up
-> OrchestratorAgent final selective_collaboration
```

Expected response metadata:

```json
{
  "intent": "selective_collaboration",
  "agent": "OrchestratorAgent",
  "data": {
    "collaboration_mode": "selective_dynamic_agents",
    "selected_intents": ["finance", "policy"],
    "selected_agents": ["FinanceAgent", "PolicyAgent"],
    "agent_plan": {
      "followups": ["policy"]
    }
  }
}
```

## Planner Behavior

`plan_agents()` uses the configured LLM first.

Fallback:

```text
_heuristic_agent_plan()
```

The heuristic is only a fallback for disabled/failed LLM planning.

Current legal/regulatory questions are mapped to `policy` because there is not yet a separate `LegalAgent`.

## Follow-Up Behavior

Currently generalized pipeline exists, but implemented follow-up rule is:

```text
FinanceAgent result
-> if funding_gap / support_handoff / risk C with negative profit
-> run PolicyAgent
```

Relevant helpers:

- `_plan_followups`
- `_should_follow_up_policy`
- `_policy_query_from_finance`
- `_finance_policy_trigger_reason`

Future improvement:

Replace the hardcoded finance-to-policy rule with an LLM follow-up planner that reads all agent results and returns additional agents.

## Finance Input Extraction

Finance requests extract assumptions from natural language before simulation.

Example fields:

- `item_name`
- `business_type`
- `sales_channel`
- `price_per_unit_krw`
- `expected_daily_customers`
- `operating_days_per_month`

LLM extraction is used first, with rule fallback.

Important fix:

`FinanceAgent` now respects explicit input fields via `model_fields_set`, so template defaults do not overwrite values like `price_per_unit_krw=3500` or `expected_daily_customers=40`.

## Test Pages

Test HTML files are outside the `StartMateAI` repo root:

```text
c:\ssafy\해커톤\startmate-chat-test.html
c:\ssafy\해커톤\multi-agent-test.html
```

Important current behavior:

- Default intent is `auto`.
- Default context is `{}`.
- `startmate-chat-test.html` prints a `Request Debug` message before sending:

```text
base=http://127.0.0.1:8001, intent=auto, context={}, session=...
```

If the page shows stale behavior:

1. Use `Ctrl + F5`.
2. Confirm Base URL is `http://127.0.0.1:8001`.
3. Click New Session.
4. Check the `Request Debug` line.

## Stream Event Note

For `selective_collaboration`, `/ai/chat/stream` must send full agent result data from `agent_results`, not just `agent_contracts`.

This matters because the test UI renders FinanceAgent details from fields like:

- `initial_cash_needed_krw`
- `monthly_profit_krw`
- `scenario_table`
- `budget_analysis`

If these appear as `-`, check `selective_agent_views()` in `app/api/routes.py`.

## Quick Verification

Run:

```powershell
cd c:\ssafy\해커톤\StartMateAI\ai
.\.venv\Scripts\python -m py_compile app\agents\orchestrator.py app\api\routes.py app\agents\finance.py
```

Then call `/ai/chat` with:

```json
{
  "intent": "auto",
  "message": "구미에서 예산 300만원으로 수제 쿠키 팝업을 해보고 싶어. 객단가는 3500원 정도고 하루 40명 정도 팔 수 있을 것 같은데 재정적으로 가능할까?",
  "profile": {
    "startup_stage": "예비창업",
    "risk_tolerance": "medium"
  }
}
```

Expected:

```text
FinanceAgent + PolicyAgent
intent=selective_collaboration
collaboration_mode=selective_dynamic_agents
```
