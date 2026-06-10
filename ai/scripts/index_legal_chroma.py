from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import chromadb
from chromadb.config import Settings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.rag.embeddings import get_embedding_provider
from app.rag.legal_retriever import LegalRetriever


DEFAULT_COLLECTION = "legal_sources"


def main() -> None:
    parser = argparse.ArgumentParser(description="Index collected legal documents into embedded Chroma.")
    parser.add_argument("--input", default="app/data/legal_documents.json")
    parser.add_argument("--chroma-path", default="")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--dimensions", type=int, default=3072)
    parser.add_argument("--embedding-provider", default="", help="hash or openai. Defaults to RAG_EMBEDDING_PROVIDER.")
    parser.add_argument("--embedding-cache", default=".rag_index/legal_embeddings.cache.json")
    parser.add_argument("--embedding-workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild the Chroma collection.")
    parser.add_argument("--query", default="쿠키 팝업 영업신고 시설기준")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    chroma_path = Path(args.chroma_path or get_settings().rag_chroma_path)
    documents = json.loads(input_path.read_text(encoding="utf-8"))

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

    settings = get_settings()
    provider_name = args.embedding_provider or settings.rag_embedding_provider
    embedding_provider = get_embedding_provider(provider_name, dimensions=args.dimensions)
    records = normalize_documents(documents)
    existing_ids = set(collection.get(include=[])["ids"]) if not args.reset and collection.count() else set()
    pending_records = [record for record in records if record["id"] not in existing_ids]

    if pending_records:
        print(f"Indexing {len(pending_records)} pending chunks ({len(existing_ids)} already indexed).")
        embedding_cache_path = resolve_path(args.embedding_cache)
        embedding_cache = load_embedding_cache(embedding_cache_path)
        indexed = 0
        for batch in batched(pending_records, args.batch_size):
            ids = [record["id"] for record in batch]
            texts = [record["text"] for record in batch]
            metadatas = [record["metadata"] for record in batch]
            embeddings = embed_texts(
                texts,
                embedding_provider=embedding_provider,
                cache=embedding_cache,
                provider_name=provider_name,
                workers=args.embedding_workers,
            )
            save_embedding_cache(embedding_cache_path, embedding_cache)
            collection.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
            indexed += len(batch)
            print(f"Indexed batch: {indexed}/{len(pending_records)} pending")
    else:
        print("Collection already has all source documents. Use --reset to rebuild it.")

    print(f"Indexed {collection.count()} legal chunks into {chroma_path / args.collection}")

    if args.query:
        retriever = LegalRetriever(
            chroma_path=chroma_path,
            collection_name=args.collection,
            embedding_dimensions=args.dimensions,
            embedding_provider=provider_name,
        )
        print(f"\nQuery: {args.query}")
        for index, result in enumerate(retriever.search(args.query, top_k=args.top_k), start=1):
            law_name = result.metadata.get("law_name", "-")
            article = result.metadata.get("article_no", "-")
            title = result.metadata.get("article_title", "")
            print(f"{index}. {law_name} {article} {title} score={result.score}")
            print(f"   {result.text[:180]}")


def normalize_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    seen: dict[str, int] = {}
    for document in documents:
        base_id = str(document.get("id") or "").strip() or f"legal-{len(normalized)}"
        seen[base_id] = seen.get(base_id, 0) + 1
        doc_id = base_id if seen[base_id] == 1 else f"{base_id}-{seen[base_id]}"
        metadata = chroma_metadata(document.get("metadata") or {})
        normalized.append(
            {
                "id": doc_id,
                "text": str(document.get("text") or ""),
                "metadata": metadata,
            }
        )
    return normalized


def chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    converted: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, list):
            converted[key] = ",".join(str(item) for item in value)
        elif isinstance(value, (str, int, float, bool)):
            converted[key] = value
        else:
            converted[key] = json.dumps(value, ensure_ascii=False)
    return converted


def embed_texts(
    texts: list[str],
    *,
    embedding_provider: Any,
    cache: dict[str, list[float]],
    provider_name: str,
    workers: int,
) -> list[list[float]]:
    keys = [embedding_cache_key(text, provider_name=provider_name) for text in texts]
    embeddings: list[list[float] | None] = [cache.get(key) for key in keys]
    missing = [(index, text, keys[index]) for index, text in enumerate(texts) if embeddings[index] is None]
    if not missing:
        return [embedding for embedding in embeddings if embedding is not None]

    if hasattr(embedding_provider, "embed_many") and len(missing) > 1:
        missing_texts = [text for _, text, _ in missing]
        batch_embeddings = embedding_provider.embed_many(
            missing_texts,
            batch_size=max(1, min(len(missing_texts), 64)),
        )
        for (index, _, key), embedding in zip(missing, batch_embeddings, strict=False):
            cache[key] = embedding
            embeddings[index] = embedding
    elif workers <= 1 or len(missing) == 1:
        for index, text, key in missing:
            embedding = embedding_provider.embed(text)
            cache[key] = embedding
            embeddings[index] = embedding
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(embedding_provider.embed, text): (index, key)
                for index, text, key in missing
            }
            for future in as_completed(futures):
                index, key = futures[future]
                embedding = future.result()
                cache[key] = embedding
                embeddings[index] = embedding

    return [embedding for embedding in embeddings if embedding is not None]


def embedding_cache_key(text: str, *, provider_name: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{provider_name or 'default'}:{digest}"


def load_embedding_cache(path: Path) -> dict[str, list[float]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_embedding_cache(path: Path, cache: dict[str, list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def batched(items: list[dict[str, Any]], batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


if __name__ == "__main__":
    main()
