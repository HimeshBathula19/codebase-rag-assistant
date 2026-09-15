from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.errors import AppError
from app.services.github import GitHubRef, parse_github_url


@dataclass(frozen=True)
class GitCheckout:
    owner: str
    repo: str
    full_name: str
    url: str
    branch: str
    default_branch: str
    commit_sha: str


def _git_executable() -> str:
    path = shutil.which("git")
    if not path:
        raise AppError("git_not_installed", "Git is not installed or is not on PATH.", 500)
    return path


def _redact(text: str, token: str | None) -> str:
    if not text:
        return ""
    cleaned = text
    if token:
        cleaned = cleaned.replace(token, "***")
        cleaned = cleaned.replace(token.replace("\\", "\\\\"), "***")
    cleaned = cleaned.replace("x-access-token:", "x-access-token:")
    return cleaned


def _run_git(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 180) -> str:
    git = _git_executable()
    merged_env = os.environ.copy()
    merged_env["GIT_TERMINAL_PROMPT"] = "0"
    merged_env["GCM_INTERACTIVE"] = "never"
    if env:
        merged_env.update(env)
    try:
        completed = subprocess.run(
            [git, *args],
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AppError("git_not_installed", "Git is not installed or is not on PATH.", 500) from exc
    except subprocess.TimeoutExpired as exc:
        raise AppError("network_failure", "Git timed out while contacting the remote repository.", 503) from exc
    if completed.returncode == 0:
        return (completed.stdout or "").strip()
    raise AppError("git_error", "Git command failed.", 502, {"stderr": completed.stderr or ""})


def classify_git_error(stderr: str, token_present: bool, requested_branch: str | None) -> AppError:
    text = (stderr or "").lower()
    if "not found" in text and requested_branch and requested_branch.lower() in text:
        return AppError("branch_not_found", f"Branch '{requested_branch}' was not found.", 404)
    if "remote branch" in text and "not found" in text:
        return AppError("branch_not_found", f"Branch '{requested_branch}' was not found.", 404)
    if "couldn't find remote ref" in text or "did not match any file(s) known to git" in text:
        return AppError("branch_not_found", f"Branch '{requested_branch or 'specified'}' was not found.", 404)
    if "authentication failed" in text or "invalid username or password" in text or "bad credentials" in text:
        if token_present:
            return AppError("invalid_token", "The GitHub token is invalid.", 401)
        return AppError(
            "private_repository",
            "This repository is private or not accessible without a GitHub token.",
            403,
        )
    if "could not resolve host" in text or "unable to access" in text and "failed to connect" in text:
        return AppError("network_failure", "Network failure while cloning the repository.", 503)
    if "failed to connect" in text or "timed out" in text or "connection was reset" in text:
        return AppError("network_failure", "Network failure while cloning the repository.", 503)
    if "rate limit" in text or "429" in text:
        return AppError("rate_limit", "GitHub rate limit exceeded while cloning.", 429)
    if "repository not found" in text:
        if token_present:
            return AppError("repository_not_found", "GitHub repository was not found.", 404)
        return AppError(
            "private_repository",
            "Repository was not found. If it is private, provide a GitHub token.",
            404,
        )
    return AppError("repository_not_found", "GitHub repository was not found or could not be cloned.", 404)


def public_clone_url(ref: GitHubRef) -> str:
    return f"https://github.com/{ref.owner}/{ref.repo}.git"


def clone_github_repository(ref: GitHubRef, dest: Path, branch: str | None, token: str | None) -> GitCheckout:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)

    clone_url = public_clone_url(ref)
    extra_header: list[str] = []
    env: dict[str, str] = {}
    if token:
        extra_header = ["-c", f"http.extraHeader=Authorization: Bearer {token}"]

    args = [*extra_header, "clone", "--depth", "1"]
    if branch:
        args.extend(["--branch", branch, "--single-branch"])
    args.extend([clone_url, str(dest)])

    git = _git_executable()
    merged_env = os.environ.copy()
    merged_env["GIT_TERMINAL_PROMPT"] = "0"
    merged_env["GCM_INTERACTIVE"] = "never"
    merged_env.update(env)
    try:
        completed = subprocess.run(
            [git, *args],
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AppError("git_not_installed", "Git is not installed or is not on PATH.", 500) from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise AppError("network_failure", "Network failure while cloning the repository.", 503) from exc

    if completed.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        raise classify_git_error(completed.stderr or completed.stdout or "", bool(token), branch)

    try:
        _run_git(["remote", "set-url", "origin", public_clone_url(ref)], cwd=dest)
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=dest)
        current_branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=dest)
        default_branch = current_branch
        try:
            symbolic = _run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=dest)
            if symbolic.startswith("refs/remotes/origin/"):
                default_branch = symbolic.rsplit("/", 1)[-1]
        except AppError:
            default_branch = current_branch
    except AppError:
        shutil.rmtree(dest, ignore_errors=True)
        raise

    if not commit_sha:
        raise AppError("empty_repository", "The cloned repository has no commit SHA.", 400)

    return GitCheckout(
        owner=ref.owner,
        repo=ref.repo,
        full_name=ref.full_name,
        url=ref.html_url,
        branch=current_branch,
        default_branch=default_branch or current_branch,
        commit_sha=commit_sha,
    )


def inspect_without_clone(url: str, branch: str | None) -> tuple[GitHubRef, str | None]:
    ref = parse_github_url(url)
    return ref, branch
