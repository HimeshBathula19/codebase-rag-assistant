from pathlib import Path

from app.services.filtering import should_skip_file, path_has_skipped_dir, language_for_path


def test_skips_ignored_directories():
    skip, reason = should_skip_file("src/node_modules/pkg/index.js", 100)
    assert skip is True
    assert reason == "ignored_directory"
    assert path_has_skipped_dir(Path(".venv/lib/foo.py"))


def test_skips_binaries_and_media():
    skip, reason = should_skip_file("assets/logo.png", 1200)
    assert skip is True
    assert reason == "binary_or_media"
    skip, reason = should_skip_file("vendor.zip", 10)
    assert skip is True


def test_keeps_source_files():
    skip, reason = should_skip_file("app/main.py", 200)
    assert skip is False
    assert reason is None
    assert language_for_path("app/main.py") == "python"
    assert language_for_path("src/App.tsx") == "tsx"


def test_skips_generated_and_large():
    skip, _ = should_skip_file("package-lock.json", 20)
    assert skip is True
    skip, reason = should_skip_file("big.py", 5_000_000)
    assert skip is True
    assert reason == "file_too_large"
