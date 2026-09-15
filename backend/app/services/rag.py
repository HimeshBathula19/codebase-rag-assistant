from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.errors import AppError
from app.services.citations import INSUFFICIENT_ANSWER, grounded_answer, validate_citations
from app.services.retrieval import hybrid_search, result_to_evidence
from app.services import repo_store

logger = logging.getLogger("codebase_rag.rag")


def _pipeline_flow(query: str, top_k: int, mode: str) -> list[dict[str, Any]]:
    return [
        {"step": "query", "detail": query},
        {"step": "retrieval", "detail": f"{mode} search with top_k={top_k}"},
        {"step": "ranking", "detail": "Merge semantic cosine similarity with BM25 keyword scores"},
        {"step": "context", "detail": "Build grounded context only from retrieved chunks"},
        {"step": "llm", "detail": "Generate or extract an answer strictly from retrieved context"},
        {"step": "grounding_validation", "detail": "Reject answers without sufficient retrieved evidence"},
        {"step": "citation_validation", "detail": "Keep citations only if they match retrieved file/line ranges"},
        {"step": "structured_answer", "detail": "Return answer, evidence, related files, and confidence"},
    ]


def _extractive_answer(query: str, chunks: list[dict[str, Any]]) -> str | None:
    if not chunks:
        return None
    parts = []
    for item in chunks[:4]:
        meta = item.get("metadata") or {}
        symbol = meta.get("symbol") or "file"
        parts.append(
            f"{meta.get('file_path')} ({symbol} lines {meta.get('start_line')}-{meta.get('end_line')}):\n{(item.get('text') or '')[:500]}"
        )
    return (
        "Based only on retrieved indexed chunks, the most relevant code is:\n\n"
        + "\n\n".join(parts)
        + f"\n\nThe question was: {query}"
    )


def _call_llm(query: str, chunks: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    settings = get_settings()
    if not settings.llm_api_key:
        return _extractive_answer(query, chunks), [result_to_evidence(c) for c in chunks]
    context_blocks = []
    for item in chunks:
        meta = item.get("metadata") or {}
        context_blocks.append(
            {
                "file": meta.get("file_path"),
                "symbol": meta.get("symbol"),
                "start_line": meta.get("start_line"),
                "end_line": meta.get("end_line"),
                "text": item.get("text"),
            }
        )
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You answer questions about a software repository. "
                    "Use only the provided evidence chunks. "
                    "If evidence is insufficient, reply with exactly: "
                    f"{INSUFFICIENT_ANSWER} "
                    "Return JSON with keys answer and citations. "
                    "Each citation must have file, symbol, start_line, end_line copied from evidence. "
                    "Never invent files, symbols, or line numbers."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"question": query, "evidence": context_blocks}),
            },
        ],
        "response_format": {"type": "json_object"},
    }
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise AppError("llm_failure", "The language model request failed.", 502)
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("answer"), parsed.get("citations") or []
    except AppError:
        raise
    except Exception as exc:
        logger.warning("LLM call failed: %s", type(exc).__name__)
        raise AppError("llm_failure", "The language model request failed.", 502) from exc


def ask_repository(repository_id: str, query: str, top_k: int | None = None) -> dict[str, Any]:
    repo = repo_store.get_repository(repository_id)
    if not repo:
        raise AppError("not_found", "Repository not found.", 404)
    if repo.get("status") != "ready":
        raise AppError("not_indexed", "Repository is not indexed yet.", 409)
    settings = get_settings()
    k = top_k or repo.get("top_k") or settings.default_top_k
    sem_w = repo.get("semantic_weight")
    key_w = repo.get("keyword_weight")
    chunks = hybrid_search(
        repository_id,
        query,
        top_k=k,
        mode="hybrid",
        semantic_weight=sem_w,
        keyword_weight=key_w,
    )
    how = [
        "Hybrid retrieval mixes dense embeddings (sentence-transformers/all-MiniLM-L6-v2) with BM25 keyword search.",
        f"Semantic weight={sem_w if sem_w is not None else settings.semantic_weight}, keyword weight={key_w if key_w is not None else settings.keyword_weight}.",
        "Answers are grounded: citations must match retrieved chunk file paths and overlapping line ranges.",
        "If retrieved evidence is weak or citations cannot be validated, no answer is invented.",
    ]
    flow = _pipeline_flow(query, k, "hybrid")
    evidence_from_retrieval = [result_to_evidence(c) for c in chunks]
    llm_citations = [result_to_evidence(c) for c in chunks]
    proposed = None
    settings = get_settings()
    if settings.llm_api_key:
        try:
            proposed, llm_citations_raw = _call_llm(query, chunks)
            if isinstance(llm_citations_raw, list) and llm_citations_raw:
                llm_citations = llm_citations_raw
        except AppError:
            raise
    else:
        proposed = _extractive_answer(query, chunks)

    validated = validate_citations(llm_citations, chunks)
    if not validated:
        validated = validate_citations(evidence_from_retrieval, chunks)
    answer, grounded, insufficient, confidence = grounded_answer(proposed, validated, chunks)
    if insufficient:
        validated = []
        answer = INSUFFICIENT_ANSWER
    related = []
    for item in validated or evidence_from_retrieval:
        file_path = item.get("file")
        if file_path and file_path not in related:
            related.append(file_path)
    return {
        "answer": answer,
        "confidence": 0.0 if insufficient else confidence,
        "how_it_works": how,
        "execution_flow": flow,
        "evidence": [] if insufficient else validated,
        "related_files": [] if insufficient else related[:12],
        "grounded": grounded,
        "insufficient_evidence": insufficient,
    }
