# StartMateAI Backend Guide

이 문서는 `backend/src/main/java/com/kakao/backend` 아래의 패키지들이 어떤 일을 하는지 빠르게 파악하기 위한 지도입니다.

## 전체 구조

```text
com.kakao.backend
  agent              AI 에이전트 정의
  aichat             AI 채팅 요청 생성 및 RabbitMQ 발행
  auth               회원가입, 로그인, 세션 인증
  chat               채팅방, 메시지, 에이전트 참여자 저장 모델
  commercialarea     상권 CSV/샘플 데이터 적재와 경쟁도 분석
  common             공통 설정, 공통 엔티티, 외부 API 호출, 예외 응답
  idea               창업 아이디어 결과와 선택지 저장 모델
  marketing          SNS 콘텐츠 생성 결과 저장 모델
  operation          운영 지표와 운영 피드백 저장 모델
  plan               사업계획서와 섹션 저장 모델
  policy             정부/공공 지원사업 수집, 정규화, 추천
  seed               기본 지식 시드 데이터 적재
  simulation         시뮬레이션 결과와 상세 항목 저장 모델
  startupProfile     창업 프로필 온보딩과 프로필 상태 관리
  user               사용자 계정 모델과 저장소
  workspace          사용자 작업 공간과 저장 결과
```

## 실행과 공통 설정

### `BackendApplication`

Spring Boot 애플리케이션 진입점입니다.

### `common.config`

- `WebConfig`
  - 로그인 검사 인터셉터와 CORS 정책을 등록합니다.
  - 현재 인증 API(`/auth/**`)를 제외한 요청에 세션 로그인 여부를 확인하도록 설정되어 있습니다.
- `JacksonConfiguration`
  - JSON 직렬화/역직렬화 공통 설정을 담당합니다.

### `common.presentation`

- `LoginRequiredInterceptor`
  - 요청 전에 `HttpSession`의 `LOGIN_USER_ID` 존재 여부를 확인합니다.
  - 없으면 `401 {"message":"로그인이 필요합니다."}`를 반환합니다.
- `GlobalExceptionHandler`
  - `AuthException`을 공통 에러 응답으로 변환합니다.
- `ApiErrorResponse`
  - API 에러 메시지 응답 DTO입니다.

### `common.domain`

- `BaseCreatedEntity`
  - 생성일(`createdAt`)만 필요한 엔티티의 공통 부모입니다.
- `BaseTimeEntity`
  - 생성일(`createdAt`)과 수정일(`updatedAt`)을 자동 관리하는 공통 부모입니다.

### `common.external`

- `ExternalApiClient`
  - 외부 HTTP API 호출을 담당합니다.
- `ApiResponseExtractor`
  - 외부 API 응답에서 필요한 목록 데이터를 뽑아냅니다.
- `ExternalApiResult`
  - 외부 API 호출 결과를 담는 record입니다.

## 인증: `auth`

회원가입, 로그인, 로그아웃, 세션 기반 인증을 담당합니다.

### 주요 API

`server.servlet.context-path=/api` 기준 외부 경로입니다.

```text
POST /api/auth/signup       회원가입 후 자동 로그인
POST /api/auth/login        로그인
POST /api/auth/logout       로그아웃
GET  /api/auth/me           현재 로그인 사용자 조회

GET  /api/profile/status    창업 프로필 입력 필요 여부 조회
GET  /api/profile           창업 프로필 상세 조회
POST /api/profile           창업 프로필 생성 또는 수정
```

### `auth.controller`

- `AuthController`
  - 회원가입, 로그인, 로그아웃, 현재 사용자 조회 API를 제공합니다.
  - 로그인 성공 시 `HttpSession`에 `AuthSession.LOGIN_USER_ID`를 저장합니다.

### `auth.service`

- `AuthService`
  - 이메일/닉네임/비밀번호 검증, 회원가입, 로그인 검증, 현재 사용자 조회를 담당합니다.
  - 닉네임은 XSS성 입력을 줄이기 위해 허용 문자와 길이를 제한합니다.
- `PasswordHashService`
  - 비밀번호를 salt 포함 SHA-256 해시로 저장하고 검증합니다.
- `StartupProfileService`
  - 프로필 존재 여부, 누락 필드 목록, 온보딩 필요 여부를 계산합니다.
  - 온보딩 입력값을 검증한 뒤 `StartupProfile`을 생성하거나 갱신합니다.
- `AuthSession`
  - 세션 attribute 이름(`LOGIN_USER_ID`)을 모아둡니다.
- `AuthException`
  - 인증/검증 실패 시 HTTP 상태와 메시지를 함께 담는 예외입니다.

### `auth.dto`

- `SignupRequest`, `LoginRequest`, `AuthUserResponse`
  - 인증 요청과 응답 DTO입니다.

## 사용자 계정: `user`

사용자 계정의 중심 엔티티와 저장소를 담당합니다.

### `user.model`

- `User`
  - 이메일, 비밀번호 해시, 닉네임, provider, role을 저장합니다.
  - `StartupProfile`, `Workspace`와 연결됩니다.

### `user.repository`

- `UserRepository`
  - 이메일 중복 확인, 이메일 로그인 조회를 제공합니다.

## 창업 프로필: `startupProfile`

로그인한 사용자의 창업 프로필 온보딩과 상태 관리를 담당합니다.

### `startupProfile.controller`

- `StartupProfileController`
  - 프론트가 온보딩 필요 여부를 판단할 수 있도록 프로필 상태를 반환합니다.
  - 온보딩 페이지에서 입력한 창업 프로필을 생성하거나 수정합니다.

### `startupProfile.service`

- `StartupProfileService`
  - 프로필 존재 여부, 누락 필드 목록, 온보딩 필요 여부를 계산합니다.
  - 온보딩 입력값을 검증한 뒤 `StartupProfile`을 생성하거나 갱신합니다.

### `startupProfile.model`

- `StartupProfile`
  - 전공, 경력, 관심 분야, 거주 지역, 사업 희망 지역, 초기 예산, 팀 상태, 창업 형태, 강점 태그 등을 저장합니다.
  - 팀 상태는 `TeamStatus`, 창업 형태는 `PreferredBusinessType` enum으로 관리합니다.
  - AI 채팅과 지원사업 추천에 사용자 컨텍스트로 활용될 수 있습니다.
- `TeamStatus`
  - 팀 구성 상태 enum입니다: `SOLO`, `HAS_TEAM`, `LOOKING_FOR_TEAM`, `UNDECIDED`.
- `PreferredBusinessType`
  - 희망 창업 형태 enum입니다: `ONLINE`, `OFFLINE`, `PLATFORM`, `LOCAL_STORE`, `HYBRID`, `UNDECIDED`.

### `startupProfile.repository`

- `StartupProfileRepository`
  - 사용자 id 기준 창업 프로필 조회를 제공합니다.

### `startupProfile.dto`

- `StartupProfileRequest`
  - 온보딩 프로필 입력 DTO입니다.
  - `teamStatus`, `preferredBusinessType`은 enum code를 권장하지만 한글 label도 입력으로 허용합니다.
- `StartupProfileResponse`
  - 저장된 프로필 상세 응답 DTO입니다.
- `StartupProfileStatusResponse`
  - `profileExists`, `profileCompleted`, `requiresOnboarding`, `missingFields`를 반환합니다.

## AI 채팅: `aichat`

사용자/프로필/최근 메시지/저장 결과를 AI 서버로 넘길 요청 메시지로 조립하고 RabbitMQ에 발행합니다.

### `aichat.application`

- `AiChatDispatchService`
  - `AiChatRequestFactory`로 요청 메시지를 만들고 `AiChatGateway`로 발행합니다.
- `AiChatRequestFactory`
  - 채팅방, 사용자 프로필, 최근 메시지, 저장 결과를 AI 요청 payload로 변환합니다.
- `AiChatGateway`
  - AI 채팅 요청 발행을 위한 포트 인터페이스입니다.
- `AiChatDispatchCommand`
  - AI 채팅 발행에 필요한 입력을 모은 command record입니다.

### `aichat.infrastructure`

- `RabbitMqAiChatGateway`
  - `AiChatGateway` 구현체입니다.
  - RabbitMQ exchange/routing key로 AI 채팅 요청을 발행합니다.

### `aichat.config`

- `AiChatRabbitConfiguration`
  - AI 채팅용 RabbitMQ exchange, queue, binding을 설정합니다.
- `AiChatProperties`
  - `startmate.ai.chat` 설정값을 바인딩합니다.

### `aichat.dto`

- `AiChatRequestMessage`
  - AI 서버로 보낼 최상위 요청 메시지입니다.
- `AiChatResponseMessage`
  - AI 서버 응답 메시지 구조입니다.
- `AiChatUserProfilePayload`
  - 사용자 창업 프로필 payload입니다.
- `AiChatContextPayload`
  - 저장 결과 등 AI가 참고할 컨텍스트 payload입니다.
- `AiRecentMessagePayload`
  - 최근 채팅 메시지 payload입니다.

## 채팅: `chat`

AI 에이전트와 사용자의 대화 기록을 저장하는 도메인입니다.

- `ChatRoom`
  - 사용자 작업 공간 안에서 하나의 대화방을 표현합니다.
- `ChatMessage`
  - 대화방에 쌓이는 사용자/에이전트 메시지입니다.
- `ChatAgentParticipant`
  - 채팅방에 참여한 에이전트와 역할을 저장합니다.

현재는 엔티티 중심이며 별도 컨트롤러/서비스는 아직 없습니다.

## 작업 공간: `workspace`

사용자가 만든 작업 단위와 AI/기능 결과물을 저장합니다.

- `Workspace`
  - 사용자별 작업 공간입니다.
  - 채팅방, 사업 아이디어, 시뮬레이션, 사업계획서, 운영 피드백, 마케팅 콘텐츠, 지원사업 추천 결과와 연결됩니다.
- `SavedResult`
  - 사용자가 저장한 결과물을 타입별로 보관합니다.

## AI 에이전트: `agent`

- `Agent`
  - 기획, 시뮬레이션, 정책 추천, 마케팅 등 역할별 AI 에이전트의 메타데이터를 저장합니다.

## 아이디어: `idea`

창업 아이디어 생성/선택 결과를 저장합니다.

- `BusinessIdeaResult`
  - 특정 workspace의 아이디어 생성 결과 묶음입니다.
- `BusinessIdeaOption`
  - 결과 안에 들어가는 개별 아이디어 선택지입니다.

현재는 저장 모델 중심이며 생성 API는 아직 없습니다.

## 시뮬레이션: `simulation`

창업 아이디어나 사업 계획의 시뮬레이션 결과를 저장합니다.

- `SimulationResult`
  - 전체 시뮬레이션 결과와 요약 지표를 저장합니다.
- `SimulationDetail`
  - 세부 항목별 점수/설명 등을 저장합니다.

현재는 엔티티 중심입니다.

## 사업계획서: `plan`

- `BusinessPlan`
  - workspace에 연결된 사업계획서 최상위 엔티티입니다.
- `BusinessPlanSection`
  - 사업계획서의 섹션별 내용을 저장합니다.

현재는 엔티티 중심입니다.

## 운영: `operation`

창업 이후 운영 지표와 피드백을 저장합니다.

- `OperationMetric`
  - 매출, 비용, 고객 수 같은 운영 지표를 저장합니다.
- `OperationFeedback`
  - 운영 개선 피드백과 액션 아이템을 저장합니다.

현재는 엔티티 중심입니다.

## 마케팅: `marketing`

SNS 콘텐츠 생성 결과를 저장합니다.

- `SnsContent`
  - SNS 콘텐츠 생성 결과 묶음입니다.
- `SnsContentItem`
  - 개별 SNS 콘텐츠 아이템입니다.

현재는 엔티티 중심입니다.

## 지원사업 추천: `policy`

공공 지원사업 데이터를 외부 API/샘플에서 가져오고, 사용자 조건과 매칭해 추천합니다.

### 주요 API

주의: 현재 `application.yml`에 `server.servlet.context-path=/api`가 있고, `SupportProgramController`도 `/api/support-programs`를 사용합니다. 따라서 현재 외부 경로는 `/api/api/support-programs/...` 형태가 될 수 있습니다.

```text
POST /api/api/support-programs/sync?source=all
POST /api/api/support-programs/recommend
```

### `policy.api`

- `SupportProgramController`
  - 지원사업 동기화와 추천 API를 제공합니다.

### `policy.service`

- `SupportProgramService`
  - K-Startup, Bizinfo, YouthCenter 데이터를 가져와 정규화 후 저장합니다.
  - 데이터가 없으면 데모 지원사업을 넣고 추천을 수행할 수 있습니다.

### `policy.connector`

- `KstartupConnector`
  - K-Startup 지원사업 API 호출을 담당합니다.
- `BizinfoConnector`
  - 기업마당/Bizinfo API 호출을 담당합니다.
- `YouthCenterConnector`
  - 청년정책 API 호출을 담당합니다.

### `policy.normalize`

- `SupportProgramNormalizer`
  - 서로 다른 외부 API 원천 데이터를 `SupportProgram` 엔티티 형태로 표준화합니다.
- `DateNormalizer`
  - 외부 데이터의 날짜 문자열을 `LocalDate`로 정규화합니다.

### `policy.matcher`

- `SupportProgramMatcher`
  - 연령, 지역, 창업 단계, 지원 유형, 업종, 모집 상태, 사업자등록 여부, 업력 조건을 점수화합니다.
  - 추천 이유(`reasons`)와 주의점(`cautions`)도 함께 만듭니다.

### `policy.domain`

- `SupportProgram`
  - 외부/샘플 지원사업 공고의 표준 저장 모델입니다.
- `SupportProgramRule`
  - 지원사업 매칭 규칙 저장 모델입니다.
- `SupportProgramRecommendation`
  - workspace별 추천 결과 묶음입니다.
- `SupportProgramMatch`
  - 추천된 개별 지원사업과 점수/사유를 저장합니다.

### `policy.repository`

- `SupportProgramRepository`
  - source/sourceId 기준 upsert 조회와 전체 추천 대상 조회를 담당합니다.
- `SupportProgramRuleRepository`
  - 지원사업 규칙 저장소입니다.

### `policy.dto`

- `SupportProgramRecommendationRequest`
  - 추천 요청 사용자 조건입니다.
- `RecommendedProgramResponse`
  - 추천 결과 응답입니다.
- `SupportProgramSyncResponse`
  - 외부 데이터 동기화 결과 응답입니다.

## 상권 분석: `commercialarea`

상가 CSV나 샘플 데이터를 저장하고 특정 지역/업종의 경쟁 정도를 계산합니다.

### 주요 API

주의: 현재 `application.yml`의 context-path와 컨트롤러 경로가 모두 `/api`를 포함하므로 외부 경로는 `/api/api/...` 형태가 될 수 있습니다.

```text
POST /api/api/stores/import-csv
POST /api/api/commercial-areas/analyze
```

### `commercialarea.api`

- `CommercialAreaController`
  - 상가 CSV 적재와 상권 분석 API를 제공합니다.

### `commercialarea.service`

- `CommercialAreaService`
  - CSV/ZIP 파일에서 상가 데이터를 읽어 저장합니다.
  - 파일이 없거나 읽기 실패 시 데모 상가 데이터를 넣습니다.
  - 요청 지역/업종 기준으로 전체 상가 수, 직접 경쟁자 수, 유사 경쟁자 수, 경쟁 수준을 계산합니다.

### `commercialarea.normalize`

- `StoreNormalizer`
  - CSV row를 `Store` 엔티티로 변환합니다.

### `commercialarea.domain`

- `Store`
  - 상가 원천 id, 상호명, 업종, 주소, 좌표, 원본 payload를 저장합니다.
- `CommercialAreaMetric`
  - 지역/업종별 분석 결과를 저장합니다.

### `commercialarea.repository`

- `StoreRepository`
  - 지역 조건별 상가 조회와 source/sourceStoreId 중복 조회를 제공합니다.
- `CommercialAreaMetricRepository`
  - 지역/업종 조합 기준 metric 조회를 제공합니다.

### `commercialarea.dto`

- `StoreImportRequest`, `StoreImportResponse`
  - 상가 데이터 적재 요청/응답입니다.
- `CommercialAreaRequest`, `CommercialAreaResponse`
  - 상권 분석 요청/응답입니다.

## 시드 데이터: `seed`

AI/기능에서 참고할 기본 분류와 템플릿 지식을 저장합니다.

### 주요 API

주의: 현재 외부 경로는 context-path 중복으로 `/api/api/seeds/default` 형태가 될 수 있습니다.

```text
POST /api/api/seeds/default
```

### 구성

- `SeedController`
  - 기본 시드 데이터를 넣는 API를 제공합니다.
- `SeedKnowledgeService`
  - 창업 단계, 지원 유형, 법률 체크리스트, 운영 체크리스트, 마케팅 플레이북, 초기 비용 템플릿 등을 upsert합니다.
- `SeedKnowledgeItem`
  - 시드 지식 항목 저장 엔티티입니다.
- `SeedKnowledgeItemRepository`
  - agentType/category/title 기준 중복 조회를 제공합니다.
- `SeedImportResponse`
  - 적재 개수 응답입니다.

## 테스트 구조

`backend/src/test/java`에는 다음 성격의 테스트가 있습니다.

- `BackendApplicationTests`
  - Spring context 로딩 확인.
- `domain/EntityMappingTests`
  - 주요 엔티티의 테이블명과 id 필드 매핑 확인.
- `aichat/application`
  - AI 요청 메시지 생성과 발행 흐름 테스트.
- `commercialarea/service`
  - 상권 분석 계산 테스트.
- `policy/matcher`, `policy/normalize`
  - 지원사업 정규화와 매칭 점수 테스트.
- `user/service`, `user/dto`
  - 인증, 비밀번호 해시, 응답 escape, 창업 프로필 온보딩 테스트.

`backend/src/test/resources/application.properties`는 테스트에서 H2 인메모리 DB를 사용하도록 고정합니다.

## 주요 데이터 흐름

### 로그인 후 온보딩

1. 프론트가 `POST /api/auth/login` 호출.
2. 서버가 `HttpSession`에 `LOGIN_USER_ID` 저장.
3. 프론트가 `GET /api/profile/status` 호출.
4. `requiresOnboarding=true`면 온보딩 페이지로 이동.
5. 온보딩 입력 후 `POST /api/profile` 호출.
6. 이후 `GET /api/profile/status`에서 `profileCompleted=true`가 됩니다.

### AI 채팅 요청

1. 도메인 정보와 최근 메시지를 `AiChatDispatchCommand`로 모읍니다.
2. `AiChatRequestFactory`가 AI 서버용 payload로 변환합니다.
3. `AiChatDispatchService`가 `AiChatGateway`에 발행을 위임합니다.
4. `RabbitMqAiChatGateway`가 RabbitMQ로 메시지를 보냅니다.

### 지원사업 추천

1. `POST /support-programs/sync` 계열 API로 외부 지원사업을 가져옵니다.
2. Connector가 외부 API를 호출합니다.
3. Normalizer가 원천 데이터를 `SupportProgram`으로 표준화합니다.
4. Service가 source/sourceId 기준으로 upsert합니다.
5. 추천 요청이 오면 Matcher가 사용자 조건과 공고 조건을 점수화합니다.

### 상권 분석

1. CSV/ZIP 또는 데모 데이터로 `Store`를 적재합니다.
2. 분석 요청의 지역/업종 조건으로 상가를 조회합니다.
3. 직접 경쟁/유사 경쟁 수를 계산합니다.
4. 결과를 `CommercialAreaMetric`으로 저장하고 응답합니다.

## 현재 주의할 점

- `server.servlet.context-path=/api`가 설정되어 있습니다.
- 그런데 일부 신규 데이터 API 컨트롤러는 `@RequestMapping("/api/...")`를 직접 사용합니다.
- 그래서 인증 API는 `/api/auth/...`인데, 일부 데이터 API는 `/api/api/...`가 될 수 있습니다.
- 라우트 정리를 할 때는 컨트롤러의 `/api` prefix를 제거하고 context-path에만 맡기는 방향이 가장 단순합니다.
- 로그인은 JWT가 아니라 서버 세션 기반입니다. 프론트 요청에는 쿠키가 포함되어야 하므로 `fetch`나 axios에서 credentials 옵션이 필요합니다.
