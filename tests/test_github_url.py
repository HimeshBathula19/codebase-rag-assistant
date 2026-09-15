import pytest

from app.errors import AppError
from app.services.github import parse_github_url


def test_https_url():
    ref = parse_github_url("https://github.com/encode/starlette")
    assert ref.owner == "encode"
    assert ref.repo == "starlette"
    assert ref.full_name == "encode/starlette"


def test_git_suffix_and_ssh():
    ref = parse_github_url("https://github.com/encode/starlette.git")
    assert ref.repo == "starlette"
    ssh = parse_github_url("git@github.com:encode/starlette.git")
    assert ssh.full_name == "encode/starlette"


def test_invalid_url():
    with pytest.raises(AppError) as exc:
        parse_github_url("https://gitlab.com/foo/bar")
    assert exc.value.code == "invalid_github_url"


def test_empty_url():
    with pytest.raises(AppError) as exc:
        parse_github_url("  ")
    assert exc.value.code == "invalid_github_url"
