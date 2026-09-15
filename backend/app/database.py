from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import get_settings

_lock = threading.Lock()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    return get_settings().data_dir / "app.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    get_settings().ensure_dirs()
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                full_name TEXT NOT NULL,
                url TEXT NOT NULL,
                branch TEXT NOT NULL,
                analysis_mode TEXT NOT NULL,
                top_k INTEGER NOT NULL,
                commit_sha TEXT,
                default_branch TEXT,
                token_encrypted TEXT,
                status TEXT NOT NULL,
                health TEXT NOT NULL,
                last_indexed TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                stats_json TEXT NOT NULL DEFAULT '{}',
                languages_json TEXT NOT NULL DEFAULT '{}',
                warnings_json TEXT NOT NULL DEFAULT '[]',
                index_error TEXT,
                duration_ms INTEGER,
                semantic_weight REAL,
                keyword_weight REAL
            );

            CREATE TABLE IF NOT EXISTS file_index (
                repository_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                language TEXT,
                size INTEGER NOT NULL,
                PRIMARY KEY (repository_id, file_path),
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS index_jobs (
                repository_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                stage TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                error TEXT,
                started_at TEXT,
                finished_at TEXT,
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            );
            """
        )


def row_to_repo(row: sqlite3.Row, include_secret: bool = False) -> dict[str, Any]:
    data = dict(row)
    token_encrypted = data.pop("token_encrypted", None)
    data["stats"] = json.loads(data.pop("stats_json") or "{}")
    data["languages"] = json.loads(data.pop("languages_json") or "{}")
    data["warnings"] = json.loads(data.pop("warnings_json") or "[]")
    data["has_github_token"] = bool(token_encrypted)
    if include_secret:
        data["token_encrypted"] = token_encrypted
    return data


def hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
