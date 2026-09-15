from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.database import hash_bytes, utcnow
from app.errors import AppError
from app.services import repo_store, vectorstore
from app.services.architecture import build_architecture, parse_manifest_dependencies
from app.services.chunking import chunk_parsed_file
from app.services.filtering import language_for_path, should_skip_file
from app.services.github import parse_github_url
from app.services.git_clone import clone_github_repository
from app.services.insights import build_insights
from app.services.parsing import parse_source

logger = logging.getLogger("codebase_rag.indexer")


def checkout_path(repository_id: str) -> Path:
    return get_settings().repos_dir / repository_id / "checkout"


def artifacts_path(repository_id: str) -> Path:
    return get_settings().repos_dir / repository_id / "artifacts"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _analysis_limits(mode: str) -> dict[str, int]:
    if mode == "quick":
        return {"max_bytes": 200_000, "max_files": 400, "chunk_max": 60, "overlap": 6}
    if mode == "deep":
        return {"max_bytes": 1_500_000, "max_files": 4000, "chunk_max": 100, "overlap": 12}
    return {"max_bytes": 1_000_000, "max_files": 1500, "chunk_max": 80, "overlap": 8}


def run_index(repository_id: str, reindex: bool = False) -> None:
    started = time.perf_counter()
    repo = repo_store.get_repository(repository_id)
    if not repo:
        return
    token = repo_store.get_repository_token(repository_id)
    try:
        repo_store.upsert_job(
            repository_id,
            status="running",
            stage="detecting",
            progress=5,
            message="Detecting GitHub repository",
            error=None,
            started_at=utcnow(),
            finished_at=None,
        )
        repo_store.update_repository(repository_id, status="indexing", health="indexing", index_error=None)
        ref = parse_github_url(repo["url"])
        requested_branch = (repo.get("branch") or "").strip() or None
        repo_store.upsert_job(repository_id, stage="discovering", progress=15, message="Cloning repository with git")
        dest_root = get_settings().repos_dir / repository_id
        dest_root.mkdir(parents=True, exist_ok=True)
        checkout = checkout_path(repository_id)
        meta = clone_github_repository(ref, checkout, requested_branch, token)
        repo_store.update_repository(
            repository_id,
            name=meta.repo,
            owner=meta.owner,
            full_name=meta.full_name,
            default_branch=meta.default_branch,
            branch=meta.branch,
            commit_sha=meta.commit_sha,
        )
        limits = _analysis_limits(repo.get("analysis_mode") or "standard")
        repo_store.upsert_job(repository_id, stage="filtering", progress=30, message="Discovering and filtering files")
        all_files = [p for p in checkout.rglob("*") if p.is_file()]
        if not all_files:
            raise AppError("empty_repository", "The repository contains no files to index.", 400)

        skipped: list[dict[str, str]] = []
        warnings: list[str] = []
        kept: list[Path] = []
        for path in all_files:
            rel = path.relative_to(checkout)
            skip, reason = should_skip_file(rel, path.stat().st_size, limits["max_bytes"])
            if skip:
                skipped.append({"file": rel.as_posix(), "reason": reason or "skipped"})
                continue
            kept.append(path)
        if len(kept) > limits["max_files"]:
            warnings.append(f"File cap reached for {repo.get('analysis_mode')} mode; indexing first {limits['max_files']} files.")
            extra = kept[limits["max_files"] :]
            kept = kept[: limits["max_files"]]
            for path in extra:
                skipped.append({"file": path.relative_to(checkout).as_posix(), "reason": "analysis_mode_cap"})

        previous_hashes = repo_store.list_file_hashes(repository_id) if reindex else {}
        current_map: dict[str, tuple[Path, str, str | None, int]] = {}
        for path in kept:
            rel = path.relative_to(checkout).as_posix()
            data = path.read_bytes()
            current_map[rel] = (path, hash_bytes(data), language_for_path(rel), len(data))

        deleted = set(previous_hashes) - set(current_map)
        unchanged = {p for p, (_path, sha, _lang, _size) in current_map.items() if previous_hashes.get(p) == sha}
        changed = [p for p in current_map if p not in unchanged]

        if not reindex:
            vectorstore.delete_repository_chunks(repository_id)
            unchanged = set()
            changed = list(current_map)
            deleted = set()
        else:
            for file_path in deleted:
                vectorstore.delete_file_chunks(repository_id, file_path)
            for file_path in changed:
                vectorstore.delete_file_chunks(repository_id, file_path)

        repo_store.upsert_job(repository_id, stage="parsing", progress=45, message="Parsing files and extracting symbols")
        chunks_all = []
        functions = classes = methods = 0
        languages: dict[str, int] = {}
        parsed_symbol_records: list[dict[str, Any]] = []
        relative_files = list(current_map.keys())

        to_process = changed if reindex else list(current_map)
        for idx, rel in enumerate(to_process):
            path, _sha, language, _size = current_map[rel]
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                warnings.append(f"Could not read {rel}")
                continue
            parsed = parse_source(rel, source, language)
            if parsed.warning == "unsupported_language":
                warnings.append(f"Unsupported or unparsed language for {rel}")
            if parsed.warning and parsed.warning.startswith("parser_failure"):
                warnings.append(f"Parser failure for {rel}")
            for symbol in parsed.symbols:
                if symbol.symbol_type == "function":
                    functions += 1
                elif symbol.symbol_type == "class":
                    classes += 1
                elif symbol.symbol_type == "method":
                    methods += 1
                parsed_symbol_records.append(
                    {"file": rel, "name": symbol.name, "type": symbol.symbol_type, "start": symbol.start_line}
                )
            file_chunks = chunk_parsed_file(
                parsed,
                source,
                repository_id=repository_id,
                repository_name=meta.full_name,
                commit_sha=meta.commit_sha,
                max_lines=limits["chunk_max"],
                overlap=limits["overlap"],
            )
            chunks_all.extend(file_chunks)
            lang_key = parsed.language or language or "unknown"
            languages[lang_key] = languages.get(lang_key, 0) + 1
            if idx % 25 == 0:
                repo_store.upsert_job(
                    repository_id,
                    stage="chunking",
                    progress=45 + int(25 * (idx + 1) / max(len(to_process), 1)),
                    message=f"Chunking {idx + 1}/{len(to_process)} changed files",
                )

        repo_store.upsert_job(repository_id, stage="embedding", progress=75, message="Generating embeddings")
        try:
            embedded = vectorstore.upsert_chunks(chunks_all)
        except AppError:
            raise
        except Exception as exc:
            raise AppError("embedding_failure", f"Embedding generation failed: {exc}", 500) from exc

        repo_store.upsert_job(repository_id, stage="dependencies", progress=88, message="Analyzing dependencies")
        graph = build_architecture(checkout, relative_files)
        insights = build_insights(checkout, relative_files, parsed_symbol_records)
        artifacts = artifacts_path(repository_id)
        _write_json(artifacts / "architecture.json", graph)
        _write_json(artifacts / "insights.json", insights)
        _write_json(artifacts / "skipped.json", skipped)

        chunk_count = vectorstore.count_repository_chunks(repository_id)
        duration_ms = int((time.perf_counter() - started) * 1000)
        stats = {
            "files": len(relative_files),
            "functions": functions if not reindex else None,
            "classes": classes if not reindex else None,
            "methods": methods if not reindex else None,
            "chunks": chunk_count,
            "embeddings": chunk_count,
            "dependencies": sum(len(v) for v in parse_manifest_dependencies(checkout).values()),
            "internal_edges": len(graph.get("edges") or []),
            "modules": len(insights.get("major_modules") or []),
            "entry_points": len(insights.get("entry_points") or []),
            "skipped_files": len(skipped),
            "files_reprocessed": len(to_process),
            "files_unchanged": len(unchanged),
            "files_deleted": len(deleted),
            "commit": meta.commit_sha,
            "branch": meta.branch,
        }
        # On incremental reindex, recount symbols from current checkout for accurate totals
        if reindex:
            functions = classes = methods = 0
            languages = {}
            for rel, (path, _sha, language, _size) in current_map.items():
                source = path.read_text(encoding="utf-8", errors="replace")
                parsed = parse_source(rel, source, language)
                languages[parsed.language or language or "unknown"] = (
                    languages.get(parsed.language or language or "unknown", 0) + 1
                )
                for symbol in parsed.symbols:
                    if symbol.symbol_type == "function":
                        functions += 1
                    elif symbol.symbol_type == "class":
                        classes += 1
                    elif symbol.symbol_type == "method":
                        methods += 1
            stats["functions"] = functions
            stats["classes"] = classes
            stats["methods"] = methods

        repo_store.replace_file_hashes(
            repository_id,
            [(rel, sha, lang, size) for rel, (_p, sha, lang, size) in current_map.items()],
        )
        repo_store.update_repository(
            repository_id,
            status="ready",
            health="ready",
            last_indexed=utcnow(),
            commit_sha=meta.commit_sha,
            stats=stats,
            languages=languages,
            warnings=warnings[:200],
            duration_ms=duration_ms,
            index_error=None,
        )
        repo_store.upsert_job(
            repository_id,
            status="completed",
            stage="ready",
            progress=100,
            message=f"Indexed {embedded} new/updated chunks",
            error=None,
            finished_at=utcnow(),
        )
        logger.info("Indexed repository %s commit %s", repository_id, meta.commit_sha)
    except AppError as exc:
        logger.warning("Index failed for %s: %s", repository_id, exc.message)
        repo_store.update_repository(repository_id, status="failed", health="error", index_error=exc.message)
        repo_store.upsert_job(
            repository_id,
            status="failed",
            stage="failed",
            progress=100,
            message=exc.message,
            error=exc.code,
            finished_at=utcnow(),
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected index failure")
        repo_store.update_repository(repository_id, status="failed", health="error", index_error=str(exc))
        repo_store.upsert_job(
            repository_id,
            status="failed",
            stage="failed",
            progress=100,
            message="Unexpected indexing failure",
            error=type(exc).__name__,
            finished_at=utcnow(),
        )
