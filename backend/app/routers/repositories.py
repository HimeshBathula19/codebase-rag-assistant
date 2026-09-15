from __future__ import annotations

import threading
import uuid
from pathlib import Path, PurePosixPath

from fastapi import APIRouter

from app.config import get_settings
from app.errors import AppError
from app.schemas import AskRequest, RepositoryCreate, SearchRequest
from app.services import repo_store, vectorstore
from app.services.github import parse_github_url
from app.services.git_clone import _git_executable
from app.services.indexer import artifacts_path, checkout_path, run_index
from app.services.rag import ask_repository
from app.services.retrieval import hybrid_search, result_to_evidence

router = APIRouter(prefix="/repositories", tags=["repositories"])
_index_lock = threading.Lock()
_running: set[str] = set()


def _public_repo(repo: dict) -> dict:
    return {k: v for k, v in repo.items() if k != "token_encrypted"}


def _ensure_repo(repository_id: str) -> dict:
    repo = repo_store.get_repository(repository_id)
    if not repo:
        raise AppError("not_found", "Repository not found.", 404)
    return repo


def _schedule_index(repository_id: str, reindex: bool) -> None:
    with _index_lock:
        if repository_id in _running:
            raise AppError("index_in_progress", "An indexing job is already running for this repository.", 409)
        _running.add(repository_id)

    def _job() -> None:
        try:
            run_index(repository_id, reindex=reindex)
        finally:
            with _index_lock:
                _running.discard(repository_id)

    thread = threading.Thread(target=_job, daemon=True)
    thread.start()


def _build_tree(root: Path) -> list[dict]:
    def walk(directory: Path) -> list[dict]:
        children = []
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return []
        for entry in entries:
            if entry.name in {".git"}:
                continue
            rel = entry.relative_to(root).as_posix()
            if entry.is_dir():
                children.append({"name": entry.name, "path": rel, "type": "directory", "children": walk(entry)})
            else:
                children.append(
                    {
                        "name": entry.name,
                        "path": rel,
                        "type": "file",
                        "size": entry.stat().st_size,
                    }
                )
        return children

    return walk(root)


@router.get("")
def list_repositories():
    return [_public_repo(r) for r in repo_store.list_repositories()]


@router.post("", status_code=201)
def create_repository(body: RepositoryCreate):
    ref = parse_github_url(body.url)
    _git_executable()
    token = body.github_token or None
    settings = get_settings()
    existing = repo_store.find_by_full_name(ref.full_name)
    if existing:
        updates = {
            "name": ref.repo,
            "owner": ref.owner,
            "full_name": ref.full_name,
            "url": ref.html_url,
            "analysis_mode": body.analysis_mode,
            "top_k": body.top_k,
            "semantic_weight": body.semantic_weight if body.semantic_weight is not None else existing.get("semantic_weight") or settings.semantic_weight,
            "keyword_weight": body.keyword_weight if body.keyword_weight is not None else existing.get("keyword_weight") or settings.keyword_weight,
        }
        if body.branch:
            updates["branch"] = body.branch
        repo_store.update_repository(existing["id"], **updates)
        if token:
            repo_store.set_repository_token(existing["id"], token)
        repo_store.upsert_job(existing["id"], status="queued", stage="queued", progress=0, message="Waiting to index")
        try:
            _schedule_index(existing["id"], True)
        except AppError as exc:
            if exc.code != "index_in_progress":
                raise
        return _public_repo(repo_store.get_repository(existing["id"]))

    repo_id = str(uuid.uuid4())
    record = {
        "id": repo_id,
        "name": ref.repo,
        "owner": ref.owner,
        "full_name": ref.full_name,
        "url": ref.html_url,
        "branch": (body.branch or "").strip() or "",
        "analysis_mode": body.analysis_mode,
        "top_k": body.top_k,
        "commit_sha": None,
        "default_branch": None,
        "github_token": token,
        "status": "pending",
        "health": "not_indexed",
        "semantic_weight": body.semantic_weight if body.semantic_weight is not None else settings.semantic_weight,
        "keyword_weight": body.keyword_weight if body.keyword_weight is not None else settings.keyword_weight,
    }
    created = repo_store.create_repository(record)
    repo_store.upsert_job(repo_id, status="queued", stage="queued", progress=0, message="Waiting to index")
    _schedule_index(repo_id, False)
    return _public_repo(created)


@router.get("/{repository_id}")
def get_repository(repository_id: str):
    return _public_repo(_ensure_repo(repository_id))


@router.delete("/{repository_id}")
def delete_repository(repository_id: str):
    _ensure_repo(repository_id)
    vectorstore.delete_repository_chunks(repository_id)
    repo_store.delete_repository(repository_id)
    checkout = get_settings().repos_dir / repository_id
    import shutil

    shutil.rmtree(checkout, ignore_errors=True)
    return {"deleted": True, "id": repository_id}


@router.post("/{repository_id}/index")
def index_repository(repository_id: str):
    _ensure_repo(repository_id)
    _schedule_index(repository_id, reindex=False)
    return repo_store.get_job(repository_id)


@router.post("/{repository_id}/reindex")
def reindex_repository(repository_id: str):
    _ensure_repo(repository_id)
    _schedule_index(repository_id, reindex=True)
    return repo_store.get_job(repository_id)


@router.get("/{repository_id}/index/status")
def index_status(repository_id: str):
    _ensure_repo(repository_id)
    job = repo_store.get_job(repository_id)
    if not job:
        return {"status": "idle", "progress": 0, "stage": None, "message": None}
    return job


@router.post("/{repository_id}/ask")
def ask(repository_id: str, body: AskRequest):
    return ask_repository(repository_id, body.query, body.top_k)


@router.post("/{repository_id}/search")
def search(repository_id: str, body: SearchRequest):
    repo = _ensure_repo(repository_id)
    if repo.get("status") != "ready":
        raise AppError("not_indexed", "Repository is not indexed yet.", 409)
    settings = get_settings()
    k = body.top_k or repo.get("top_k") or settings.default_top_k
    items = hybrid_search(
        repository_id,
        body.query,
        top_k=k,
        mode=body.mode,
        semantic_weight=repo.get("semantic_weight"),
        keyword_weight=repo.get("keyword_weight"),
    )
    results = []
    for item in items:
        ev = result_to_evidence(item)
        results.append(
            {
                **ev,
                "relevance": ev.get("score"),
            }
        )
    return {"query": body.query, "mode": body.mode, "results": results}


@router.get("/{repository_id}/files")
def list_files(repository_id: str):
    _ensure_repo(repository_id)
    root = checkout_path(repository_id)
    if not root.exists():
        raise AppError("not_indexed", "Repository files are not available yet.", 409)
    return {"tree": _build_tree(root)}


@router.get("/{repository_id}/files/{file_path:path}")
def get_file(repository_id: str, file_path: str):
    _ensure_repo(repository_id)
    root = checkout_path(repository_id).resolve()
    target = (root / file_path).resolve()
    if root not in target.parents and target != root:
        raise AppError("invalid_path", "Invalid file path.", 400)
    if not target.is_file():
        raise AppError("not_found", "File not found.", 404)
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise AppError("io_error", f"Could not read file: {exc}", 500) from exc
    return {
        "path": PurePosixPath(file_path).as_posix(),
        "language": target.suffix.lstrip("."),
        "content": content,
        "size": target.stat().st_size,
        "line_count": content.count("\n") + (0 if content.endswith("\n") or not content else 1),
    }


@router.get("/{repository_id}/architecture")
def architecture(repository_id: str):
    _ensure_repo(repository_id)
    path = artifacts_path(repository_id) / "architecture.json"
    if not path.exists():
        raise AppError("not_indexed", "Architecture has not been generated yet.", 409)
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/{repository_id}/insights")
def insights(repository_id: str):
    _ensure_repo(repository_id)
    path = artifacts_path(repository_id) / "insights.json"
    if not path.exists():
        raise AppError("not_indexed", "Insights have not been generated yet.", 409)
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/{repository_id}/index-details")
def index_details(repository_id: str):
    repo = _ensure_repo(repository_id)
    job = repo_store.get_job(repository_id)
    settings = get_settings()
    skipped = []
    skipped_path = artifacts_path(repository_id) / "skipped.json"
    if skipped_path.exists():
        import json

        skipped = json.loads(skipped_path.read_text(encoding="utf-8"))
    stats = repo.get("stats") or {}
    return {
        "commit": repo.get("commit_sha"),
        "files": stats.get("files"),
        "functions": stats.get("functions"),
        "classes": stats.get("classes"),
        "methods": stats.get("methods"),
        "chunks": stats.get("chunks"),
        "embeddings": stats.get("embeddings") or vectorstore.count_repository_chunks(repository_id),
        "dependencies": stats.get("dependencies"),
        "languages": repo.get("languages") or {},
        "skipped_files": skipped,
        "warnings": repo.get("warnings") or [],
        "duration": repo.get("duration_ms"),
        "retrieval_settings": {
            "top_k": repo.get("top_k"),
            "semantic_weight": repo.get("semantic_weight") if repo.get("semantic_weight") is not None else settings.semantic_weight,
            "keyword_weight": repo.get("keyword_weight") if repo.get("keyword_weight") is not None else settings.keyword_weight,
            "embedding_model": settings.embedding_model,
            "supported_top_k": [3, 5, 8, 12],
        },
        "job": job,
        "status": repo.get("status"),
        "health": repo.get("health"),
        "last_indexed": repo.get("last_indexed"),
        "branch": repo.get("branch"),
        "repository": repo.get("full_name"),
    }
