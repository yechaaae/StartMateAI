# Agent Debate Event Contract

AI worker can emit explicit debate events after selected agents finish their first analysis.

## Flow

1. `status`: routing or running state
2. `result`: each agent's initial analysis result
3. `argument`: each agent restates its position for the debate
4. `challenge`: one agent objects to another agent's position
5. `revision`: an agent revises its position after a challenge
6. `consensus`: Plan Agent summarizes the agreement
7. `final`: final `CHAT_RESPONSE`

## Event Types

- `argument`: first claim with evidence
- `challenge`: conflict or objection
- `revision`: revised opinion after objection
- `consensus`: final agreement before the final answer

These values are sent in:

- top-level `type`
- `payload.type`
- `payload.viewType`

## Example Challenge

```json
{
  "messageType": "AGENT_EVENT",
  "type": "challenge",
  "agent": "FinanceAgent",
  "summary": "재무 Agent -> 아이디어 Agent: 저는 이 지점에 이견이 있습니다...",
  "payload": {
    "eventType": "agent.challenge",
    "type": "challenge",
    "viewType": "challenge",
    "message": "재무 Agent -> 아이디어 Agent: 저는 이 지점에 이견이 있습니다...",
    "detail": {
      "type": "challenge",
      "source_intent": "finance",
      "target_intent": "idea",
      "issue": "현재 아이템/실행안은 재무 조건과 충돌합니다.",
      "basis": "월 손익 -566,400원, 손익분기 76개/day",
      "proposal": "아이디어를 유지하더라도 30일 MVP나 예약판매로 축소해야 합니다."
    }
  }
}
```

## Frontend Rendering Suggestion

- `status`: gray temporary progress text, do not persist as a normal chat bubble
- `argument`: normal agent bubble with lighter visual weight
- `challenge`: objection/conflict bubble, subtle warning tone
- `revision`: follow-up bubble from the challenged agent
- `consensus`: Plan Agent agreement bubble before final answer
- `final`: normal final AI answer

## Backend Notes

Do not drop `payload.detail`; the frontend can use it to render conflict arrows, evidence, and proposal chips.

Recommended progress DTO fields:

```java
String eventType;
String type;
String viewType;
String message;
ChatAgentDescriptorPayload agent;
List<ChatAgentDescriptorPayload> selectedAgents;
Map<String, Object> detail;
```
