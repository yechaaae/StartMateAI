# StartMate AI 구현 방향

## 1. 현재 구현 골격

PDF 기획서 기준 AI 파트는 `Orchestrator Agent`가 사용자 의도를 판단하고 아래 전문 에이전트로 위임하는 구조로 잡았다.

- `ProfileAgent`: JSON 프로필과 자연어 질문을 합쳐 `effective_profile`을 만들고 강점, 제약조건, 준비도 점수, 추가 질문을 정리. 확실한 숫자/부정 표현은 규칙으로 검증하고, GMS가 켜져 있으면 LLM 기반 구조화 추출로 경험, 관심 분야, 채널 선호 같은 자연어 표현을 보정한다.
- `IdeaAgent`: GMS가 켜져 있으면 LLM으로 맞춤 아이템 후보를 JSON 생성하고, 코드는 예산/경험/관심 분야/채널/리스크/30일 검증 가능성을 점수화해 상위 3~5개 추천
- `PolicyAgent`: 지원사업 공고 검색/RAG 매칭, 제출 서류 체크리스트 생성
- `FinanceAgent`: 초기비용, 예상 매출, 손익분기점, 30일 운영 시뮬레이션
- `SimulationAgent`: 30일 동안 이벤트와 선택지를 제공하는 게임형 창업 체험
- `OperationAgent`: 매출, 재고, 리뷰 기반 운영 피드백과 다음 주 계획
- `MarketingAgent`: SNS 릴스 훅, 15초 콘티, 게시글, 해시태그, 업로드 일정 생성

현재는 해커톤 데모가 바로 붙을 수 있도록 GMS LLM + deterministic rule fallback 형태로 동작한다. GMS API 형식이 바뀌면 `app/core/gms_client.py`만 수정하거나 환경변수만 채우면 된다.

`ProfileAgent`는 단독 호출과 멀티에이전트 호출 양쪽에서 사용된다. 단독 호출에서는 사용자에게 보여줄 프로필 분석과 추가 질문을 반환하고, 멀티에이전트 호출에서는 `effective_profile`, `readiness_scores`, `agent_hints`를 Orchestrator와 다른 에이전트의 판단 근거로 제공한다.

`/ai/chat`의 넓은 상담 흐름은 단순 라우팅이 아니라 협업형 멀티에이전트로 동작한다.

1차 라운드에서는 `ProfileAgent`, `IdeaAgent`, `PolicyAgent`가 동시에 실행되어 사용자 조건, 아이템 후보, 지원사업 가능성을 병렬 검토한다.

2차 라운드에서는 1순위 아이템을 기준으로 `FinanceAgent`, `MarketingAgent`, `OperationAgent`가 동시에 실행되어 비용, 홍보, 운영 리스크를 검토한다.

마지막으로 `OrchestratorAgent`가 1차 라운드 결론을 `round1_synthesis`로 압축하고, 각 에이전트의 입장, 충돌 지점, 최종 결정을 `debate` 필드로 통합한다.

모든 에이전트는 공통 출력 계약을 따른다. 상세 구조는 [agent_contract.md](agent_contract.md)를 참고한다.

```text
position
evidence
score
risks
assumptions
missing_inputs
recommendation
```

## 2. API 설계

프론트는 단일 라우팅 API와 기능별 API 중 편한 것을 쓰면 된다.

- `POST /ai/chat`: 사용자 메시지 기반 자동 라우팅 또는 협업형 멀티에이전트 상담
- `POST /ai/profile/analyze`: 창업 프로필 분석
- `POST /ai/ideas/recommend`: 아이템 추천
- `POST /ai/policies/match`: 지원사업 매칭
- `POST /ai/finance/simulate`: 비용/매출/손익분기점 시뮬레이션
- `POST /ai/simulation/start`: 30일 게임형 창업 시뮬레이션 시작
- `POST /ai/simulation/choose`: 선택지 반영 후 다음 날 이벤트 반환
- `POST /ai/operations/feedback`: 창업 후 운영 피드백
- `POST /ai/marketing/sns`: SNS 홍보 자동화

응답은 모두 `AgentResponse` 형태다.

```json
{
  "intent": "idea",
  "agent": "IdeaAgent",
  "summary": "요약",
  "data": {},
  "next_actions": [],
  "sources": [],
  "warnings": []
}
```

## 3. GMS 연동 지점

`app/core/gms_client.py`는 GMS Gemini `generateContent` 형태를 기본값으로 둔다.

```json
{
  "systemInstruction": {
    "parts": [{"text": "..."}]
  },
  "contents": [
    {
      "role": "user",
      "parts": [{"text": "..."}]
    }
  ],
  "generationConfig": {
    "temperature": 0.3
  }
}
```

확인해야 할 값:

- GMS base URL: `https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com`
- path 예: `/v1beta/models/gemini-2.5-flash:generateContent`
- 인증 헤더 예: `x-goog-api-key: <key>`
- 쿼리스트링 인증이 필요하면 `GMS_API_KEY_HEADER=""`, `GMS_API_KEY_QUERY_PARAM="key"`
- 응답 텍스트 위치: `candidates[0].content.parts[*].text`

형식이 다르면 `GMSClient._build_payload`, `_build_headers`, `_extract_content`만 바꾸면 된다.

## 4. RAG 확장 방향

현재 `support_programs.sample.json`은 샘플 데이터다. 실제 구현은 아래 순서로 확장한다.

1. K-Startup, 지자체, 소상공인 지원 공고를 크롤링 또는 수동 업로드
2. 제목, 지역, 대상, 마감일, 제출서류, 지원금, URL을 정규화
3. 문서를 chunk로 쪼개 임베딩 인덱스 생성
4. `PolicyAgent`에서 keyword + vector hybrid 검색
5. 응답에 출처 URL과 공고 원문 근거를 함께 제공

현재 샘플 RAG는 `app/rag/vector_store.py`의 `LocalVectorStore`와 `app/rag/embeddings.py`의 `HashEmbeddingProvider`를 통해 vector retrieval 형태로 동작한다. 외부 Vector DB가 확정되기 전까지는 dependency-free 로컬 인덱스로 문서 chunk를 임베딩하고, 실제 구현 시 이 인터페이스를 Chroma, FAISS, Pinecone, GMS embedding 등으로 교체한다.

검색 모드는 `.env`의 `RAG_RETRIEVAL_MODE`로 바꾼다.

```text
keyword: 기존 규칙/키워드 점수만 사용
vector: vector hit가 있는 문서만 후보로 사용
hybrid: vector similarity + 지역/단계/서류/예산 점수를 결합
```

현재 샘플 RAG도 단순 키워드 개수 대신 지역 적합도, 창업단계 적합도, 관심/경험 키워드, 예산 부담 완화 가능성, 서류 준비도, vector similarity를 나눠 점수화한다. `PolicyAgent` 응답의 `matches[].score_breakdown`, `matches[].retrieval`, `matches[].source_chunks`, `eligibility_gaps`, `required_documents`, `application_strategy`를 프론트에 보여주면 정책 에이전트의 판단 근거가 드러난다.

## 5. 데모 우선순위

해커톤 데모에서는 아래 흐름을 먼저 완성하는 것이 좋다.

1. 프로필 입력
2. 아이템 추천 3개
3. 1개 선택 후 비용/손익분기점 시뮬레이션
4. 지역 기반 지원사업 매칭
5. SNS 홍보 문구 생성

운영 피드백은 창업 후 데이터가 필요하므로, 데모에서는 샘플 매출/리뷰 입력으로 보여주면 된다.

발표에서는 `/ai/chat` 응답의 `data.rounds`, `data.round1_synthesis`, `data.debate.agent_positions`, `data.debate.conflicts`, `data.debate.orchestrator_decision`을 보여주면 멀티에이전트 협업 구조가 잘 드러난다.

30일 창업 체험은 `SimulationAgent`를 사용한다. 프론트는 `start` 응답의 `current_event.choices`를 카드/버튼으로 보여주고, 선택한 `choice_id`를 `choose` API로 보내면 된다. 매 선택마다 현금, 총매출, 재고, 평판, 고객 수, 피로도, 리스크, 홍보력이 갱신된다. 30일이 지나면 `final_report`에 점수와 등급이 반환된다.

## 6. 다음 고도화 순서

1. `PolicyAgent`: 실제 공고 JSON 수집 후 현재 score breakdown을 유지한 채 embedding RAG로 확장
2. `SimulationAgent`: 업종별 이벤트 확률, 장기 효과, 엔딩 다양화
3. `FinanceAgent`: 업종별 비용 템플릿과 what-if 시나리오 강화
4. `IdeaAgent`: `PolicyAgent`, `FinanceAgent`, `SimulationAgent` 점수를 반영한 통합 추천 점수화
5. `MarketingAgent`: GMS로 업종/이벤트별 콘텐츠 문구 생성
6. `OperationAgent`: 주간 리포트와 위험 신호 탐지 강화
7. `ProfileAgent`: LLM 구조화 추출 결과의 confidence/근거 표시와 추가 질문 UX 강화
8. `OrchestratorAgent`: 2차 재토론 라운드와 최종 합의 근거 강화
