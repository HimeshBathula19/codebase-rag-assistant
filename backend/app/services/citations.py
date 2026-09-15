from __future__ import annotations

from typing import Any

INSUFFICIENT_ANSWER = (
    "I could not find enough evidence in the indexed codebase to answer this confidently."
)


def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return not (a_end < b_start or a_start > b_end)


def citation_matches_chunk(citation: dict[str, Any], chunk: dict[str, Any]) -> bool:
    meta = chunk.get("metadata") or {}
    file_path = (citation.get("file") or citation.get("file_path") or "").replace("\\", "/")
    chunk_file = (meta.get("file_path") or "").replace("\\", "/")
    if not file_path or file_path != chunk_file:
        return False
    try:
        start = int(citation.get("start_line") or citation.get("startLine") or 0)
        end = int(citation.get("end_line") or citation.get("endLine") or 0)
    except (TypeError, ValueError):
        return False
    chunk_start = int(meta.get("start_line") or 0)
    chunk_end = int(meta.get("end_line") or 0)
    if start <= 0 or end <= 0 or chunk_start <= 0:
        return False
    return ranges_overlap(start, end, chunk_start, chunk_end)


def validate_citations(
    citations: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for citation in citations:
        matched = next((chunk for chunk in retrieved_chunks if citation_matches_chunk(citation, chunk)), None)
        if not matched:
            continue
        meta = matched.get("metadata") or {}
        file_path = meta.get("file_path") or citation.get("file")
        start = int(meta.get("start_line") or citation.get("start_line"))
        end = int(meta.get("end_line") or citation.get("end_line"))
        key = (file_path, start, end)
        if key in seen:
            continue
        seen.add(key)
        valid.append(
            {
                "file": file_path,
                "symbol": meta.get("symbol") or citation.get("symbol") or None,
                "start_line": start,
                "end_line": end,
                "snippet": (matched.get("text") or "")[:1200],
                "score": matched.get("score"),
                "language": meta.get("language") or None,
                "symbol_type": meta.get("symbol_type") or None,
            }
        )
    return valid


def evidence_is_sufficient(chunks: list[dict[str, Any]], min_score: float = 0.18, min_count: int = 1) -> bool:
    strong = [c for c in chunks if float(c.get("score") or 0) >= min_score]
    return len(strong) >= min_count


def grounded_answer(
    proposed_answer: str | None,
    validated_evidence: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]],
) -> tuple[str, bool, bool, float]:
    if not evidence_is_sufficient(retrieved_chunks) or not validated_evidence:
        return INSUFFICIENT_ANSWER, False, True, 0.0
    answer = (proposed_answer or "").strip()
    if not answer or answer == INSUFFICIENT_ANSWER:
        return INSUFFICIENT_ANSWER, False, True, 0.15
    top = max(float(c.get("score") or 0) for c in retrieved_chunks)
    confidence = min(0.97, 0.35 + 0.4 * top + 0.05 * min(len(validated_evidence), 6))
    return answer, True, False, round(confidence, 3)
