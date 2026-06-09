# 청년 창업 Agent 데이터/API 연동 MVP Handoff

이 문서는 해커톤용으로 구현한 **지원사업 추천 + 상권 경쟁점 계산 MVP**를 다른 팀원이나 AI coding assistant가 빠르게 이해하고 이어서 작업할 수 있도록 정리한 내용입니다.

## 1. 구현 방향

- 구현 위치: `backend` Spring Boot/JPA
- DB 기준: MySQL, 기존 프로젝트 관례에 맞춰 `Long` + `AUTO_INCREMENT`
- 마이그레이션 도구는 붙이지 않았고, 해커톤 데모 기준으로 Hibernate `ddl-auto=update`를 사용합니다.
- 실제 API key가 없어도 시연 가능하도록 support program/store demo seed fallback을 넣었습니다.
- AI 서버는 이번 작업에서 직접 연결하지 않았습니다. 백엔드 API를 먼저 만들고, 이후 `ai`의 `PolicyAgent`가 이 API를 호출하도록 붙이면 됩니다.

## 2. 실행 환경 변경

`compose.yaml`에 MySQL 서비스가 추가되었습니다.

```bash
docker compose up --build
```

기본 서비스:

- Frontend: `http://localhost`
- Backend: `http://localhost:8080`
- MySQL: `localhost:3306`
- DB/user/password: `startmate` / `startmate` / `startmate`

백엔드 주요 환경변수:

```text
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_DATASOURCE_PASSWORD
SPRING_JPA_HIBERNATE_DDL_AUTO
DATA_GO_KR_SERVICE_KEY
BIZINFO_API_KEY
YOUTH_CENTER_API_KEY
```

API key가 비어 있으면 외부 API sync는 빈 결과가 되고, 데모 seed fallback이 들어갑니다.

## 3. 추가된 주요 도메인

지원사업:

- `support_programs`: K-Startup/기업마당/온통청년 공고 정규화 저장
- `support_program_rules`: 향후 자격 룰 확장용 테이블

상권:

- `stores`: 소상공인 상가 CSV 또는 demo store 저장
- `commercial_area_metrics`: 지역/업종별 계산 결과 저장

Seed:

- `seed_knowledge_items`: Agent별 체크리스트/템플릿/분류 seed 저장

기존 `SupportProgramRecommendation`은 "사용자별 추천 결과" 성격이라 그대로 두고, 이번에는 원천 공고 저장용 `SupportProgram`을 새로 추가했습니다.

## 4. 주요 API

### Seed 일괄 import

```http
POST /api/seeds/import
```

역할:

- 지원사업 demo 공고 import
- 연남동 상권 demo store import
- Agent별 seed knowledge import

### 지원사업 sync

```http
POST /api/support-programs/sync?source=all
```

`source` 값:

- `all`
- `kstartup`
- `bizinfo`
- `youthcenter`

역할:

- 각 공식 API 호출
- raw response item 추출
- 공통 `support_programs` 형태로 normalize
- `(source, source_id)` 기준 upsert
- 실제 호출 실패 또는 API key 없음이면 demo 공고 fallback

### 지원사업 추천

```http
POST /api/support-programs/recommend
Content-Type: application/json

{
  "age": 27,
  "residenceSido": "서울",
  "desiredSido": "서울",
  "desiredSigungu": "마포구",
  "founderType": "pre_founder",
  "businessRegistered": false,
  "businessStage": "idea",
  "industryLarge": "음식점업",
  "industryMedium": "카페",
  "requiredFundingAmount": 30000000,
  "interestedSupportTypes": ["grant", "education", "mentoring", "space"]
}
```

응답은 `matchScore`, `matchReasons`, `cautionReasons`를 포함합니다.

점수는 해커톤 MVP 기준의 단순 룰입니다:

- 연령 조건
- 지역 조건
- 창업단계
- 관심 지원유형
- 업종 조건
- 모집 상태
- 사업자등록 필요 여부

주의: "지원 가능 확정"이 아니라 "추천 가능성/주의사항"으로 보여줘야 합니다.

### 상가 CSV import

```http
POST /api/stores/import-csv
Content-Type: application/json

{
  "filePath": "/absolute/path/to/sbiz_stores.csv",
  "region": "서울"
}
```

`filePath`가 비어 있거나 파일이 없으면 demo store가 import됩니다.
`filePath`가 `.zip`이면 ZIP 안에서 `region`에 맞는 지역 CSV를 찾아 stream으로 import합니다. `region`이 없으면 `서울`을 기본값으로 사용합니다.

CSV header는 소상공인 상권정보 파일의 일반 컬럼명을 우선 지원합니다:

- `상가업소번호`
- `상호명`
- `상권업종대분류명`
- `상권업종중분류명`
- `상권업종소분류명`
- `표준산업분류코드`
- `표준산업분류명`
- `시도명`
- `시군구명`
- `행정동명`
- `도로명주소`
- `지번주소`
- `경도`
- `위도`

실제 파일의 `시도명`은 `서울특별시`처럼 들어오지만, 저장/조회 시 `서울`, `부산`, `경기` 같은 짧은 이름으로 정규화합니다.

### 상권 분석

```http
POST /api/commercial-areas/analyze
Content-Type: application/json

{
  "sido": "서울",
  "sigungu": "마포구",
  "dong": "연남동",
  "industryLarge": "음식점업",
  "industryMedium": "커피점/카페",
  "industrySmall": "카페"
}
```

응답:

- `totalStores`: 지역 내 전체 점포 수
- `directCompetitors`: 입력 업종과 직접 일치하는 경쟁점 수
- `similarCompetitors`: 대분류/중분류가 비슷한 점포 수
- `competitionLevel`: `low`, `medium`, `high`
- `notes`: 임대료/매출은 별도 데이터가 필요하다는 경고 포함

V0 경쟁 강도 기준:

- `directCompetitors <= 5`: `low`
- `directCompetitors <= 20`: `medium`
- `directCompetitors > 20`: `high`

## 5. 주요 코드 위치

지원사업:

- `src/main/java/com/kakao/backend/policy/api/SupportProgramController.java`
- `src/main/java/com/kakao/backend/policy/service/SupportProgramService.java`
- `src/main/java/com/kakao/backend/policy/connector/*Connector.java`
- `src/main/java/com/kakao/backend/policy/normalize/SupportProgramNormalizer.java`
- `src/main/java/com/kakao/backend/policy/matcher/SupportProgramMatcher.java`
- `src/main/java/com/kakao/backend/policy/domain/SupportProgram.java`
- `src/main/java/com/kakao/backend/policy/domain/SupportProgramRule.java`

상권:

- `src/main/java/com/kakao/backend/commercialarea/api/CommercialAreaController.java`
- `src/main/java/com/kakao/backend/commercialarea/service/CommercialAreaService.java`
- `src/main/java/com/kakao/backend/commercialarea/normalize/StoreNormalizer.java`
- `src/main/java/com/kakao/backend/commercialarea/domain/Store.java`
- `src/main/java/com/kakao/backend/commercialarea/domain/CommercialAreaMetric.java`

Seed:

- `src/main/java/com/kakao/backend/seed/api/SeedController.java`
- `src/main/java/com/kakao/backend/seed/service/SeedKnowledgeService.java`
- `src/main/java/com/kakao/backend/seed/domain/SeedKnowledgeItem.java`

공통 외부 API:

- `src/main/java/com/kakao/backend/common/external/ExternalApiClient.java`
- `src/main/java/com/kakao/backend/common/external/ApiResponseExtractor.java`

## 6. 테스트

실행:

```bash
cd backend
GRADLE_USER_HOME=/private/tmp/gradle ./gradlew test
```

추가된 테스트:

- `SupportProgramNormalizerTest`: 지원사업 raw fixture 정규화
- `SupportProgramMatcherTest`: 청년 예비창업자 추천 점수
- `CommercialAreaServiceTest`: 연남동 카페 경쟁점 계산

현재 테스트는 H2 MySQL mode로 동작합니다.

## 7. 다음 작업 제안

해커톤 데모 우선순위:

1. 프론트 `지원사업 추천` 화면에서 `POST /api/support-programs/recommend` 호출
2. 프론트 `상권 분석` 화면에서 `POST /api/commercial-areas/analyze` 호출
3. AI 서버 `PolicyAgent`가 백엔드 추천 API를 호출하도록 연결
4. 실제 API key를 넣고 `POST /api/support-programs/sync?source=all` 확인
5. 실제 소상공인 CSV 파일 경로로 `POST /api/stores/import-csv` 확인

주의할 점:

- K-Startup은 기존 중단 예정 API가 아니라 신규 `K-Startup(사업소개, 사업공고, 콘텐츠 등)_조회서비스` 기준입니다.
- 공식 API 응답 필드는 조금씩 바뀔 수 있으므로 `SupportProgramNormalizer`의 후보 필드명을 필요할 때 보강하면 됩니다.
- 현재 CSV parser는 해커톤용 단순 구현입니다. 매우 큰 전국 CSV를 바로 넣기보다는 지역 단위 파일이나 샘플 subset으로 먼저 확인하는 것이 안전합니다.
- 법률/금융 응답은 단정하지 말고 체크리스트/확인 필요/전문가 상담 권장 톤을 유지해야 합니다.
