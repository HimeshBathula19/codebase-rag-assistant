from __future__ import annotations

from pathlib import Path

SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    "target",
    "vendor",
    ".next",
    ".cache",
    ".turbo",
    ".idea",
    ".vscode",
    "eggs",
    ".eggs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "htmlcov",
}

SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".bmp",
    ".svg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".mp3",
    ".wav",
    ".flac",
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".7z",
    ".rar",
    ".pdf",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".class",
    ".jar",
    ".war",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".pyc",
    ".pyo",
    ".o",
    ".obj",
    ".a",
    ".lib",
    ".pdb",
    ".wasm",
    ".lock",
    ".min.js",
    ".min.css",
    ".map",
}

GENERATED_NAME_FRAGMENTS = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "poetry.lock",
    "cargo.lock",
    "go.sum",
}

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".md": "markdown",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".sh": "shell",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
}


def path_has_skipped_dir(path: Path | str) -> bool:
    parts = Path(path).parts
    return any(part in SKIP_DIR_NAMES for part in parts)


def language_for_path(path: Path | str) -> str | None:
    suffix = Path(path).suffix.lower()
    name = Path(path).name.lower()
    if name.endswith(".min.js") or name.endswith(".min.css"):
        return None
    return LANGUAGE_BY_EXTENSION.get(suffix)


def should_skip_file(path: Path | str, size: int | None = None, max_bytes: int = 1_000_000) -> tuple[bool, str | None]:
    p = Path(path)
    if path_has_skipped_dir(p):
        return True, "ignored_directory"
    name = p.name.lower()
    if name in GENERATED_NAME_FRAGMENTS:
        return True, "generated_lockfile"
    if name.endswith(".min.js") or name.endswith(".min.css") or name.endswith(".map"):
        return True, "generated_asset"
    suffix = p.suffix.lower()
    if suffix in SKIP_EXTENSIONS:
        return True, "binary_or_media"
    if size is not None and size > max_bytes:
        return True, "file_too_large"
    if size == 0:
        return True, "empty_file"
    return False, None


def iter_source_files(root: Path, max_bytes: int = 1_000_000) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        skip, _reason = should_skip_file(path.relative_to(root), path.stat().st_size, max_bytes)
        if skip:
            continue
        files.append(path)
    return sorted(files)
