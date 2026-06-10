# AI Mock Service

RabbitMQ request queue를 구독해서 백엔드 채팅 검증용 응답을 response queue로 돌려주는 mock 서비스다.

## 역할

- `chat.request` 소비
- 백엔드 `AiChatRequestMessage` envelope 해석
- `payload.featureContext`, `payload.resultContext`, `payload.profile` 기반 응답 생성
- 기능별 에이전트 진행 이벤트(`AGENT_EVENT`) 발행
- 최종 응답(`CHAT_RESPONSE`) 발행

## 지원 기능

- `ITEM`
- `SIMULATOR`
- `SUPPORT`
- `PLAN`
- `OPERATION`
- `SNS`
- `FREE_DISCUSSION`

기능 채팅에서는 현재 페이지 컨텍스트를 읽어서 summary, result payload, selected agent 목록이 달라진다.

예:
- `SUPPORT`: `supportSearchMode`, `userGoal`, `selectedSupportProgram`
- `PLAN`: `planGoal`, `focusedSection`
- `OPERATION`: `operationInput`, `operationReport`, `businessContext`
- `SNS`: `campaignDraft`, `campaignContext`

## 환경 변수

- `SPRING_RABBITMQ_HOST`
- `SPRING_RABBITMQ_PORT`
- `SPRING_RABBITMQ_USERNAME`
- `SPRING_RABBITMQ_PASSWORD`
- `STARTMATE_AI_CHAT_REQUEST_QUEUE`
- `STARTMATE_AI_CHAT_RESPONSE_QUEUE`
- `AI_MOCK_EVENT_DELAY_SECONDS`
