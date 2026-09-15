from __future__ import annotations

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.errors import AppError
from app.services.chunking import SemanticChunk
from app.services.embeddings import get_embedder

COLLECTION = "code_chunks"


def get_chroma_client() -> chromadb.PersistentClient:
    path = str(get_settings().chroma_dir)
    return chromadb.PersistentClient(
        path=path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(chunks: list[SemanticChunk]) -> int:
    if not chunks:
        return 0
    try:
        collection = get_collection()
        embedder = get_embedder()
        texts = [c.text for c in chunks]
        embeddings = embedder.encode(texts)
        collection.upsert(
            ids=[c.id for c in chunks],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c.metadata() for c in chunks],
        )
        return len(chunks)
    except Exception as exc:
        raise AppError("chromadb_failure", f"Failed to write embeddings: {exc}", 500) from exc


def delete_repository_chunks(repository_id: str) -> None:
    collection = get_collection()
    try:
        collection.delete(where={"repository_id": repository_id})
    except Exception:
        # Collection may be empty
        pass


def delete_file_chunks(repository_id: str, file_path: str) -> None:
    collection = get_collection()
    try:
        collection.delete(where={"$and": [{"repository_id": repository_id}, {"file_path": file_path}]})
    except Exception:
        pass


def count_repository_chunks(repository_id: str) -> int:
    collection = get_collection()
    result = collection.get(where={"repository_id": repository_id}, include=[])
    return len(result.get("ids") or [])


def get_repository_chunks(repository_id: str) -> dict[str, Any]:
    collection = get_collection()
    return collection.get(
        where={"repository_id": repository_id},
        include=["documents", "metadatas"],
    )


def query_semantic(repository_id: str, query: str, n_results: int) -> list[dict[str, Any]]:
    try:
        collection = get_collection()
        embedder = get_embedder()
        vector = embedder.encode([query])[0]
        result = collection.query(
            query_embeddings=[vector],
            n_results=max(n_results, 1),
            where={"repository_id": repository_id},
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        raise AppError("chromadb_failure", f"Semantic search failed: {exc}", 500) from exc

    items: list[dict[str, Any]] = []
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    for i, chunk_id in enumerate(ids):
        distance = float(distances[i]) if i < len(distances) else 1.0
        score = max(0.0, 1.0 - distance)
        meta = metas[i] if i < len(metas) else {}
        items.append(
            {
                "id": chunk_id,
                "text": docs[i] if i < len(docs) else "",
                "score": score,
                "metadata": meta,
            }
        )
    return items
