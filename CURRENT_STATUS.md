# StartMateAI Current Status

이 문서는 사람이 바로 읽는 현재 상태 요약본입니다.

AI coding assistant 또는 작업자가 코드 작업을 마치면 이 문서를 반드시 갱신합니다. 구조나 데이터 흐름이 바뀐 경우 [PROJECT_STRUCTURE_HANDOFF.md](PROJECT_STRUCTURE_HANDOFF.md)도 함께 갱신합니다.

## 1. 현재 상태 요약

- 프로젝트는 해커톤 MVP 기준으로 `frontend`, `backend`, `ai`, `ai-mock`으로 나뉩니다.
- 백엔드는 MySQL/JPA 기반으로 지원사업 데이터와 상권 데이터를 저장하고 추천/분석 API를 제공합니다.
- AI는 RabbitMQ worker로 백엔드 채팅 요청을 받아 멀티에이전트 판단을 수행합니다.
- 지원사업과 상권 판단은 두 가지 방식으로 AI에 전달됩니다.
  - 백엔드가 채팅 요청 payload에 `reference.externalData`로 미리 넣어 전달
  - AI Agent가 필요할 때 백엔드 internal tool API를 직접 호출
- 외부 공공 API key는 백엔드가 소유합니다. AI는 공공 API를 직접 호출하지 않습니다.

## 2. 구현된 주요 기능

### 지원사업 데이터

- K-Startup, 기업마당, 온통청년 connector 기반 sync 구조가 있습니다.
- API key가 없거나 외부 API가 불안정해도 demo fallback 데이터로 시연할 수 있습니다.
- 지원사업 공고는 공통 형태로 normalize되어 MySQL에 저장됩니다.
- 사용자 프로필 기반 추천은 `matchScore`, `matchReasons`, `cautionReasons`를 반환합니다.
- 추천은 "지원 가능 확정"이 아니라 "가능성/주의사항" 기준입니다.

### 상권 데이터

- 소상공인 상가 CSV 또는 ZIP 파일 import 구조가 있습니다.
- `filePath`가 비어 있거나 파일이 없으면 demo store fallback으로 동작합니다.
- 지역/업종 기준으로 전체 점포 수, 직접 경쟁점 수, 유사 경쟁점 수, 경쟁 강도를 계산합니다.
- 해커톤 MVP 기준 경쟁 강도는 단순 룰입니다.
  - `directCompetitors <= 5`: `low`
  - `directCompetitors <= 20`: `medium`
  - 그 이상: `high`

### AI 연동

- 백엔드는 RabbitMQ `chat.request`로 AI 요청을 발행합니다.
- AI worker는 요청을 consume하고 `chat.response`로 결과를 publish합니다.
- `PolicyAgent`는 지원사업 reference data 또는 backend support tool 결과를 사용합니다.
- `CommercialAreaAgent`는 상권 reference data 또는 backend commercial area tool 결과를 사용합니다.
- AI 응답 data에는 데이터 사용 근거가 남습니다.
  - `reference_data_used`
  - `reference_sources`
  - `tool_calls`
  - `evidence`

## 3. 주요 실행 흐름

### 외부 API sync 흐름

```text
Backend
  -> K-Startup / Bizinfo / YouthCenter
  -> normalize
  -> MySQL support_programs
  -> recommend API or AI internal tool API
```

외부 API 호출이 실패하거나 key가 없으면 demo fallback으로 최소 시연 데이터가 들어갑니다.

### 상권 import/analyze 흐름

```text
Backend
  -> SBIZ CSV or ZIP import
  -> MySQL stores
  -> commercial area analyze
  -> AI reference data or internal tool response
```

### 채팅에서 AI가 데이터를 쓰는 흐름

```text
Frontend
  -> Backend chat API
  -> RabbitMQ chat.request
  -> AI worker
     -> use reference.externalData if present
     -> call backend internal tool API if needed
  -> RabbitMQ chat.response
  -> Backend
  -> Frontend
```

## 4. 현재 주요 API

### 데모/사용자용

```text
POST /api/seeds/import
POST /api/support-programs/sync?source=all
POST /api/support-programs/recommend
POST /api/stores/import-csv
POST /api/commercial-areas/analyze
```

### AI internal tool

```text
POST /api/internal/ai-tools/support-programs/sync
POST /api/internal/ai-tools/support-programs/recommend
POST /api/internal/ai-tools/commercial-areas/analyze
```

Internal tool API는 `X-Startmate-Internal-Token` 헤더가 필요합니다.

## 5. 필요한 환경변수

실제 값은 이 문서에 쓰지 않습니다.

### 필수 또는 데모 핵심

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
SPRING_RABBITMQ_HOST
SPRING_RABBITMQ_PORT
SPRING_RABBITMQ_USERNAME
SPRING_RABBITMQ_PASSWORD
STARTMATE_INTERNAL_TOOL_TOKEN
BACKEND_INTERNAL_BASE_URL
```

### 외부 API

```text
DATA_GO_KR_SERVICE_KEY
BIZINFO_API_KEY
YOUTH_CENTER_API_KEY
```

### AI/GMS

```text
USE_MOCK_LLM
GMS_API_KEY
GMS_BASE_URL
GMS_CHAT_PATH
GMS_MODEL
GMS_API_KEY_HEADER
GMS_API_KEY_QUERY_PARAM
BACKEND_TOOL_TIMEOUT_SECONDS
```

## 6. 데모 실행 순서

1. `.env`에 필요한 환경변수 이름을 준비합니다. secret 값은 공유 문서에 적지 않습니다.
2. 전체 서비스를 실행합니다.

```bash
docker compose up --build
```

3. 필요하면 seed 데이터를 넣습니다.

```http
POST /api/seeds/import
```

4. 지원사업 데이터를 sync합니다.

```http
POST /api/support-programs/sync?source=all
```

5. 상권 CSV를 import하거나 demo fallback을 사용합니다.

```http
POST /api/stores/import-csv
```

6. 채팅에서 아래처럼 질문합니다.

```text
서울 마포구 연남동에서 카페 창업하려고 하는데 지금 지원사업이랑 상권 경쟁점 봐줘
```

기대 결과:

- 지원사업 추천이 반환됩니다.
- 상권 경쟁점 수와 경쟁 강도가 반환됩니다.
- AI 응답 data에 `reference_data_used=true` 또는 tool-call evidence가 남습니다.

## 7. 최근 브랜치/PR 기준 변경 요약

현재 작업 기준 브랜치:

```text
feature/ai/backend-tool-calls
```

최근 큰 변경:

- 백엔드 internal AI tool API 추가
- AI `BackendToolClient` 추가
- `PolicyAgent`가 최신/모집중 지원사업 요청에서 백엔드 support tool을 호출
- `CommercialAreaAgent`가 reference data가 없을 때 백엔드 상권 tool을 호출
- AI 응답에 `tool_calls`, `reference_data_used`, `reference_sources`, `evidence` 근거를 남김
- compose 기본 AI 연결을 `ai-worker` 중심으로 구성하고 `ai-mock`은 mock profile로 분리

## 8. 테스트 상태

최근 기준으로 확인된 테스트 명령:

```bash
cd backend
GRADLE_USER_HOME=/private/tmp/gradle ./gradlew test
```

```bash
cd ai
.venv/bin/python -m unittest discover -s tests
```

```bash
docker compose config
```

이 문서를 수정하는 작업 자체는 코드 변경이 아니므로 별도 애플리케이션 테스트는 필수는 아닙니다. 다만 코드나 compose를 함께 바꿨다면 위 명령을 다시 실행하고 결과를 이 섹션에 갱신해야 합니다.

## 9. 알려진 제한사항

- `backend/DATA_MVP_HANDOFF.md`에는 AI 직접 연결 전 설명이 남아 있습니다. 최신 전체 구조는 루트의 `PROJECT_STRUCTURE_HANDOFF.md`와 이 문서를 기준으로 봅니다.
- LLM provider native function calling은 붙이지 않았습니다. 현재는 Agent 코드가 조건을 보고 백엔드 tool client를 호출하는 deterministic tool-call 방식입니다.
- 지원사업 자격 판단은 단순 룰 기반입니다. 법적/행정적 자격 확정으로 표현하면 안 됩니다.
- 상권 경쟁 강도는 업종별 benchmark가 아니라 단순 점포 수 기준입니다.
- 대용량 CSV import는 해커톤 데모 기준입니다. 운영 환경에서는 batch 처리, 진행률, 실패 row 리포트가 필요합니다.
- AI가 사용한 evidence를 프론트에서 얼마나 보여주는지는 추가 작업이 필요합니다.

## 10. 다음 작업 추천

- 데모 안정성을 위해 `seed import + support sync + demo store import`를 묶는 bootstrap endpoint 또는 스크립트를 추가합니다.
- 프론트 채팅 응답에 `reference_data_used`, `tool_calls`, `evidence` 일부를 보여줍니다.
- `ai/README.md`에 RabbitMQ worker와 backend tool-call 설명을 보강합니다.
- `backend/DATA_MVP_HANDOFF.md` 상단에 "구 데이터 MVP 문서이며 최신 구조는 루트 문서 참고" 안내를 추가합니다.
- 프로필 입력값을 지원사업 matcher와 상권 analyzer가 더 잘 쓰도록 필드 정규화를 보강합니다.

## 11. AI 작업 후 갱신 체크리스트

AI coding assistant 또는 작업자는 작업 종료 전에 아래 항목을 채워 이 섹션을 갱신합니다.

```text
작업일:
작업자:
이번 작업 요약:
수정한 주요 영역:
추가/변경된 API:
추가/변경된 환경변수:
실행한 테스트:
실패한 테스트와 이유:
데모 영향:
깨질 수 있는 부분:
다음 사람이 보면 좋은 파일:
아직 안 한 일:
```

문서만 수정한 경우에도 "이번 작업 요약"과 "실행한 테스트"는 남깁니다.

## 12. 마지막 문서 갱신 기록

```text
작업일: 2026-06-10
작업자: Codex
이번 작업 요약: 프로젝트 구조 핸드오프 문서와 현재 상태 요약본 작성
수정한 주요 영역: 루트 문서
추가/변경된 API: 없음
추가/변경된 환경변수: 없음
실행한 테스트: 문서 변경만 수행하여 애플리케이션 테스트는 실행하지 않음
실패한 테스트와 이유: 없음
데모 영향: 팀원이 AI-백엔드 데이터 흐름과 데모 실행 순서를 빠르게 파악 가능
깨질 수 있는 부분: 없음
다음 사람이 보면 좋은 파일: PROJECT_STRUCTURE_HANDOFF.md, backend/DATA_MVP_HANDOFF.md, ai/README.md
아직 안 한 일: 기존 세부 문서의 최신 구조 반영은 후속 작업으로 남김
```
