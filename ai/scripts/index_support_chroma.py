from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.rag.embeddings import get_embedding_provider


DEFAULT_COLLECTION = "support_programs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Index backend support programs into Chroma.")
    parser.add_argument("--input", default="", help="Optional JSON file. If omitted, fetch from backend.")
    parser.add_argument("--backend-url", default="", help="Backend base URL. Defaults to BACKEND_INTERNAL_BASE_URL.")
    parser.add_argument("--token", default="", help="Internal tool token. Defaults to STARTMATE_INTERNAL_TOOL_TOKEN.")
    parser.add_argument("--sync", action="store_true", help="Call backend support-program sync before export.")
    parser.add_argument("--source", default="all", help="Sync source: all, kstartup, bizinfo, youthcenter.")
    parser.add_argument("--out", default="app/data/support_programs.backend.json")
    parser.add_argument("--chroma-path", default="")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--embedding-provider", default="", help="hash or openai. Defaults to RAG_EMBEDDING_PROVIDER.")
    parser.add_argument("--dimensions", type=int, default=3072)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    settings = get_settings()
    programs = load_programs(args, settings)
    write_snapshot(programs, args.out)

    chroma_path = Path(args.chroma_path or settings.support_rag_chroma_path)
    provider_name = args.embedding_provider or settings.rag_embedding_provider
    embedding_provider = get_embedding_provider(provider_name, dimensions=args.dimensions)
    client = chromadb.PersistentClient(
        path=str(chroma_path),
        settings=Settings(anonymized_telemetry=False),
    )
    if args.reset:
        try:
            client.delete_collection(args.collection)
        except Exception:
            pass
    collection = client.get_or_create_collection(name=args.collection, metadata={"hnsw:space": "cosine"})

    documents = normalize_programs(programs)
    if not documents:
        print("No support programs to index.")
        return

    existing_ids = set(collection.get(include=[])["ids"]) if not args.reset and collection.count() else set()
    pending = [document for document in documents if document["id"] not in existing_ids]
    if not pending:
        print(f"Collection already has all {len(documents)} support program chunks.")
        return

    indexed = 0
    for batch in batched(pending, args.batch_size):
        texts = [item["text"] for item in batch]
        embeddings = embedding_provider.embed_many(texts, batch_size=min(args.batch_size, 64)) if hasattr(embedding_provider, "embed_many") else [
            embedding_provider.embed(text) for text in texts
        ]
        collection.upsert(
            ids=[item["id"] for item in batch],
            documents=texts,
            metadatas=[item["metadata"] for item in batch],
            embeddings=embeddings,
        )
        indexed += len(batch)
        print(f"Indexed support batch: {indexed}/{len(pending)} pending")

    print(f"Indexed {collection.count()} support program chunks into {chroma_path / args.collection}")


def load_programs(args: argparse.Namespace, settings) -> list[dict[str, Any]]:
    if args.input:
        path = resolve_path(args.input)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else payload.get("items", [])

    base_url = (args.backend_url or settings.backend_internal_base_url).rstrip("/")
    token = args.token or settings.internal_tool_token
    if not base_url or not token:
        raise RuntimeError("Backend URL and internal token are required.")

    headers = {"X-Startmate-Internal-Token": token}
    with httpx.Client(timeout=settings.backend_tool_timeout_seconds) as client:
        if args.sync:
            sync_response = client.post(
                f"{base_url}/api/internal/ai-tools/support-programs/sync",
                headers=headers,
                params={"source": args.source},
                json={},
            )
            sync_response.raise_for_status()
            print(f"Synced support programs: {sync_response.json()}")

        response = client.get(f"{base_url}/api/internal/ai-tools/support-programs", headers=headers)
        response.raise_for_status()
        payload = response.json()
    return payload if isinstance(payload, list) else []


def normalize_programs(programs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    documents = []
    for index, program in enumerate(programs):
        title = text(program.get("title"))
        if not title:
            continue
        program_id = text(program.get("programId") or program.get("id") or program.get("sourceId") or index)
        body = program_text(program)
        documents.append(
            {
                "id": f"support:{stable_id(program_id + title)}",
                "text": body,
                "metadata": metadata(program, program_id=program_id, title=title),
            }
        )
    return documents


def program_text(program: dict[str, Any]) -> str:
    fields = [
        ("지원사업명", program.get("title")),
        ("요약", program.get("summary")),
        ("본문", program.get("content")),
        ("지원유형", program.get("supportType")),
        ("지원금", program.get("supportAmount")),
        ("대상", program.get("target")),
        ("연령조건", program.get("ageCondition")),
        ("창업단계", program.get("businessStageCondition")),
        ("지역조건", program.get("regionCondition")),
        ("업종조건", program.get("industryCondition")),
        ("주관기관", program.get("organization")),
        ("부서", program.get("department")),
        ("신청기간", f"{text(program.get('applicationStartDate'))} ~ {text(program.get('applicationEndDate'))}"),
        ("상태", program.get("status")),
        ("필수서류", program.get("requiredDocuments")),
        ("태그", program.get("tags")),
    ]
    return "\n".join(f"{label}: {text(value)}" for label, value in fields if text(value))


def metadata(program: dict[str, Any], *, program_id: str, title: str) -> dict[str, str | int | float | bool]:
    values = {
        "program_id": program_id,
        "source": program.get("source"),
        "source_id": program.get("sourceId"),
        "title": title,
        "summary": program.get("summary"),
        "category": program.get("category"),
        "support_type": program.get("supportType"),
        "target": program.get("target"),
        "age_condition": program.get("ageCondition"),
        "business_stage_condition": program.get("businessStageCondition"),
        "region_condition": program.get("regionCondition"),
        "industry_condition": program.get("industryCondition"),
        "organization": program.get("organization"),
        "department": program.get("department"),
        "contact": program.get("contact"),
        "application_start_date": program.get("applicationStartDate"),
        "application_end_date": program.get("applicationEndDate"),
        "status": program.get("status"),
        "support_amount": program.get("supportAmount"),
        "required_documents": program.get("requiredDocuments"),
        "apply_url": program.get("applyUrl"),
        "detail_url": program.get("detailUrl"),
        "source_url": program.get("sourceUrl"),
        "tags": program.get("tags"),
    }
    return {key: text(value) for key, value in values.items() if text(value)}


def write_snapshot(programs: list[dict[str, Any]], out: str) -> None:
    path = resolve_path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(programs, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote support snapshot: {path}")


def batched(items: list[dict[str, Any]], batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


if __name__ == "__main__":
    main()
