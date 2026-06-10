# StartMateAI Project Structure Handoff

이 문서는 StartMateAI를 이어서 작업하는 사람과 AI coding assistant가 프로젝트 구조를 빠르게 파악하도록 만든 최신 기준 문서입니다.

작업을 마친 AI 또는 작업자는 반드시 루트의 [CURRENT_STATUS.md](CURRENT_STATUS.md)를 갱신해야 합니다. 구조, API, 데이터 흐름, 실행 방식이 바뀌면 이 문서도 함께 갱신합니다.

## 1. 한 줄 구조

StartMateAI는 **프론트엔드 채팅 UI + Spring Boot 백엔드 데이터/API 허브 + RabbitMQ 기반 AI 멀티에이전트 worker**로 구성됩니다.

```text
frontend
  -> backend
     -> MySQL
     -> external public APIs
     -> RabbitMQ chat.request
        -> ai-worker
           -> backend internal AI tool APIs
        <- RabbitMQ chat.response
  <- chat response / SSE
```

해커톤 MVP 기준으로 외부 API key와 DB 접근은 백엔드가 담당합니다. AI 서버는 공공 API key를 직접 갖지 않고, 백엔드가 보내준 reference data 또는 백엔드 internal tool API 결과만 사용합니다.

## 2. 최상위 디렉토리

| 디렉토리 | 역할 | 먼저 볼 파일 |
| --- | --- | --- |
| `frontend/` | 사용자 화면, 채팅 진입점, 백엔드 API 호출 | `frontend/README.md`, `frontend/src/` |
| `backend/` | Spring Boot API, MySQL/JPA, 외부 API 수집, 지원사업/상권 추천, RabbitMQ 발행/수신 | `backend/src/main/java/com/kakao/backend/`, `backend/DATA_MVP_HANDOFF.md` |
| `ai/` | FastAPI 멀티에이전트, RabbitMQ worker, GMS/mock LLM, 백엔드 tool-call client | `ai/README.md`, `ai/app/agents/`, `ai/app/rabbitmq_worker.py` |
| `ai-mock/` | RabbitMQ mock AI worker. 실제 AI worker가 불안할 때만 사용 | `ai-mock/README.md` |

주의: `backend/DATA_MVP_HANDOFF.md`는 데이터 MVP 구현 당시의 상세 메모입니다. 현재는 AI 연결과 backend tool-call 구조가 추가되었으므로 최신 전체 구조는 이 문서를 기준으로 봅니다.

## 3. 서비스별 책임

### Frontend

- 사용자의 채팅 메시지와 기능별 화면 진입을 담당합니다.
- 백엔드의 채팅 API를 호출하고, 백엔드가 받은 AI 응답을 사용자에게 보여줍니다.
- SSE `agent-progress` 이벤트를 받아 Agent별 진행 로그를 임시 말풍선처럼 보여줍니다.
- 현재 AI가 어떤 데이터 근거를 썼는지 더 자세히 보여주려면 백엔드 응답의 `tool_calls`, `reference_data_used`, `evidence` 계열 데이터를 UI에 추가 노출하면 됩니다.

### Backend

- MySQL과 JPA entity를 소유합니다.
- K-Startup, 기업마당, 온통청년 같은 외부 공공 API key를 소유하고 호출합니다.
- 소상공인 상가 CSV/imported store 데이터를 저장하고 상권 경쟁점 수를 계산합니다.
- 채팅 요청을 RabbitMQ `chat.request`로 발행하고, AI 응답을 `chat.response`에서 받습니다.
- AI가 필요할 때 호출할 수 있는 internal tool API를 제공합니다.

중요 영역:

- `backend/src/main/java/com/kakao/backend/aichat/`: 채팅 요청 조립, RabbitMQ 발행/응답 처리, AI reference data 조립
- `backend/src/main/java/com/kakao/backend/policy/`: 지원사업 connector, normalizer, matcher, recommendation service
- `backend/src/main/java/com/kakao/backend/commercialarea/`: 상가 CSV import, 상권 분석, 경쟁점 계산
- `backend/src/main/java/com/kakao/backend/internal/`: AI internal tool API와 token 인증

### AI

- RabbitMQ worker가 `chat.request`를 consume하고, Orchestrator/개별 Agent를 실행한 뒤 `chat.response`로 publish합니다.
- Orchestrator/Agent 실행 중간 상태는 RabbitMQ `AGENT_EVENT`로 publish되고, 백엔드는 이를 SSE `agent-progress`로 프론트에 전달합니다.
- `PolicyAgent`는 지원사업 판단을 담당합니다.
- `CommercialAreaAgent`는 상권/입지/경쟁점 판단을 담당합니다.
- reference data가 없거나 사용자가 "최신", "지금 모집", "새 공고", "상권", "입지", "경쟁점"처럼 실시간성이 필요한 질문을 하면 deterministic tool-call 방식으로 백엔드 internal API를 호출합니다.
- 여기서 deterministic tool-call은 LLM provider의 native function calling이 아니라, Agent 코드가 조건을 보고 `BackendToolClient`를 호출하는 방식입니다.

중요 영역:

- `ai/app/rabbitmq_worker.py`: RabbitMQ request/response worker
- `ai/app/agents/orchestrator.py`: 사용자 의도 라우팅과 에이전트 조합
- `ai/app/agents/policy.py`: 지원사업 Agent
- `ai/app/agents/commercial_area.py`: 상권 Agent
- `ai/app/core/backend_tools.py`: 백엔드 internal tool API client

## 4. AI - 데이터 흐름

### 4.1 백엔드가 먼저 참고 데이터를 넣는 흐름

1. 사용자가 프론트에서 채팅합니다.
2. 백엔드가 채팅 메시지, 프로필, feature context를 기반으로 AI 요청 payload를 만듭니다.
3. 백엔드가 지원사업 추천 또는 상권 분석이 필요하다고 판단하면 `payload.reference.externalData`에 정규화된 결과를 넣습니다.
4. 백엔드가 RabbitMQ `chat.request`에 메시지를 발행합니다.
5. AI worker가 이 reference data를 우선 사용해 답변합니다.
6. AI worker가 RabbitMQ `chat.response`로 결과를 보냅니다.

이 방식은 시연 안정성이 좋습니다. 백엔드가 이미 추천/분석 결과를 같이 보내므로 AI가 추가 요청 없이 판단할 수 있습니다.

### 4.2 AI가 필요할 때 백엔드 tool을 호출하는 흐름

1. AI worker가 `chat.request`를 받습니다.
2. Agent가 reference data가 부족하거나 최신성이 필요하다고 판단합니다.
3. Agent가 `BackendToolClient`로 백엔드 internal API를 호출합니다.
4. 백엔드는 DB 또는 외부 API sync/fallback 데이터를 이용해 결과를 반환합니다.
5. Agent는 응답의 `data.tool_calls`, `data.reference_data_used`, `data.reference_sources`, `data.evidence`에 어떤 근거를 썼는지 남깁니다.

이 방식은 AI가 질문 맥락에 따라 능동적으로 필요한 데이터를 가져올 수 있게 합니다. 단, 공공 API key는 여전히 백엔드에만 있습니다.

### 4.3 Agent 진행 로그 흐름

1. AI worker가 `chat.request` 처리를 시작하면서 `orchestrator.started` 이벤트를 보냅니다.
2. Orchestrator가 선택된 Agent 목록을 `agents.selected` 이벤트로 보냅니다.
3. 각 Agent는 시작/완료 시 `agent.started`, `agent.completed` 이벤트를 보냅니다.
4. Orchestrator가 최종 합성 단계에서 `orchestrator.synthesizing`, `orchestrator.completed` 이벤트를 보냅니다.
5. 백엔드는 `AGENT_EVENT`를 `agent-progress` SSE로 변환하고, 프론트는 이를 실시간 진행 말풍선으로 표시합니다.

중간 이벤트는 해커톤 MVP 기준으로 히스토리에 저장하지 않고 실시간 표시용으로 사용합니다.

## 5. 주요 API

### 데모/사용자용 백엔드 API

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/api/seeds/import` | 지원사업/상권/Agent seed 데이터 import |
| `POST` | `/api/support-programs/sync?source=all` | K-Startup/기업마당/온통청년 sync, 실패 시 demo fallback |
| `POST` | `/api/support-programs/recommend` | 사용자 프로필 기반 지원사업 추천 |
| `POST` | `/api/stores/import-csv` | 소상공인 상가 CSV 또는 demo store import |
| `POST` | `/api/commercial-areas/analyze` | 지역/업종 기반 경쟁점 수 분석 |

### AI internal tool API

AI worker만 호출해야 하는 내부 API입니다.

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/api/internal/ai-tools/support-programs/sync` | 지원사업 데이터 sync |
| `POST` | `/api/internal/ai-tools/support-programs/recommend` | AI용 지원사업 추천 |
| `POST` | `/api/internal/ai-tools/commercial-areas/analyze` | AI용 상권 분석 |

내부 API는 `X-Startmate-Internal-Token` 헤더로 보호합니다. token 값은 문서나 코드에 직접 적지 말고 환경변수로만 관리합니다.

## 6. 환경변수 기준

실제 값은 문서에 쓰지 않습니다. 필요한 이름만 공유합니다.

### Backend

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
SPRING_JPA_HIBERNATE_DDL_AUTO
SPRING_RABBITMQ_HOST
SPRING_RABBITMQ_PORT
SPRING_RABBITMQ_USERNAME
SPRING_RABBITMQ_PASSWORD
STARTMATE_AI_CHAT_REQUEST_QUEUE
STARTMATE_AI_CHAT_RESPONSE_QUEUE
DATA_GO_KR_SERVICE_KEY
BIZINFO_API_KEY
YOUTH_CENTER_API_KEY
STARTMATE_INTERNAL_TOOL_TOKEN
```

### AI

```text
USE_MOCK_LLM
GMS_API_KEY
GMS_BASE_URL
GMS_CHAT_PATH
GMS_MODEL
GMS_API_KEY_HEADER
GMS_API_KEY_QUERY_PARAM
SPRING_RABBITMQ_HOST
SPRING_RABBITMQ_PORT
SPRING_RABBITMQ_USERNAME
SPRING_RABBITMQ_PASSWORD
STARTMATE_AI_CHAT_REQUEST_QUEUE
STARTMATE_AI_CHAT_RESPONSE_QUEUE
BACKEND_INTERNAL_BASE_URL
STARTMATE_INTERNAL_TOOL_TOKEN
BACKEND_TOOL_TIMEOUT_SECONDS
```

## 7. 실행과 테스트

전체 compose 실행:

```bash
docker compose up --build
```

기본 서비스:

- Frontend: `http://localhost`
- Backend: `http://localhost:8080`
- MySQL: `localhost:3306`
- RabbitMQ management: `http://localhost:15672`

백엔드 테스트:

```bash
cd backend
GRADLE_USER_HOME=/private/tmp/gradle ./gradlew test
```

AI 테스트:

```bash
cd ai
.venv/bin/python -m unittest discover -s tests
```

Compose 설정 검증:

```bash
docker compose config
```

## 8. AI 작업자가 지켜야 할 문서 규칙

모든 AI coding assistant와 작업자는 코드 작업 후 아래를 지킵니다.

1. `CURRENT_STATUS.md`를 반드시 갱신합니다.
2. 구조, API, 데이터 흐름, 실행 방법, 환경변수가 바뀌면 `PROJECT_STRUCTURE_HANDOFF.md`도 갱신합니다.
3. 실제 API key, token, password는 절대 문서에 쓰지 않습니다.
4. 작업 후 실행한 테스트와 실패한 테스트를 `CURRENT_STATUS.md`에 남깁니다.
5. 다음 작업자가 보면 좋은 파일과 남은 이슈를 `CURRENT_STATUS.md`에 남깁니다.
6. 해커톤 데모에 영향을 주는 변경이면 "데모 영향"을 짧게 적습니다.

## 9. 해커톤 기준 개선 제안

- 데모 직전 안정성을 위해 `seed import + support sync + demo store import`를 한 번에 실행하는 demo bootstrap endpoint나 스크립트가 있으면 좋습니다.
- AI 응답의 `tool_calls`, `reference_data_used`, `evidence`를 프론트에서 일부라도 보여주면 "실제 데이터를 보고 판단했다"는 근거가 분명해집니다.
- `backend/DATA_MVP_HANDOFF.md`와 `ai/README.md`는 각각 데이터 MVP/AI 서버 관점의 문서라서, 최신 전체 구조는 이 루트 문서로 연결해 두는 편이 좋습니다.
- 해커톤 이후에는 프로필 필드 정규화, 지원사업 자격 룰 추출, 대용량 CSV import 성능, 상권 benchmark 고도화를 분리해서 진행하면 됩니다.
