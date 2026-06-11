# RAG 임베딩 재생성 명령어

다른 사람이 같은 RAG를 쓰려면 `.chroma` 폴더를 Git으로 받는 것이 아니라, 각자 로컬에서 아래 명령으로 다시 임베딩하면 됩니다.

현재 RAG 대상은 두 가지입니다.

- 법률 RAG: `LegalAgent`
- 지원사업 RAG: `PolicyAgent`

상권 분석은 RAG가 아니라 MySQL `stores` 테이블 조회입니다. 상권 데이터 적재는 별도 문서를 참고하세요.

## 1. 환경 변수

`StartMateAI/ai/.env`에 아래 값이 있어야 합니다.

```env
RAG_CHROMA_PATH=.chroma
RAG_EMBEDDING_PROVIDER=openai
RAG_EMBEDDING_DIMENSIONS=3072

SUPPORT_RAG_CHROMA_ENABLED=true
SUPPORT_RAG_CHROMA_PATH=.chroma
SUPPORT_RAG_CHROMA_COLLECTION=support_programs
SUPPORT_RAG_EMBEDDING_DIMENSIONS=384

OPENAI_EMBEDDING_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com
OPENAI_EMBEDDING_PATH=/v1/embeddings
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
GMS_API_KEY=발급받은_GMS_KEY

BACKEND_INTERNAL_BASE_URL=http://backend:8080
STARTMATE_INTERNAL_TOOL_TOKEN=startmate-local-internal-token
```

법률 원문을 다시 수집하려면 추가로 필요합니다.

```env
LAW_OPEN_API_OC=국가법령정보센터_OC
```

루트 Docker Compose에서 실행할 경우 루트 `.env`에도 `GMS_API_KEY`, `STARTMATE_INTERNAL_TOOL_TOKEN` 등이 들어가 있어야 합니다.

## 2. Docker 서비스 실행

루트에서 실행합니다.

```bash
cd StartMateAI
docker compose up -d --build mysql rabbitmq backend ai-worker
```

상태 확인:

```bash
docker compose ps
```

## 3. 법률 RAG 인덱싱

### 3-1. 이미 법률 JSON이 있는 경우

아래 파일이 있으면 바로 인덱싱할 수 있습니다.

```text
ai/app/data/legal_documents.json
```

로컬 venv 기준:

```bash
cd StartMateAI/ai
./.venv/Scripts/python.exe scripts/index_legal_chroma.py
```

Docker 기준:

```bash
cd StartMateAI
docker compose exec ai-worker python scripts/index_legal_chroma.py
```

### 3-2. 법률 원문부터 다시 수집하는 경우

`LAW_OPEN_API_OC`가 필요합니다.

로컬 venv 기준:

```bash
cd StartMateAI/ai
./.venv/Scripts/python.exe scripts/collect_legal_sources.py
./.venv/Scripts/python.exe scripts/index_legal_chroma.py
```

수집 개수를 줄여 테스트하려면:

```bash
cd StartMateAI/ai
./.venv/Scripts/python.exe scripts/collect_legal_sources.py --limit 1
./.venv/Scripts/python.exe scripts/index_legal_chroma.py
```

## 4. 지원사업 RAG 인덱싱

지원사업 RAG는 백엔드의 지원사업 DB를 가져와 Chroma에 넣습니다.

### 4-1. 백엔드 지원사업 동기화

루트에서:

```bash
cd StartMateAI
curl -X POST "http://localhost:8080/api/internal/ai-tools/support-programs/sync?source=all" \
  -H "X-Startmate-Internal-Token: startmate-local-internal-token"
```

Windows PowerShell:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8080/api/internal/ai-tools/support-programs/sync?source=all" `
  -Headers @{ "X-Startmate-Internal-Token" = "startmate-local-internal-token" }
```

### 4-2. Chroma 인덱싱

로컬 venv 기준:

```bash
cd StartMateAI/ai
./.venv/Scripts/python.exe scripts/index_support_chroma.py --sync
```

Docker 기준:

```bash
cd StartMateAI
docker compose exec ai-worker python scripts/index_support_chroma.py --sync
```

`--sync`를 붙이면 인덱싱 전에 백엔드 지원사업 동기화를 한 번 더 호출합니다.

## 5. 전체 RAG 재생성 한 번에 실행

법률 JSON이 이미 있다고 가정한 빠른 버전:

```bash
cd StartMateAI/ai
./.venv/Scripts/python.exe scripts/index_legal_chroma.py
./.venv/Scripts/python.exe scripts/index_support_chroma.py --sync
```

Docker 기준:

```bash
cd StartMateAI
docker compose exec ai-worker python scripts/index_legal_chroma.py
docker compose exec ai-worker python scripts/index_support_chroma.py --sync
```

## 6. 생성되는 파일

인덱싱 결과는 아래 경로에 생성됩니다.

```text
StartMateAI/ai/.chroma/
```

지원사업 스냅샷은 아래 파일로 저장될 수 있습니다.

```text
StartMateAI/ai/app/data/support_programs.backend.json
```

주의:

- `.chroma`는 Git에 올리지 않습니다.
- `.chroma`는 각자 로컬에서 재생성합니다.
- 임베딩 모델과 차원이 바뀌면 기존 Chroma 컬렉션을 지우고 다시 만들어야 합니다.

## 7. Chroma를 처음부터 다시 만들기

기존 인덱스가 꼬였거나 임베딩 모델을 바꿨다면 `.chroma`를 삭제하고 다시 인덱싱합니다.

PowerShell:

```powershell
cd StartMateAI/ai
Remove-Item -Recurse -Force .chroma
./.venv/Scripts/python.exe scripts/index_legal_chroma.py
./.venv/Scripts/python.exe scripts/index_support_chroma.py --sync
```

Docker Compose를 쓰는 경우 `ai/.chroma`가 컨테이너에 마운트되어 있으므로, 로컬 `ai/.chroma`를 지우면 됩니다.

## 8. 동작 확인

AI worker를 다시 시작합니다.

```bash
cd StartMateAI
docker compose up -d --build ai-worker
```

법률 RAG 테스트 질문:

```text
홍보용으로 팝업스토어를 길거리에서 하려고 하는데 관련 법률 알려줘
```

지원사업 RAG 테스트 질문:

```text
구미시에서 받을 수 있는 창업 지원사업 알려줘
```

정상이라면 답변에 다음 정보가 포함되어야 합니다.

- 어떤 문서/공고를 참조했는지
- 왜 그 결과를 골랐는지
- 다음 행동 또는 확인할 조건

## 9. 자주 나는 문제

### GMS_API_KEY가 없다고 나오는 경우

`ai/.env` 또는 루트 `.env`에 `GMS_API_KEY`가 들어갔는지 확인합니다.

### 임베딩 차원 오류가 나는 경우

`RAG_EMBEDDING_DIMENSIONS`와 기존 `.chroma` 컬렉션 차원이 다를 수 있습니다.

해결:

```powershell
cd StartMateAI/ai
Remove-Item -Recurse -Force .chroma
./.venv/Scripts/python.exe scripts/index_legal_chroma.py
./.venv/Scripts/python.exe scripts/index_support_chroma.py --sync
```

### 지원사업이 데모 데이터만 나오는 경우

백엔드 API 키 또는 지원사업 sync가 실패했을 수 있습니다.

확인:

```bash
cd StartMateAI
curl -X POST "http://localhost:8080/api/internal/ai-tools/support-programs/sync?source=all" \
  -H "X-Startmate-Internal-Token: startmate-local-internal-token"
```

### Docker에서는 되는데 로컬 venv에서는 안 되는 경우

로컬에서 의존성을 설치합니다.

```bash
cd StartMateAI/ai
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```
