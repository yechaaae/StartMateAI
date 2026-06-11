# Agent Event Type 연동 가이드

AI worker는 RabbitMQ 응답으로 최종 답변(`CHAT_RESPONSE`)과 진행 이벤트(`AGENT_EVENT`)를 보냅니다.

이 문서는 백엔드/프론트에서 에이전트 진행 이벤트를 채팅 UI에 다르게 표시하기 위한 계약입니다.

## 목표

현재 문제:

- `Plan Agent가 질문을 분석 중입니다`
- `Idea Agent가 탐색을 시작했습니다`
- `Finance Agent가 검토를 시작했습니다`

이런 진행 로그가 일반 답변 카드처럼 계속 남아서 대화가 지저분해 보입니다.

목표:

- 진행 중 상태는 회색 작은 글씨/typing 느낌으로 보여주고 필요하면 사라지게 처리
- 실제 에이전트 의견은 토론 발언처럼 남김
- 최종 답변은 일반 답변으로 크게 표시

## AI가 내려주는 타입

AI는 이벤트에 아래 필드를 추가합니다.

```json
{
  "type": "status"
}
```

동일한 값을 `payload.type`, `payload.viewType`, top-level `type`에도 넣습니다.

```json
{
  "messageType": "AGENT_EVENT",
  "type": "status",
  "payload": {
    "eventType": "agent.started",
    "type": "status",
    "viewType": "status"
  }
}
```

## 타입 종류

### `status`

진행 상태입니다. 채팅 답변 카드로 남기지 않는 것을 권장합니다.

예:

- 질문을 분석해서 필요한 Agent를 고르는 중입니다.
- 아이디어 Agent가 아이템 후보 탐색 관점에서 근거를 확인하는 중입니다.
- 최종 답변을 준비했습니다.

프론트 권장 표시:

- 회색 작은 텍스트
- typing indicator 근처
- 최신 status만 보여주거나 일정 시간 뒤 제거
- 대화 히스토리에 저장하지 않아도 됨

### `discussion`

오케스트레이터가 여러 에이전트 의견을 조율하는 중간 발언입니다.

예:

- 1차 의견을 합쳐 특정 아이템을 기준 후보로 검토합니다.
- 각 Agent 의견의 충돌 지점을 정리하고 최종 실행안을 합의합니다.

프론트 권장 표시:

- 일반 답변보다 작고 회색에 가까운 말풍선
- `Plan Agent` 또는 `Orchestrator` 이름으로 표시
- 남겨도 되지만 최종 답변보다 시각적 우선순위는 낮게

### `result`

개별 에이전트가 낸 실제 의견입니다.

예:

- 재무 관점에서는 초기 필요 현금과 손익분기점이 핵심입니다...
- 운영 관점에서는 품절 신호와 재고 누적 신호를 먼저 봐야 합니다...

AI는 `result` 메시지 본문에 가능한 경우 `판단 근거` 섹션을 함께 붙입니다.

예:

```text
재무 관점에서는 현재 조건에서 초기 비용을 줄이는 실행안이 필요합니다.

판단 근거
- 검토 점수 72점
- 초기 필요 현금 3,190,000원
- 월 예상 손익 -566,400원
- 손익분기 판매량 76개/day
```

프론트 권장 표시:

- 에이전트별 발언 카드로 남김
- `detail` 필드가 있으면 접힌 근거/리스크 영역으로 보여줄 수 있음

### `final`

최종 답변입니다.

예:

- `CHAT_RESPONSE`의 최종 `summary`

프론트 권장 표시:

- 일반 AI 답변 카드
- 가장 눈에 띄는 본문
- 저장/리포트화 대상

## AGENT_EVENT 예시

### status 예시

```json
{
  "messageType": "AGENT_EVENT",
  "type": "status",
  "agent": "IdeaAgent",
  "summary": "아이디어 Agent가 아이템 후보 탐색 관점에서 근거를 확인하는 중입니다.",
  "payload": {
    "eventType": "agent.started",
    "type": "status",
    "viewType": "status",
    "orchestrator": "OrchestratorAgent",
    "sequence": 3,
    "message": "아이디어 Agent가 아이템 후보 탐색 관점에서 근거를 확인하는 중입니다.",
    "agent": {
      "agentKey": "IdeaAgent",
      "label": "아이디어 Agent",
      "role": "아이템 후보 탐색",
      "status": "running"
    },
    "selectedAgents": [],
    "detail": {}
  }
}
```

### result 예시

```json
{
  "messageType": "AGENT_EVENT",
  "type": "result",
  "agent": "FinanceAgent",
  "summary": "재무 관점에서는 초기 필요 현금이 예산보다 크고, 손익분기 판매량을 먼저 낮춰야 합니다.",
  "payload": {
    "eventType": "agent.completed",
    "type": "result",
    "viewType": "result",
    "message": "재무 관점에서는 초기 필요 현금이 예산보다 크고, 손익분기 판매량을 먼저 낮춰야 합니다.",
    "agent": {
      "agentKey": "FinanceAgent",
      "label": "재무 Agent",
      "role": "비용/손익 검토",
      "status": "completed"
    },
    "detail": {
      "position": "초기 현금, 월 손익, 손익분기 판매량을 함께 봐야 합니다.",
      "score": 72,
      "evidence": {
        "monthly_profit_krw": -566400,
        "break_even_units_per_day": 76
      },
      "risks": [
        "월 예상 이익이 0 이하입니다.",
        "초기 필요 현금이 현재 예산을 초과합니다."
      ],
      "missingInputs": [
        "실제 임대료",
        "실제 원가율"
      ],
      "recommendation": "초기 비용을 줄이는 실행안으로 축소하세요."
    }
  }
}
```

### discussion 예시

```json
{
  "messageType": "AGENT_EVENT",
  "type": "discussion",
  "agent": "OrchestratorAgent",
  "summary": "각 Agent 의견의 충돌 지점을 정리하고 최종 실행안을 합의합니다.",
  "payload": {
    "eventType": "orchestrator.synthesizing",
    "type": "discussion",
    "viewType": "discussion",
    "message": "각 Agent 의견의 충돌 지점을 정리하고 최종 실행안을 합의합니다."
  }
}
```

### final 예시

최종 답변은 `messageType=CHAT_RESPONSE`입니다.

```json
{
  "messageType": "CHAT_RESPONSE",
  "type": "final",
  "agent": "OrchestratorAgent",
  "summary": "종합하면...",
  "payload": {
    "type": "final",
    "summary": "종합하면..."
  }
}
```

## 백엔드 작업 가이드

백엔드는 AI worker의 `AGENT_EVENT`를 받을 때 아래 값을 SSE payload로 전달하면 됩니다.

필수 전달:

- `payload.eventType`
- `payload.type`
- `payload.viewType`
- `payload.message`
- `payload.agent`
- `payload.selectedAgents`
- `payload.detail`
- `sequence`

권장 DTO 필드:

```java
public record ChatAgentProgressPayload(
    String requestId,
    String status,
    String targetFeature,
    String eventType,
    String type,
    String viewType,
    String orchestrator,
    Integer sequence,
    String message,
    ChatAgentDescriptorPayload agent,
    List<ChatAgentDescriptorPayload> selectedAgents,
    Map<String, Object> detail
) {}
```

하위 호환:

- `type`이 없으면 `eventType`으로 추론
- `agent.completed` -> `result`
- `orchestrator.synthesizing` -> `discussion`
- 그 외 진행 이벤트 -> `status`

## 프론트 작업 가이드

프론트는 `agent-progress` SSE를 받을 때 `type` 기준으로 처리합니다.

권장 로직:

```js
if (progress.type === 'status') {
  setCurrentStatus(progress)
  return
}

if (progress.type === 'discussion' || progress.type === 'result') {
  appendProgressMessage(progress)
}
```

렌더링 권장:

- `status`: 채팅 카드에 append하지 않음. 회색 작은 글씨 또는 typing row로 표시
- `discussion`: 낮은 강조도의 회색 발언 카드
- `result`: 에이전트별 의견 카드
- `final`: 최종 답변 카드

CSS 방향:

```css
.agent-progress-status {
  color: #8a94a6;
  font-size: 12px;
}

.chat-row.progress-discussion .chat-copy p {
  background: #f7f8fb;
  color: #667085;
}

.chat-row.progress-result .chat-copy p {
  background: #f5f6f9;
}
```

## 저장 정책 권장

대화 히스토리에 저장할 것:

- 사용자 메시지
- `CHAT_RESPONSE` final
- 필요하면 `result`

저장하지 않거나 임시 UI로만 둘 것:

- `status`
- typing 상태

`discussion`은 팀 UX 선택입니다. 회의 흐름을 보여주고 싶으면 저장하고, 최종 답변만 깔끔하게 남기고 싶으면 임시 표시로 처리해도 됩니다.
