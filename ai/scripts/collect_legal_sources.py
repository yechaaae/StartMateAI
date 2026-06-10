from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag.embeddings import HashEmbeddingProvider
from app.rag.vector_store import LocalVectorStore, VectorDocument


LAW_SEARCH_URL = "https://www.law.go.kr/DRF/lawSearch.do"
LAW_SERVICE_URL = "https://www.law.go.kr/DRF/lawService.do"


@dataclass
class CollectionResult:
    source: dict[str, Any]
    status: str
    message: str = ""
    selected: dict[str, Any] | None = None
    chunk_count: int = 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect legal source chunks for LegalAgent RAG.")
    parser.add_argument("--seed", default="app/data/legal_sources.seed.json")
    parser.add_argument("--out", default="app/data/legal_documents.json")
    parser.add_argument("--report", default="app/data/legal_collection_report.json")
    parser.add_argument("--vector-out", default=".rag_index/legal_sources.vector.json")
    parser.add_argument("--oc", default="")
    parser.add_argument("--limit", type=int, default=0, help="Optional source limit for quick tests.")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between API calls.")
    parser.add_argument("--rebuild-vector", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    oc = args.oc or os.getenv("LAW_OPEN_API_OC") or os.getenv("LAW_API_OC") or ""
    seed_path = _path(args.seed)
    sources = json.loads(seed_path.read_text(encoding="utf-8"))
    if args.limit > 0:
        sources = sources[: args.limit]

    if not oc:
        print("LAW_OPEN_API_OC is missing. Add it to .env or pass --oc.")
        print(f"Seed list is ready: {seed_path}")
        return

    all_documents: list[dict[str, Any]] = []
    report: list[CollectionResult] = []

    for source in sources:
        try:
            documents, selected = collect_source(source, oc=oc)
            all_documents.extend(documents)
            report.append(
                CollectionResult(
                    source=source,
                    status="ok" if documents else "empty",
                    selected=selected,
                    chunk_count=len(documents),
                )
            )
        except Exception as exc:  # noqa: BLE001 - collection should continue per source.
            report.append(CollectionResult(source=source, status="error", message=str(exc)))
        time.sleep(args.sleep)

    out_path = _path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(all_documents, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = _path(args.report)
    report_payload = {
        "source_count": len(sources),
        "document_count": len(all_documents),
        "results": [result.__dict__ for result in report],
    }
    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    vector_path = _path(args.vector_out)
    build_vector_index(all_documents, vector_path=vector_path, rebuild=args.rebuild_vector)

    print(f"Collected {len(all_documents)} chunks from {len(sources)} sources.")
    print(f"Wrote {out_path}")
    print(f"Wrote {report_path}")
    print(f"Wrote {vector_path}")


def collect_source(source: dict[str, Any], *, oc: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    target = "ordin" if source.get("source_type") == "local_ordinance" else "law"
    service_target = "ordin" if target == "ordin" else "eflaw"
    query = source["query"]

    search_payload = request_json(
        LAW_SEARCH_URL,
        {
            "OC": oc,
            "target": target,
            "type": "JSON",
            "query": query,
            "display": 10,
        },
    )
    candidates = extract_search_results(search_payload, target=target)
    selected = select_candidate(candidates, source)
    if not selected:
        return [], None

    detail_params = {
        "OC": oc,
        "target": service_target,
        "type": "JSON",
    }
    if selected.get("id"):
        detail_params["ID"] = selected["id"]
    elif selected.get("mst"):
        detail_params["MST"] = selected["mst"]
    else:
        return [], selected

    detail_payload = request_json(LAW_SERVICE_URL, detail_params)
    documents = article_documents(detail_payload, source=source, selected=selected)
    return documents, selected


def request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    full_url = f"{url}?{urlencode(params, doseq=True)}"
    request = Request(full_url, headers={"User-Agent": "StartMateAI-LegalCollector/0.1"})
    try:
        with urlopen(request, timeout=20) as response:
            text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} from {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error from {url}: {exc.reason}") from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {text[:200]}") from exc

    if isinstance(payload, dict) and payload.get("result") and payload.get("msg"):
        raise RuntimeError(str(payload.get("msg")))
    return payload


def extract_search_results(payload: dict[str, Any], *, target: str) -> list[dict[str, Any]]:
    root_key = "OrdinSearch" if target == "ordin" else "LawSearch"
    item_key = "ordin" if target == "ordin" else "law"
    root = payload.get(root_key, payload)
    raw_items = root.get(item_key, [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    results = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "name": _first(item, "법령명한글", "법령명_한글", "자치법규명", "lawNm", "ordinNm"),
                "id": _first(item, "법령ID", "ID", "자치법규ID"),
                "mst": _first(item, "법령일련번호", "MST", "자치법규일련번호"),
                "effective_date": _first(item, "시행일자"),
                "promulgation_date": _first(item, "공포일자"),
                "department": _first(item, "소관부처명", "담당부서명", "지자체기관명"),
                "raw": item,
            }
        )
    return results


def select_candidate(candidates: list[dict[str, Any]], source: dict[str, Any]) -> dict[str, Any] | None:
    if not candidates:
        return None
    expected = normalize_name(source["query"])
    exact = [candidate for candidate in candidates if normalize_name(candidate.get("name", "")) == expected]
    if exact:
        return exact[0]
    starts = [candidate for candidate in candidates if normalize_name(candidate.get("name", "")).startswith(expected)]
    if starts:
        return starts[0]
    return candidates[0]


def article_documents(
    payload: dict[str, Any],
    *,
    source: dict[str, Any],
    selected: dict[str, Any],
) -> list[dict[str, Any]]:
    records = []
    for node in walk_dicts(payload):
        title = _first(node, "조문제목", "조제목")
        content = _first(node, "조문내용", "조내용")
        article_no = _first(node, "조문번호", "조문가지번호")
        if not content or len(strip_text(content)) < 10:
            continue
        text = strip_text(" ".join(part for part in [article_label(article_no, title), content] if part))
        doc_id = stable_id(source["name"], selected.get("id") or selected.get("mst") or "", article_no or title or text[:30])
        records.append(
            {
                "id": doc_id,
                "text": text,
                "metadata": {
                    "source": "law.go.kr",
                    "source_type": source.get("source_type"),
                    "law_name": selected.get("name") or source.get("name"),
                    "query": source.get("query"),
                    "article_no": article_no,
                    "article_title": title,
                    "domains": source.get("domains", []),
                    "priority": source.get("priority"),
                    "why": source.get("why"),
                    "effective_date": selected.get("effective_date"),
                    "promulgation_date": selected.get("promulgation_date"),
                    "department": selected.get("department"),
                    "law_id": selected.get("id"),
                    "mst": selected.get("mst"),
                    "url": service_url(source, selected),
                },
            }
        )
    return dedupe_documents(records)


def build_vector_index(documents: list[dict[str, Any]], *, vector_path: Path, rebuild: bool) -> None:
    vector_docs = [
        VectorDocument(id=document["id"], text=document["text"], metadata=document.get("metadata", {}))
        for document in documents
    ]
    embedding_provider = HashEmbeddingProvider(dimensions=int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "384")))
    LocalVectorStore.from_documents(
        documents=vector_docs,
        embedding_provider=embedding_provider,
        persist_path=vector_path,
        rebuild=rebuild,
    )


def service_url(source: dict[str, Any], selected: dict[str, Any]) -> str:
    target = "ordin" if source.get("source_type") == "local_ordinance" else "eflaw"
    params = {"target": target, "type": "HTML"}
    if selected.get("id"):
        params["ID"] = selected["id"]
    elif selected.get("mst"):
        params["MST"] = selected["mst"]
    return f"{LAW_SERVICE_URL}?{urlencode(params)}"


def dedupe_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for document in documents:
        key = (document["id"], document["text"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(document)
    return unique


def walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def _first(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def article_label(article_no: str, title: str) -> str:
    pieces = []
    if article_no:
        pieces.append(f"제{int(article_no):d}조" if article_no.isdigit() else article_no)
    if title:
        pieces.append(f"({title})")
    return " ".join(pieces)


def normalize_name(value: str) -> str:
    return re.sub(r"[\sㆍ·,()]+", "", value or "").lower()


def strip_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def stable_id(*parts: str) -> str:
    clean = "_".join(re.sub(r"[^0-9A-Za-z가-힣]+", "-", part).strip("-") for part in parts if part)
    return clean[:180] or "legal-document"


def _path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


if __name__ == "__main__":
    main()
