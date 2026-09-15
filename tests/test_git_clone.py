import subprocess

from app.errors import AppError
from app.services.git_clone import classify_git_error, clone_github_repository, public_clone_url
from app.services.github import GitHubRef, parse_github_url


def test_public_clone_url_has_no_credentials():
    ref = parse_github_url("https://github.com/HimeshBathula19/portfolio")
    url = public_clone_url(ref)
    assert url == "https://github.com/HimeshBathula19/portfolio.git"
    assert "@" not in url
    assert "token" not in url.lower()


def test_classify_private_without_token():
    err = classify_git_error("remote: Repository not found.", False, None)
    assert err.code == "private_repository"


def test_classify_invalid_token():
    err = classify_git_error("Authentication failed", True, None)
    assert err.code == "invalid_token"


def test_classify_branch_missing():
    err = classify_git_error("fatal: Remote branch missing-branch not found", False, "missing-branch")
    assert err.code == "branch_not_found"


def test_public_repository_clone_via_git(tmp_path):
    src = tmp_path / "origin"
    src.mkdir()
    (src / "app.py").write_text("def greet():\n    return 'ok'\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=src, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=src, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=src, check=True, capture_output=True)
    branch = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=src,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    dest = tmp_path / "checkout"
    ref = GitHubRef(owner="acme", repo="demo", full_name="acme/demo", html_url="https://github.com/acme/demo")
    result = clone_github_repository(ref, dest, branch, None)
    assert result.commit_sha
    assert len(result.commit_sha) >= 7
    assert (dest / "app.py").read_text(encoding="utf-8").find("greet") >= 0
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=dest,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert "github.com/acme/demo.git" in remote
    assert "@" not in remote
