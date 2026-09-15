from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.errors import AppError

_GITHUB_HTTPS = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?(?:/.*)?$",
    re.IGNORECASE,
)
_GITHUB_SSH = re.compile(
    r"^git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GitHubRef:
    owner: str
    repo: str
    full_name: str
    html_url: str


def parse_github_url(url: str) -> GitHubRef:
    if not url or not url.strip():
        raise AppError("invalid_github_url", "A GitHub repository URL is required.", 400)
    raw = url.strip()
    match = _GITHUB_HTTPS.match(raw) or _GITHUB_SSH.match(raw)
    if not match:
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc and "github.com" not in parsed.netloc.lower():
            raise AppError("invalid_github_url", "Only github.com repository URLs are supported.", 400)
        raise AppError(
            "invalid_github_url",
            "Invalid GitHub URL. Expected https://github.com/owner/repo",
            400,
        )
    owner = match.group("owner")
    repo = match.group("repo")
    if owner.lower() in {"orgs", "users", "settings", "topics"}:
        raise AppError("invalid_github_url", "Invalid GitHub URL. Expected https://github.com/owner/repo", 400)
    return GitHubRef(
        owner=owner,
        repo=repo,
        full_name=f"{owner}/{repo}",
        html_url=f"https://github.com/{owner}/{repo}",
    )
