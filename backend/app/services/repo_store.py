from __future__ import annotations

import json
from typing import Any

from app.database import get_conn, row_to_repo, utcnow
from app.security import decrypt_secret, encrypt_secret


def create_repository(record: dict[str, Any]) -> dict[str, Any]:
    now = utcnow()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO repositories (
                id, name, owner, full_name, url, branch, analysis_mode, top_k,
                commit_sha, default_branch, token_encrypted, status, health,
                last_indexed, created_at, updated_at, stats_json, languages_json,
                warnings_json, index_error, duration_ms, semantic_weight, keyword_weight
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["id"],
                record["name"],
                record["owner"],
                record["full_name"],
                record["url"],
                record["branch"],
                record["analysis_mode"],
                record["top_k"],
                record.get("commit_sha"),
                record.get("default_branch"),
                encrypt_secret(record.get("github_token")),
                record.get("status") or "pending",
                record.get("health") or "not_indexed",
                None,
                now,
                now,
                json.dumps(record.get("stats") or {}),
                json.dumps(record.get("languages") or {}),
                json.dumps(record.get("warnings") or []),
                None,
                None,
                record.get("semantic_weight"),
                record.get("keyword_weight"),
            ),
        )
        row = conn.execute("SELECT * FROM repositories WHERE id = ?", (record["id"],)).fetchone()
    return row_to_repo(row)


def list_repositories() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM repositories ORDER BY updated_at DESC").fetchall()
    return [row_to_repo(r) for r in rows]


def get_repository(repository_id: str, include_secret: bool = False) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,)).fetchone()
    if not row:
        return None
    return row_to_repo(row, include_secret=include_secret)


def find_by_full_name(full_name: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM repositories WHERE lower(full_name) = lower(?) ORDER BY created_at ASC LIMIT 1",
            (full_name,),
        ).fetchone()
    return row_to_repo(row) if row else None


def set_repository_token(repository_id: str, token: str | None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE repositories SET token_encrypted = ?, updated_at = ? WHERE id = ?",
            (encrypt_secret(token), utcnow(), repository_id),
        )


def get_repository_token(repository_id: str) -> str | None:
    repo = get_repository(repository_id, include_secret=True)
    if not repo:
        return None
    return decrypt_secret(repo.get("token_encrypted"))


def update_repository(repository_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "name",
        "owner",
        "full_name",
        "url",
        "branch",
        "analysis_mode",
        "top_k",
        "commit_sha",
        "default_branch",
        "status",
        "health",
        "last_indexed",
        "index_error",
        "duration_ms",
        "semantic_weight",
        "keyword_weight",
    }
    json_fields = {"stats": "stats_json", "languages": "languages_json", "warnings": "warnings_json"}
    assignments = []
    values: list[Any] = []
    for key, value in fields.items():
        if key in json_fields:
            assignments.append(f"{json_fields[key]} = ?")
            values.append(json.dumps(value))
        elif key in allowed:
            assignments.append(f"{key} = ?")
            values.append(value)
    if not assignments:
        return get_repository(repository_id)
    assignments.append("updated_at = ?")
    values.append(utcnow())
    values.append(repository_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE repositories SET {', '.join(assignments)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repository_id,)).fetchone()
    return row_to_repo(row) if row else None


def delete_repository(repository_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM repositories WHERE id = ?", (repository_id,))
        return cur.rowcount > 0


def upsert_job(repository_id: str, **fields: Any) -> dict[str, Any]:
    with get_conn() as conn:
        existing = conn.execute("SELECT * FROM index_jobs WHERE repository_id = ?", (repository_id,)).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO index_jobs (repository_id, status, stage, progress, message, error, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repository_id,
                    fields.get("status", "queued"),
                    fields.get("stage"),
                    fields.get("progress", 0),
                    fields.get("message"),
                    fields.get("error"),
                    fields.get("started_at") or utcnow(),
                    fields.get("finished_at"),
                ),
            )
        else:
            assignments = []
            values: list[Any] = []
            for key in ("status", "stage", "progress", "message", "error", "started_at", "finished_at"):
                if key in fields:
                    assignments.append(f"{key} = ?")
                    values.append(fields[key])
            if assignments:
                values.append(repository_id)
                conn.execute(
                    f"UPDATE index_jobs SET {', '.join(assignments)} WHERE repository_id = ?",
                    values,
                )
        row = conn.execute("SELECT * FROM index_jobs WHERE repository_id = ?", (repository_id,)).fetchone()
    return dict(row) if row else {}


def get_job(repository_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM index_jobs WHERE repository_id = ?", (repository_id,)).fetchone()
    return dict(row) if row else None


def list_file_hashes(repository_id: str) -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT file_path, sha256 FROM file_index WHERE repository_id = ?",
            (repository_id,),
        ).fetchall()
    return {r["file_path"]: r["sha256"] for r in rows}


def replace_file_hashes(repository_id: str, files: list[tuple[str, str, str | None, int]]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM file_index WHERE repository_id = ?", (repository_id,))
        conn.executemany(
            """
            INSERT INTO file_index (repository_id, file_path, sha256, language, size)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(repository_id, path, sha, lang, size) for path, sha, lang, size in files],
        )
