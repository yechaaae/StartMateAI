# StartMate AI

AI 기반 맞춤형 창업 실행 파트너의 멀티에이전트 API 서버 골격이다.

`/ai/chat`의 넓은 상담 요청은 여러 에이전트가 병렬로 의견을 내고, Orchestrator가 충돌 지점과 최종 결정을 `debate`로 통합한다.

## 실행

```powershell
cd c:\ssafy\해커톤\ai
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8001
```

Swagger 문서:

```text
http://127.0.0.1:8001/docs
```

## GMS 설정

처음에는 mock 모드로 동작한다. 실제 GMS API를 붙일 때는 `.env`에 값을 넣고 `USE_MOCK_LLM=false`로 바꾼다.

```powershell
$env:USE_MOCK_LLM="false"
$env:GMS_API_KEY="..."
$env:GMS_BASE_URL="https://gms.ssafy.io/gmsapi/generativelanguage.googleapis.com"
$env:GMS_CHAT_PATH="/v1beta/models/gemini-2.5-flash:generateContent"
$env:GMS_MODEL="gemini-2.5-flash"
$env:GMS_API_KEY_HEADER="x-goog-api-key"
```

만약 GMS 안내가 쿼리스트링 `key=$GMS_KEY` 방식을 요구하면 아래처럼 헤더를 비우고 query param을 켠다.

```powershell
$env:GMS_API_KEY_HEADER=""
$env:GMS_API_KEY_QUERY_PARAM="key"
```

GMS Gemini `generateContent` 형식은 기본 지원한다. 호출 형식이 바뀌면 [docs/implementation_direction.md](docs/implementation_direction.md)의 `GMS 연동 지점`을 기준으로 `app/core/gms_client.py`만 수정하면 된다.

## RAG 설정

지원사업 매칭은 vector retrieval을 붙일 수 있는 구조로 되어 있다. 현재는 외부 Vector DB 대신 로컬 `LocalVectorStore`와 hash embedding을 사용하고, 나중에 Chroma/FAISS/GMS embedding 구현으로 교체하면 된다.

```powershell
$env:RAG_RETRIEVAL_MODE="hybrid"  # keyword, vector, hybrid
$env:RAG_VECTOR_STORE_PATH=".rag_index/support_programs.vector.json"
$env:RAG_EMBEDDING_DIMENSIONS="384"
```

`/health`에서 `rag_retrieval_mode`, `rag_vector_store` 값을 확인할 수 있다.

## 에이전트 응답 구조

모든 에이전트는 `AgentResponse.data` 안에 공통 판단 필드를 포함한다.

```text
position
evidence
score
risks
assumptions
missing_inputs
recommendation
```

상세 설명은 [docs/agent_contract.md](docs/agent_contract.md)를 참고한다.

## 예시 요청

30일 게임형 창업 시뮬레이션 시작:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/ai/simulation/start `
  -ContentType "application/json" `
  -Body '{
    "item_name": "수제 쿠키 팝업",
    "business_type": "popup",
    "difficulty": "normal",
    "profile": {
      "region": "부산",
      "budget_krw": 3000000,
      "interests": ["카페", "로컬"]
    }
  }'
```

선택지 반영:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/ai/simulation/choose `
  -ContentType "application/json" `
  -Body '{
    "session_id": "start 응답의 session_id",
    "choice_id": "A"
  }'
```

응답의 `current_event.choices`를 버튼으로 보여주고, 사용자가 고른 `choice_id`를 `/ai/simulation/choose`로 보내면 다음 날 이벤트가 반환된다.

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/ai/chat `
  -ContentType "application/json" `
  -Body '{
    "message": "부산에서 소자본으로 가능한 창업 아이템 추천해줘",
    "profile": {
      "major": "디자인",
      "experiences": ["카페 알바", "SNS 콘텐츠 제작"],
      "region": "부산",
      "budget_krw": 3000000,
      "interests": ["브랜딩", "카페", "로컬"],
      "preferred_channels": ["오프라인", "SNS"],
      "startup_stage": "예비창업",
      "risk_tolerance": "low"
    }
  }'
```

## 구조

```text
app/
  api/routes.py              # FastAPI 엔드포인트
  agents/orchestrator.py     # 의도 분석, 병렬 에이전트 협업, 결과 통합
  agents/profile.py          # 사용자 조건 분석
  agents/idea.py             # 창업 아이템 추천
  agents/policy.py           # 지원사업 매칭
  agents/finance.py          # 비용/매출/손익분기점 계산
  agents/simulation.py       # 30일 게임형 창업 시뮬레이션
  agents/operation.py        # 운영 피드백
  agents/marketing.py        # SNS 콘텐츠 생성
  core/gms_client.py         # GMS API 어댑터
  rag/embeddings.py          # 임베딩 provider 인터페이스와 로컬 hash embedding
  rag/vector_store.py        # 로컬 vector store 인터페이스
  rag/retriever.py           # 지원사업 hybrid RAG 검색
  data/support_programs.sample.json
```
