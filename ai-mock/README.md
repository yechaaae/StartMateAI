# AI Mock Service

RabbitMQ request queue를 구독해서 백엔드 채팅 검증용 응답을 response queue로 돌려주는 mock 서비스다.

## 역할

- `chat.request` 소비
- 요청 envelope/payload 읽기
- 기능별 mock 응답 생성
- `chat.response` 발행

## 환경 변수

- `SPRING_RABBITMQ_HOST`
- `SPRING_RABBITMQ_PORT`
- `SPRING_RABBITMQ_USERNAME`
- `SPRING_RABBITMQ_PASSWORD`
- `STARTMATE_AI_CHAT_REQUEST_QUEUE`
- `STARTMATE_AI_CHAT_RESPONSE_QUEUE`
