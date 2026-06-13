# 배포 서버 벡터 임베딩 명령어 모음

기준일: 2026-06-13 배포 작업용

이 문서는 배포 서버에서 Chroma 벡터 인덱스를 다시 만드는 절차입니다. `.chroma` 폴더는 Git으로 공유하지 않고, 배포 서버에서 직접 생성합니다.

## 0. 위치 이동

```bash
cd ~/StartMateAI
```

서버의 실제 프로젝트 경로가 다르면 `compose.yaml`이 있는 디렉터리로 이동합니다.

## 1. 환경변수 확인

루트 `.env`에 최소 아래 값이 있어야 합니다.

```env
GMS_API_KEY=발급받은_GMS_API_KEY
RAG_EMBEDDING_PROVIDER=openai
RAG_EMBEDDING_DIMENSIONS=3072
RAG_CHROMA_PATH=.chroma

SUPPORT_RAG_CHROMA_ENABLED=true
SUPPORT_RAG_CHROMA_PATH=.chroma
SUPPORT_RAG_CHROMA_COLLECTION=support_programs

OPENAI_EMBEDDING_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com
OPENAI_EMBEDDING_PATH=/v1/embeddings
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

BACKEND_INTERNAL_BASE_URL=http://backend:8080
STARTMATE_INTERNAL_TOOL_TOKEN=startmate-local-internal-token
```

법령 데이터를 새로 수집할 때만 추가로 필요합니다.

```env
LAW_OPEN_API_OC=국가법령정보센터_OC_KEY
```

## 2. 컨테이너 실행

백엔드, DB, RabbitMQ, AI worker를 먼저 올립니다.

```bash
docker compose up -d --build mysql rabbitmq backend ai-worker
docker compose ps
```

백엔드가 완전히 뜰 때까지 로그를 확인합니다.

```bash
docker compose logs -f backend
```

## 3. 기존 인덱스 백업 또는 삭제

인덱스를 완전히 새로 만들려면 로컬 마운트된 `ai/.chroma`를 지웁니다.

```bash
rm -rf ai/.chroma
mkdir -p ai/.chroma
```

삭제가 부담되면 백업 후 진행합니다.

```bash
mv ai/.chroma "ai/.chroma.backup.$(date +%Y%m%d-%H%M%S)" || true
mkdir -p ai/.chroma
```

## 4. 법령 RAG 인덱싱

이미 `ai/app/data/legal_documents.json`이 있으면 바로 인덱싱합니다.

```bash
docker compose exec ai-worker python scripts/index_legal_chroma.py --reset --query ""
```

법령 데이터를 서버에서 새로 수집한 뒤 인덱싱해야 하면 아래 순서로 실행합니다.

```bash
docker compose exec ai-worker python scripts/collect_legal_sources.py
docker compose exec ai-worker python scripts/index_legal_chroma.py --reset --query ""
```

수집 API를 짧게 테스트만 할 때는 `--limit`을 씁니다.

```bash
docker compose exec ai-worker python scripts/collect_legal_sources.py --limit 1
docker compose exec ai-worker python scripts/index_legal_chroma.py --reset --query ""
```

## 5. 지원사업 RAG 인덱싱

백엔드 지원사업 API에서 최신 데이터를 동기화하고 Chroma에 넣습니다.

```bash
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --reset
```

특정 소스만 동기화하려면 `--source`를 바꿉니다.

```bash
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --source kstartup --reset
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --source bizinfo --reset
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --source youthcenter --reset
```

백엔드 동기화 없이 이미 저장된 지원사업만 다시 임베딩하려면 `--sync`를 빼고 실행합니다.

```bash
docker compose exec ai-worker python scripts/index_support_chroma.py --reset
```

## 6. 한 번에 실행하는 배포용 순서

가장 자주 쓸 명령어 묶음입니다.

```bash
cd ~/StartMateAI

docker compose up -d --build mysql rabbitmq backend ai-worker

rm -rf ai/.chroma
mkdir -p ai/.chroma

docker compose exec ai-worker python scripts/index_legal_chroma.py --reset --query ""
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --reset

docker compose restart ai-worker
docker compose ps
```

## 7. 인덱스 개수 확인

Chroma 컬렉션이 생성됐는지 확인합니다.

```bash
docker compose exec ai-worker python -c "import chromadb; c=chromadb.PersistentClient(path='.chroma'); print('legal_sources=', c.get_collection('legal_sources').count()); print('support_programs=', c.get_collection('support_programs').count())"
```

생성된 파일은 서버 기준 아래 경로에 남습니다.

```text
StartMateAI/ai/.chroma/
StartMateAI/ai/app/data/support_programs.backend.json
```

## 8. AI worker 재시작

인덱싱 후 worker가 새 Chroma를 확실히 보도록 재시작합니다.

```bash
docker compose restart ai-worker
docker compose logs -f ai-worker
```

## 9. 자주 나는 문제

### GMS_API_KEY 오류

`.env`의 `GMS_API_KEY`가 비었거나 서버에 반영되지 않은 상태입니다.

```bash
grep -n "GMS_API_KEY" .env
docker compose up -d --build ai-worker
```

### Chroma 차원 오류

임베딩 모델이나 `RAG_EMBEDDING_DIMENSIONS`가 바뀐 뒤 기존 `.chroma`를 그대로 쓰면 발생할 수 있습니다. 삭제 후 다시 만듭니다.

```bash
rm -rf ai/.chroma
mkdir -p ai/.chroma
docker compose exec ai-worker python scripts/index_legal_chroma.py --reset --query ""
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --reset
docker compose restart ai-worker
```

### 지원사업이 비어 있음

백엔드 API 키 또는 동기화가 실패한 상태일 수 있습니다. 루트 `.env`에서 아래 키를 확인합니다.

```env
DATA_GO_KR_SERVICE_KEY=
BIZINFO_API_KEY=
YOUTH_CENTER_API_KEY=
STARTMATE_INTERNAL_TOOL_TOKEN=
```

지원사업 동기화만 다시 실행합니다.

```bash
docker compose exec ai-worker python scripts/index_support_chroma.py --sync --source all --reset
```

### ai-worker 컨테이너가 없다고 나옴

Compose가 내려가 있거나 다른 경로에서 명령을 실행한 상태입니다.

```bash
pwd
ls compose.yaml
docker compose up -d --build ai-worker
docker compose ps
```

