from __future__ import annotations

import math
import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.services import vectorstore

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text or "")]


def _keyword_search(repository_id: str, query: str, limit: int) -> list[dict[str, Any]]:
    stored = vectorstore.get_repository_chunks(repository_id)
    ids = stored.get("ids") or []
    docs = stored.get("documents") or []
    metas = stored.get("metadatas") or []
    if not ids:
        return []
    corpus = [tokenize(doc) for doc in docs]
    if not any(corpus):
        return []
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(ids)), key=lambda i: scores[i], reverse=True)[: max(limit * 3, limit)]
    max_score = max(scores) if len(scores) else 1.0
    items = []
    for i in ranked:
        raw = float(scores[i])
        norm = (raw / max_score) if max_score else 0.0
        if norm <= 0:
            continue
        items.append(
            {
                "id": ids[i],
                "text": docs[i],
                "score": norm,
                "keyword_score": norm,
                "metadata": metas[i],
            }
        )
        if len(items) >= limit:
            break
    return items


def hybrid_search(
    repository_id: str,
    query: str,
    top_k: int,
    mode: str = "hybrid",
    semantic_weight: float | None = None,
    keyword_weight: float | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    sem_w = settings.semantic_weight if semantic_weight is None else semantic_weight
    key_w = settings.keyword_weight if keyword_weight is None else keyword_weight
    total = sem_w + key_w
    if total <= 0:
        sem_w, key_w = 0.7, 0.3
        total = 1.0
    sem_w, key_w = sem_w / total, key_w / total

    fetch = max(top_k * 4, top_k)
    semantic_items = [] if mode == "keyword" else vectorstore.query_semantic(repository_id, query, fetch)
    keyword_items = [] if mode == "semantic" else _keyword_search(repository_id, query, fetch)

    by_id: dict[str, dict[str, Any]] = {}
    for item in semantic_items:
        by_id[item["id"]] = {
            **item,
            "semantic_score": item["score"],
            "keyword_score": 0.0,
        }
    for item in keyword_items:
        existing = by_id.get(item["id"])
        if existing:
            existing["keyword_score"] = item["score"]
            existing["text"] = existing.get("text") or item["text"]
            existing["metadata"] = existing.get("metadata") or item["metadata"]
        else:
            by_id[item["id"]] = {
                **item,
                "semantic_score": 0.0,
                "keyword_score": item["score"],
            }

    merged = []
    for item in by_id.values():
        if mode == "keyword":
            score = item["keyword_score"]
        elif mode == "semantic":
            score = item["semantic_score"]
        else:
            score = sem_w * item["semantic_score"] + key_w * item["keyword_score"]
        item["score"] = float(score)
        item["semantic_weight"] = sem_w
        item["keyword_weight"] = key_w
        merged.append(item)

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]


def result_to_evidence(item: dict[str, Any]) -> dict[str, Any]:
    meta = item.get("metadata") or {}
    start = int(meta.get("start_line") or 1)
    end = int(meta.get("end_line") or start)
    snippet = item.get("text") or ""
    lines = snippet.splitlines()
    if len(lines) > 12:
        snippet = "\n".join(lines[:12]) + "\n…"
    return {
        "file": meta.get("file_path") or "",
        "symbol": meta.get("symbol") or None,
        "start_line": start,
        "end_line": end,
        "snippet": snippet,
        "score": round(float(item.get("score") or 0), 4),
        "language": meta.get("language") or None,
        "symbol_type": meta.get("symbol_type") or None,
    }
