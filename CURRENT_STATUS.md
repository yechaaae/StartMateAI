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
- AI worker는 Orchestrator/Agent 진행 상황을 `AGENT_EVENT`로 함께 publish합니다.
- 백엔드는 `AGENT_EVENT`를 SSE `agent-progress`로 변환하고, 프론트는 진행 말풍선/typing 상태로 표시합니다.
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
     -> publish AGENT_EVENT progress logs
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
- AI worker가 Orchestrator/Agent 진행 로그를 `AGENT_EVENT`로 publish
- 프론트가 상권/법률 Agent progress 이벤트를 올바른 Agent로 매핑
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
- Agent 간 완전한 다중 턴 토론은 아닙니다. 현재는 Orchestrator가 선택한 Agent들의 시작/완료/요약 진행 로그를 실시간으로 보여주는 구조입니다.
- 지원사업 자격 판단은 단순 룰 기반입니다. 법적/행정적 자격 확정으로 표현하면 안 됩니다.
- 상권 경쟁 강도는 업종별 benchmark가 아니라 단순 점포 수 기준입니다.
- 대용량 CSV import는 해커톤 데모 기준입니다. 운영 환경에서는 batch 처리, 진행률, 실패 row 리포트가 필요합니다.
- AI가 사용한 evidence를 프론트에서 얼마나 보여주는지는 추가 작업이 필요합니다.

### 2026-06-13 코드 점검에서 추가로 확인된 제한사항 (검증됨)

- **AI worker 전체 타임아웃 없음**: `ai/app/rabbitmq_worker.py`의 `orchestrator.run(...)`이 타임아웃 없이 await되고 `prefetch_count=1`이라, LLM 호출 한 번이 hang하면 큐 전체가 그 메시지에 막힙니다.
- **백엔드 stuck-request 스윕 없음**: AI가 응답을 끝내 publish하지 않으면 `ChatRequestStatus`가 QUEUED/PROCESSING에 고정되어, 프론트 스피너가 SSE 1시간 타임아웃까지 안 풀립니다. `@Scheduled` 타임아웃 처리가 없습니다.
- **GMS 호출 재시도 없음**: `ai/app/core/gms_client.py`는 단일 요청 후 `raise_for_status()`만 합니다. GMS 지연/오류 시 그대로 실패합니다.
- **에이전트 "토론"은 일부 고정 문구**: `orchestrator._revision_message`가 challenge 시 LLM이 아니라 하드코딩 문구를 반환합니다. 실시간 다중턴 토론으로 설명하면 과장입니다.
- **의도 라우팅이 키워드 하드코딩**: 동의어/의역("초기자금" 등)에 취약하고, "상권 진입 비용" 같은 표현은 오분류될 수 있습니다.
- **외부 데이터 호출이 채팅 전송 경로에서 동기·무방비**: `AiChatExternalReferenceDataService.resolve()`가 try/catch·타임아웃 없이 추천/상권 분석을 동기 호출합니다. 외부 호출이 느리거나 예외면 해당 채팅 턴이 지연·실패합니다.
- **지역/업종 파싱이 카페·서울에 편향**: 위 서비스의 업종은 "카페/커피/음식"만 인식(나머지 null), 지역 기본값은 "서울"+마포/연남만 처리합니다. 다른 업종·지역은 reference data가 비게 됩니다.
- **커넥터 페이지네이션 없음**: K-Startup/기업마당/온통청년 모두 1페이지·100건 고정이라 100건 초과분은 수집되지 않습니다.
- **데모 폴백이 실제 데이터를 가립니다**: 3개 소스 합계가 0이면 데모 4건이 주입됩니다(`SupportProgramService` `totalUpserted == 0`). 키 없는 개발환경에선 항상 데모로 동작합니다.
- **추천 매칭이 `String.contains` 점수**: 제목에 "청년"만 있어도 나이와 무관하게 가점됩니다. 실제 자격 판정이 아닙니다. 추천도 `findAll()` 전체 스캔 후 자바에서 정렬합니다.
- **RAG 기본 임베딩이 가짜**: 기본값이 해시 버킷 임베딩(`HashEmbeddingProvider`)이라 의미 유사도가 아닙니다. GMS 임베딩 provider를 명시해야 실제 의미 검색이 됩니다.
- **내부 토큰 약한 기본값**: `InternalToolAuthService`가 기본 토큰을 코드에 두고 `.equals()`(상수시간 아님)로 비교합니다. 운영에서 override 필수.
- **프론트 SSE 재연결 무한 고정 간격**: 1.2초 간격 무한 재시도(지수 백오프·하트비트 없음).

## 10. 다음 작업 추천 (2026-06-13 점검 기준, 우선순위)

### 🔴 치명 — 데모/운영 중 사용자 무한 대기 차단

1. AI worker에 전체 타임아웃 추가: `asyncio.wait_for(orchestrator.run(...), timeout=N)`, 초과 시 FAILED 응답 publish. (`ai/app/rabbitmq_worker.py`)
2. 백엔드 stuck-request 스윕: `@Scheduled`로 일정 시간(예: 5분) 초과 QUEUED/PROCESSING을 `markFailed` + SSE 통지.
3. GMS 호출 재시도+백오프 추가, 실패 로깅. (`ai/app/core/gms_client.py`)

### 🟠 높음 — 안정성·활용도

4. 채팅 전송 경로의 외부 데이터 호출을 try/catch + 타임아웃으로 격리(실패 시 빈 externalData). (`AiChatExternalReferenceDataService`)
5. 커넥터 페이지네이션 구현(100건 상한 제거).
6. 업종·지역 파싱 일반화(카페·서울·연남 하드코딩 탈피, 매핑 테이블화).
7. worker `prefetch_count` 상향/동시처리 또는 worker 다중화.
8. 내부 토큰 하드코딩 기본값 제거 + `MessageDigest.isEqual` 상수시간 비교.

### 🟡 중간 — 품질·신뢰성

9. "토론" 답변을 LLM 생성으로 교체하거나, 최소한 고정 문구임을 명시. (`orchestrator._revision_message`)
10. 의도 라우팅을 경량 LLM 분류로 보강(키워드는 폴백).
11. 합성 단계에 모순 탐지(예: finance 자금부족 vs policy 적합없음 충돌 표시).
12. 추천 매칭을 실제 자격 룰로 정교화 + `findByStatus("open")` DB 필터/인덱스.
13. CSV import 배치화(N+1 제거, `saveAll`).
14. RAG 기본 임베딩을 실제 임베딩으로 교체.
15. AI 측 HTTP 클라이언트(`BackendToolClient` 등) 세션 재사용.

### 🟢 낮음 — UX·운영

16. Agent progress 이벤트 저장/리플레이로 새로고침 후 복원.
17. 프론트 SSE 재연결 지수 백오프 + 하트비트.
18. 채팅 히스토리 페이지네이션.
19. 외부/내부 API 호출 구조적 로깅(현재 조용히 빈 리스트 반환).
20. 데모 부트스트랩 엔드포인트(`seed import + support sync + demo store import` 일괄).

### 문서/기존 후속

- 프론트 채팅 응답에 `reference_data_used`, `tool_calls`, `evidence` 일부를 근거 패널로 노출.
- `ai/README.md`에 RabbitMQ worker와 backend tool-call 설명 보강.
- `backend/DATA_MVP_HANDOFF.md` 상단에 "구 데이터 MVP 문서, 최신 구조는 루트 문서 참고" 안내 추가.
- 프로필 입력값을 matcher/analyzer가 더 잘 쓰도록 필드 정규화 보강.

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
작업일: 2026-06-13
작업자: Claude (Claude Code)
브랜치: feat/simulator-discuss-chat
이번 작업 요약: 시뮬레이터 리포트 페이지 채팅을 전체 상담실(DiscussPage)과 동일한 멀티에이전트 진행/토론 UI로 전환. 기존에는 "AI 리포트 갱신"이 hidden 요청이라 agent-progress를 통째로 버려서 에이전트 간 대화(challenge/revision/consensus)가 안 보였음
수정한 주요 영역: frontend/src/features/pages/SimulatorPage.jsx (단일 agentProgress 상태 → chatProgressState의 activeProgressMap, StatusProgressRow 도입, agent-progress 핸들러의 hidden 조기 return 제거 후 viewType!=='status' 이벤트를 대화 메시지로 렌더, chat-status에서 COMPLETED/FAILED 시 진행맵 정리, 상태 배너는 FAILED만 표시 — DiscussPage와 동일 패턴)
추가/변경된 API: 없음
추가/변경된 환경변수: 없음
실행한 테스트: cd frontend && npm install; npm run build (성공, 69 modules); npm test (32/32 pass)
실패한 테스트와 이유: 해당 없음
데모 영향: 시뮬레이터에서 리포트 생성/갱신 중에도 에이전트들이 서로 의견을 주고받는 과정이 실시간으로 보임(전체 상담실과 동일 경험). hidden이던 리포트 생성 트리거 프롬프트(사용자 말풍선)는 여전히 숨김 유지
깨질 수 있는 부분: 진행/토론 메시지는 실시간 표시용이라 새로고침(히스토리 재로드) 후에는 사라짐(DiscussPage와 동일). 최종 리포트 카드/요약 말풍선과 리포트 데이터 적용은 기존 동작 유지
다음 사람이 보면 좋은 파일: frontend/src/features/pages/DiscussPage.jsx, frontend/src/features/chat/chatProgressState.js, frontend/src/features/chat/ChatRow.jsx(ProgressConversationRow)
아직 안 한 일: 다른 기능 페이지(FeaturePage)들도 동일 패턴 필요한지 검토 미진행
```

```text
작업일: 2026-06-13
작업자: Claude (Claude Code)
이번 작업 요약: 전체 코드 점검(멀티에이전트/외부 API/AI 판단/전체 플로우) 후 구조 문서와 제한사항·다음 작업 리스트를 실제 코드 기준으로 갱신
수정한 주요 영역: 루트 PROJECT_STRUCTURE_HANDOFF.md(백엔드 모듈 전체·Agent 10종·라우팅/토론 메커니즘·API 표 확장·§10 해커톤 데모 흐름 연출 가이드 추가), CURRENT_STATUS.md(검증된 제한사항 추가·우선순위 개선 리스트·본 기록)
추가/변경된 API: 없음(문서 표만 실제 엔드포인트에 맞게 확장)
추가/변경된 환경변수: 없음
실행한 테스트: 코드 변경 없음(문서만). 점검 과정에서 핵심 주장은 실제 소스 파일로 직접 재확인
실패한 테스트와 이유: 해당 없음
데모 영향: 없음(문서). 단, 표시된 🔴 치명 3건은 데모 안정성에 직접 영향 → 우선 처리 권장
깨질 수 있는 부분: 없음
다음 사람이 보면 좋은 파일: ai/app/rabbitmq_worker.py, ai/app/agents/orchestrator.py, backend .../aichat/application/AiChatExternalReferenceDataService.java, backend .../internal/InternalToolAuthService.java
아직 안 한 일: 섹션 10의 개선 항목은 코드 미적용(문서화만 완료)
```

```text
작업일: 2026-06-10
작업자: Codex
이번 작업 요약: RabbitMQ 채팅에서 Agent 진행 로그를 프론트에 노출할 수 있도록 AI progress event publish 구조 추가
수정한 주요 영역: ai Orchestrator/RabbitMQ worker, frontend Agent 매핑, 루트 문서
추가/변경된 API: 없음
추가/변경된 환경변수: 없음
실행한 테스트: `cd ai && .venv/bin/python -m unittest discover -s tests`; `cd backend && GRADLE_USER_HOME=/private/tmp/gradle ./gradlew test --tests com.kakao.backend.aichat.infrastructure.AiChatResponseListenerTest --tests com.kakao.backend.chat.application.ChatAiAgentEventServiceTest --tests com.kakao.backend.chat.application.ChatStreamEventFactoryTest`; `PATH=/Users/yechan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin:$PATH npm run build` in `frontend`; `docker compose config`
실패한 테스트와 이유: 최초 백엔드 Gradle 테스트는 샌드박스 파일락 소켓 제한으로 실패했으나 권한 승인 후 통과; 최초 프론트 build는 로컬 Node v18.15와 rolldown optional binding 누락으로 실패했으나, 번들 Node v24와 누락 binding 설치 후 통과
데모 영향: 채팅 중 선택된 Agent와 각 Agent 검토 시작/완료 메시지를 실시간으로 보여줄 수 있음
깨질 수 있는 부분: Agent progress 이벤트는 실시간 표시용이며 새로고침 후 히스토리에는 남지 않음
다음 사람이 보면 좋은 파일: ai/app/agents/orchestrator.py, ai/app/rabbitmq_worker.py, frontend/src/features/chat/chatMappers.js
아직 안 한 일: Agent progress 이벤트 히스토리 저장과 근거 패널 UI는 후속 작업으로 남김
```
