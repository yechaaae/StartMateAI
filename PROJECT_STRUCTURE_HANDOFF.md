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

### 2.1 백엔드 모듈 전체 (실제 기준)

초기 문서는 `policy`, `commercialarea`, `internal`, `aichat`만 설명했지만 실제 백엔드에는 아래 모듈이 더 있습니다.

| 모듈 | 역할 |
| --- | --- |
| `auth`, `user` | 회원가입/로그인/세션, 사용자 |
| `workspace` | 워크스페이스(사용자별 작업 공간) |
| `startupProfile` | 창업 프로필 입력/조회 |
| `chat` | 채팅방, 메시지, SSE 스트림, 요청 상태(`ChatRequestStatus`) |
| `aichat` | 채팅 요청 조립, RabbitMQ 발행/응답, reference data 조립 |
| `policy` | 지원사업 connector/normalize/matcher/recommend |
| `commercialarea` | 상가 CSV import, 상권/경쟁점 분석, 임대료(rent) 추정 |
| `idea`, `plan`, `marketing`, `operation`, `simulation` | 기능별 리포트/피드백 도메인 (아이템·사업계획·홍보·운영·시뮬레이션) |
| `agent` | Agent 결과/메타 도메인 |
| `seed` | 데모/시드 데이터 import |
| `internal` | AI internal tool API + 토큰 인증 |
| `common` | 공통 유틸/예외 |

프론트엔드 `frontend/src/features/`는 `chat`, `reports`, `simulator`, `layout`, `pages`로 구성됩니다.

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
- Orchestrator에 등록된 Agent는 총 10개입니다: `ProfileAgent`, `IdeaAgent`, `PolicyAgent`, `PlanAgent`, `LegalAgent`, `FinanceAgent`, `OperationAgent`, `MarketingAgent`, `CommercialAreaAgent`, `SimulationAgent`.
  - `PolicyAgent`: 지원사업 추천/판단, `CommercialAreaAgent`: 상권/입지/경쟁점, `LegalAgent`: 법률 체크리스트(RAG), `FinanceAgent`: 비용/손익, 나머지는 아이템·사업계획·운영·마케팅·시뮬레이션 검토.
- Agent 선택(라우팅)은 현재 **한국어 키워드 매칭 휴리스틱**이 1차이고, 모호하면 LLM planner로 폴백합니다(LLM 비활성 시 키워드가 최종). `orchestrator.py`의 intent별 키워드 목록 참고.
- Agent들은 wave 단위로 **병렬(asyncio) 독립 실행**되며, 그 뒤 Orchestrator가 결과를 합성합니다. 합성/“토론(debate)”은 별도 LLM 호출이 아니라 사전 정의된 challenge 규칙 + 일부 **고정 문구**로 구성됩니다(`orchestrator._revision_message`). 즉 실시간 다중턴 토론이 아니라 진행/요약 표시에 가깝습니다.
- reference data가 없거나 사용자가 "최신", "지금 모집", "새 공고", "상권", "입지", "경쟁점"처럼 실시간성이 필요한 질문을 하면 deterministic tool-call 방식으로 백엔드 internal API를 호출합니다.
- 여기서 deterministic tool-call은 LLM provider의 native function calling이 아니라, Agent 코드가 조건을 보고 `BackendToolClient`를 호출하는 방식입니다.
- RAG: `PolicyAgent`/`LegalAgent`가 retriever를 사용하지만, 기본 임베딩은 의미 임베딩이 아닌 해시 기반(`HashEmbeddingProvider`)입니다. 실제 의미 검색을 쓰려면 GMS 임베딩 provider를 명시 설정해야 합니다.

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

### 인증/사용자

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/api/auth/signup`, `/login`, `/logout` | 회원가입/로그인/로그아웃 |
| `GET` | `/api/auth/me` | 현재 사용자 |
| `GET` | `/api/profile/status` | 프로필 작성 상태 |

### 채팅 (핵심 플로우)

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/api/chat/free-rooms`, `/feature-rooms` | 자유/기능 채팅방 생성 |
| `GET` | `/api/chat/free-room`, `/feature-room`, `/free-rooms`, `/feature-rooms` | 채팅방 조회 |
| `POST` | `/api/chat/rooms/{roomId}/messages` | 메시지 전송 → AI 요청 발행 |
| `GET` | `/api/chat/rooms/{roomId}/messages` | 메시지 히스토리 |
| `GET` | `/api/chat/rooms/{roomId}/stream` | SSE 구독(메시지/상태/`agent-progress`) |

### 데모/사용자용 데이터 API

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/api/seeds/import` | 지원사업/상권/Agent seed 데이터 import |
| `POST` | `/api/support-programs/sync?source=all` | K-Startup/기업마당/온통청년 sync, 합계 0이면 demo fallback |
| `POST` | `/api/support-programs/recommend` | 사용자 프로필 기반 지원사업 추천 |
| `POST` | `/api/stores/import-csv` | 소상공인 상가 CSV 또는 demo store import |
| `POST` | `/api/commercial-areas/analyze` | 지역/업종 기반 경쟁점 수 분석 |
| `POST` | `/api/rent-references/import-csv` | 임대료 참고 데이터 import |
| `GET` | `/api/rent-references/estimate` | 임대료 추정 |

### 기능별 리포트/연동

| Method | Path | 역할 |
| --- | --- | --- |
| `*` | `/api/operation-feedback` | 운영 피드백 |
| `*` | `/api/v1/simulations` | 창업 시뮬레이션 |
| `GET` | `/api/saved-results/latest`, `/{savedResultId}` | 저장된 결과 조회 |
| `*` | `/api/sns/threads/*` | Meta Threads 연동(연결/발행/로그 등) |

### AI internal tool API

AI worker만 호출해야 하는 내부 API입니다.

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/api/internal/ai-tools/support-programs/sync` | 지원사업 데이터 sync |
| `POST` | `/api/internal/ai-tools/support-programs/recommend` | AI용 지원사업 추천 |
| `GET` | `/api/internal/ai-tools/support-programs` | 지원사업 목록 |
| `POST` | `/api/internal/ai-tools/commercial-areas/analyze` | AI용 상권 분석 |
| `POST` | `/api/internal/ai-tools/commercial-areas/rent-estimate` | AI용 임대료 추정 |

내부 API는 `X-Startmate-Internal-Token` 헤더로 보호합니다. token 값은 문서나 코드에 직접 적지 말고 환경변수로만 관리합니다. 현재 코드는 미설정 토큰을 기본값(`startmate-local-internal-token`)으로 두므로 운영에서는 반드시 override해야 합니다.

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

## 10. 해커톤 데모 흐름 (인지적 완성도 중심)

이 섹션은 **실 성능보다 "보는 사람이 잘 만들어졌다고 느끼게"** 하는 데 초점을 둔 데모 연출 가이드입니다. 즉, 가장 강하게 동작하는 실제 경로(골든 패스) 위에서 진행/근거/협업을 또렷하게 보여주는 무대 연출입니다. 시스템의 실제 한계와 리스크는 [CURRENT_STATUS.md](CURRENT_STATUS.md) §9에 정직하게 적어 두었으니, 팀은 "데모용 연출"과 "실제 한계"를 분리해서 인지해야 합니다.

### 10.1 인지적으로 가장 강한 무기 3개

1. **실시간 Agent 진행 말풍선(SSE `agent-progress`)** — 가장 강력한 시각 요소. Orchestrator가 Agent를 고르고, 각 Agent가 "검토 시작 → 완료"되는 과정이 순차적으로 떠서 "여러 AI가 실제로 일하고 있다"는 인상을 줍니다.
2. **협업/토론 연출** — Agent들이 서로 지적하고 보완하는 `discussion → argument → challenge → revision → consensus` 흐름. 내부적으로는 일부 고정 로직이지만, 화면상으로는 "에이전트들이 교차 검증한다"로 읽힙니다.
3. **데이터 근거 노출** — `reference_data_used`, `tool_calls`, `evidence`, 지원사업/상권 수치를 카드로 보여주면 "실제 공공데이터를 보고 판단했다"는 신뢰감을 줍니다.

### 10.2 골든 패스 질문 (검증된 트리거)

아래 질문은 코드의 하드코딩 매칭이 **전부 명중**하도록 골라, 모든 패널이 데이터로 채워지고 협업/근거가 동시에 보이게 합니다.

- **데이터 그라운딩 강조용**
  > 서울 마포구 연남동에서 카페 창업하려는데 지금 받을 수 있는 지원사업이랑 주변 상권 경쟁점 분석해줘
  - "지원사업" → PolicyAgent + 지원사업 reference 첨부
  - "상권/경쟁점/카페/연남동/마포" → CommercialAreaAgent + 상권 reference 첨부
  - 업종 "카페" → 음식점업/커피점/카페로 정확히 매핑, 지역 서울·마포구·연남동 명중
- **멀티에이전트 협업 강조용 (collaboration 모드)**
  > 연남동 카페 창업 전체 로드맵 짜줘  /  연남동 카페 창업 전체적으로 상담해줘
  - `로드맵 / 전체 / 상담 / 협업 / 토론 / 시작` 키워드 또는 `intent=roadmap` → **collaboration 모드**로 다수 Agent가 동시에 붙고 토론 단계까지 진행되어 화면이 가장 풍부해짐

### 10.3 트리거 키워드 (라이브에서 벗어나지 말 것)

| 보이고 싶은 것 | 명중 키워드 (이 안에서만 말하기) |
| --- | --- |
| 지원사업 reference | 지원사업, 공고, 정책, 사업화, 멘토링, 교육, 창업지원 |
| 상권 reference | 상권, 입지, 경쟁, 경쟁점, 주변, 카페, 연남동, 마포구 |
| 업종 인식 | 카페, 커피, 음식, 식당, 디저트 |
| 지역 인식 | 서울(기본), 마포, 연남 |
| 협업/토론 모드 | 로드맵, 전체, 상담, 협업, 토론, 시작 |

### 10.4 데모 전 부트스트랩 체크리스트 (빈 화면 제거)

빈 패널은 완성도를 가장 크게 깎습니다. 데모 직전 아래를 순서대로 실행해 데이터를 채워 둡니다.

1. `POST /api/seeds/import`
2. `POST /api/support-programs/sync?source=all` — 키가 없어도 demo fallback로 채워짐
3. `POST /api/stores/import-csv` — 파일 없으면 연남동 demo store로 채워짐
4. 골든 패스 질문을 **리허설로 1회** 던져 SSE 진행/토론/근거가 모두 뜨는지 확인

### 10.5 발표 스크립트 (약 3~4분)

1. (10초) 프로필이 채워진 상태로 시작 — 빈 입력 화면을 보여주지 않음.
2. (20초) 골든 패스 질문을 입력. **진행 말풍선이 하나씩 뜨는 구간을 일부러 천천히 짚어가며** "지금 Orchestrator가 필요한 Agent를 고르고, 지원사업·상권 Agent가 각각 검토에 들어갑니다"라고 내레이션.
3. (40초) 협업/토론 단계(challenge→revision→consensus)를 가리키며 "에이전트들이 서로 걸리는 부분을 맞춰갑니다"로 설명.
4. (30초) 근거 카드(지원사업 매칭 점수, 상권 경쟁점 수/강도, evidence)를 보여주며 "실제 공공데이터 기반"임을 강조.
5. (20초) collaboration 모드 질문("전체 로드맵")으로 한 번 더, 더 많은 Agent가 동시에 붙는 장면으로 마무리.

### 10.6 라이브에서 피해야 할 입력 (한계 노출 방지)

- **비-카페 업종 / 비-서울 지역** (예: "부산에서 미용실") → 지역·업종 파싱이 비어 reference 패널이 빈다.
- **네트워크 끊김 / GMS 지연** → 재시도가 없어 그대로 실패로 보인다. 데모망은 안정 회선으로.
- **초고속 연속 질문 / 매우 긴 메시지** → LLM 호출이 쌓이고 worker 타임아웃이 없어 멈춘 듯 보일 수 있다. 한 번에 하나씩, 응답을 보고 다음을 던진다.
- **임의 즉흥 질문** → §10.3 키워드 밖으로 나가면 라우팅이 흔들린다. 시연은 검증된 질문 세트 안에서만.

### 10.7 연출 디테일 팁

- 진행 단계가 너무 빨리 지나가면 인지가 안 된다. 화면을 키우고, 진행 말풍선이 보이는 동안 말로 짚어준다.
- "지원사업 N건 / 경쟁점 N개 / 경쟁강도" 같은 **숫자**를 입으로 읽어주면 데이터 기반 인상이 강해진다.
- 토론 단계는 새로고침해도 남는 타입(`discussion/result/argument/challenge/revision/consensus`)이므로, 미리 한 번 돌려 둔 방을 띄워 두면 안전판이 된다(라이브 호출이 느릴 때 대비).
