# LegalAgent RAG source plan

This project should collect legal text from official Korean government sources only.

## Official sources

- 국가법령정보 공동활용 Open API: https://open.law.go.kr/LSO/openApi/guideList.do
- 현행법령 본문 조회 API: https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=lsEfYdInfoGuide
- 자치법규 본문 조회 API: https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=ordinInfoGuide
- 공공데이터포털 법제처 국가법령정보 공유서비스: https://www.data.go.kr/data/15000115/openapi.do

## MVP scope

Use `app/data/legal_sources.seed.json` as the first ingestion list. It covers:

- Food popup basics: `식품위생법`, `식품위생법 시행령`, `식품위생법 시행규칙`
- Food labeling/advertising: `식품 등의 표시ㆍ광고에 관한 법률`
- Online sales: `전자상거래 등에서의 소비자보호에 관한 법률`
- Customer data: `개인정보 보호법`
- Tax/business registration: `부가가치세법`
- Offline space contracts: `상가건물 임대차보호법`
- Marketing/IP/labor basics: `표시ㆍ광고의 공정화에 관한 법률`, `상표법`, `저작권법`, `근로기준법`, `최저임금법`
- Local layer: Gumi/Gyeongbuk startup and small-business ordinances

## Ingestion command

The Law Open API requires an `OC` authentication value registered for the caller IP/domain.

```powershell
$env:LAW_OPEN_API_OC="your-oc"
.\.venv\Scripts\python.exe scripts\collect_legal_sources.py
```

Outputs:

- `app/data/legal_documents.json`: normalized article chunks
- `app/data/legal_collection_report.json`: collection status by source
- `.rag_index/legal_sources.vector.json`: local vector index for RAG experiments

## Retrieval shape

LegalAgent should not rely on similarity alone. Use a checklist planner first:

1. Extract business facts: item, region, online/offline, food handling, hiring, customer data, rental space.
2. Map facts to legal domains: permit, hygiene, labeling, e-commerce, privacy, tax, lease, labor, IP.
3. Run one RAG query per domain.
4. Return `likely_required`, `needs_confirmation`, `missing_inputs`, and `citations`.

The answer should say "확인 필요" for uncertain legal conclusions and point to the relevant authority when needed.
