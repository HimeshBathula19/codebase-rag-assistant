from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.errors import AppError
from app.services.github import GitHubRef


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "codebase-rag-assistant",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise_github(response: httpx.Response, token_present: bool) -> None:
    if response.status_code == 404:
        raise AppError("repository_not_found", "GitHub repository was not found.", 404)
    if response.status_code in {401}:
        raise AppError("invalid_token", "The GitHub token is invalid.", 401)
    if response.status_code == 403:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0" or "rate limit" in response.text.lower():
            raise AppError("rate_limit", "GitHub API rate limit exceeded.", 429)
        if not token_present:
            raise AppError(
                "private_repository",
                "This repository is private or not accessible without a GitHub token.",
                403,
            )
        raise AppError("invalid_token", "GitHub rejected the provided token for this repository.", 403)
    if response.status_code >= 400:
        raise AppError(
            "github_error",
            f"GitHub request failed with status {response.status_code}.",
            502,
            {"status": response.status_code},
        )


def fetch_repository_metadata(ref: GitHubRef, token: str | None, branch: str | None) -> dict[str, Any]:
    settings = get_settings()
    auth_token = token or settings.github_token or None
    url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}"
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, headers=_headers(auth_token))
            _raise_github(response, bool(auth_token))
            data = response.json()
            default_branch = data.get("default_branch") or "main"
            chosen_branch = branch or default_branch
            branch_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/branches/{chosen_branch}"
            branch_resp = client.get(branch_url, headers=_headers(auth_token))
            if branch_resp.status_code == 404:
                raise AppError("repository_not_found", f"Branch '{chosen_branch}' was not found.", 404)
            _raise_github(branch_resp, bool(auth_token))
            branch_data = branch_resp.json()
            commit_sha = ((branch_data.get("commit") or {}).get("sha")) or ""
            return {
                "name": data.get("name") or ref.repo,
                "owner": (data.get("owner") or {}).get("login") or ref.owner,
                "full_name": data.get("full_name") or ref.full_name,
                "url": data.get("html_url") or ref.html_url,
                "default_branch": default_branch,
                "branch": chosen_branch,
                "commit_sha": commit_sha,
                "private": bool(data.get("private")),
                "description": data.get("description"),
            }
    except AppError:
        raise
    except httpx.HTTPError as exc:
        raise AppError("network_failure", f"Network failure while contacting GitHub: {exc}", 503) from exc


def download_and_extract(ref: GitHubRef, branch: str, dest: Path, token: str | None) -> str:
    settings = get_settings()
    auth_token = token or settings.github_token or None
    dest.mkdir(parents=True, exist_ok=True)
    url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/zipball/{branch}"
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(url, headers=_headers(auth_token))
            _raise_github(response, bool(auth_token))
            if not response.content:
                raise AppError("empty_repository", "The downloaded repository archive was empty.", 400)
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                names = zf.namelist()
                if not names:
                    raise AppError("empty_repository", "The repository archive contained no files.", 400)
                # GitHub zipballs have a single top-level folder
                zf.extractall(dest)
                top = Path(names[0].split("/")[0])
                extracted = dest / top
                return str(extracted)
    except AppError:
        raise
    except zipfile.BadZipFile as exc:
        raise AppError("network_failure", "GitHub returned an invalid archive.", 502) from exc
    except httpx.HTTPError as exc:
        raise AppError("network_failure", f"Network failure while downloading repository: {exc}", 503) from exc


def flatten_github_extract(extracted_root: Path, dest: Path) -> Path:
    """Move extracted GitHub zip contents into dest (clean checkout path)."""
    dest.mkdir(parents=True, exist_ok=True)
    if extracted_root.resolve() == dest.resolve():
        return dest
    # If dest already has files from a previous clone, caller should clear it.
    for item in extracted_root.iterdir():
        target = dest / item.name
        item.rename(target)
    try:
        extracted_root.rmdir()
    except OSError:
        pass
    return dest
