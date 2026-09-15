from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.services.architecture import parse_manifest_dependencies
from app.services.parsing import parse_source


ENTRY_FILES = {
    "main.py",
    "app.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "index.js",
    "index.ts",
    "index.tsx",
    "main.ts",
    "main.tsx",
    "main.go",
    "main.rs",
    "Main.java",
    "Program.cs",
}

AUTH_HINTS = re.compile(r"auth|oauth|jwt|session|passport|login", re.I)
DB_HINTS = re.compile(r"database|sqlalchemy|prisma|mongoose|sequelize|sqlite|postgres|mysql|redis|orm", re.I)
API_HINTS = re.compile(r"route|router|controller|endpoint|fastapi|express|handler", re.I)
SERVICE_HINTS = re.compile(r"service|worker|job|queue|consumer", re.I)
CONFIG_HINTS = re.compile(r"config|settings|\.env|application\.yml|pyproject|tsconfig", re.I)
TEST_HINTS = re.compile(r"(^|/)(tests?|spec|__tests__)(/|$)|(_test|\.test|\.spec)\.", re.I)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def build_insights(repo_root: Path, relative_files: list[str], parsed_symbols: list[dict[str, Any]]) -> dict[str, Any]:
    files = [f.replace("\\", "/") for f in relative_files]
    entry_points: list[dict[str, Any]] = []
    authentication: list[str] = []
    database: list[str] = []
    api_routes: list[str] = []
    services: list[str] = []
    configuration: list[str] = []
    tests: list[str] = []
    modules: dict[str, int] = {}

    for rel in files:
        path = repo_root / rel
        name = Path(rel).name
        top = rel.split("/", 1)[0]
        modules[top] = modules.get(top, 0) + 1
        if name in ENTRY_FILES or rel in ENTRY_FILES:
            entry_points.append({"file": rel, "reason": "conventional entry file"})
        if AUTH_HINTS.search(rel):
            authentication.append(rel)
        if DB_HINTS.search(rel):
            database.append(rel)
        if API_HINTS.search(rel):
            api_routes.append(rel)
        if SERVICE_HINTS.search(rel):
            services.append(rel)
        if CONFIG_HINTS.search(rel) or name.endswith((".ini", ".toml", ".yml", ".yaml", ".env.example")):
            configuration.append(rel)
        if TEST_HINTS.search(rel):
            tests.append(rel)
        if path.is_file() and path.suffix in {".py", ".js", ".ts", ".go"}:
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", source) or re.search(
                r"func\s+main\s*\(", source
            ):
                if not any(e["file"] == rel for e in entry_points):
                    entry_points.append({"file": rel, "reason": "detected main/runtime entry"})
            parsed = parse_source(rel, source)
            for symbol in parsed.symbols:
                if symbol.name in {"main", "createApp", "create_app"}:
                    if not any(e["file"] == rel for e in entry_points):
                        entry_points.append(
                            {"file": rel, "reason": f"symbol {symbol.name}", "symbol": symbol.name}
                        )

    major_modules = [
        {"name": name, "files": count}
        for name, count in sorted(modules.items(), key=lambda kv: kv[1], reverse=True)
        if count >= 1
    ]

    return {
        "entry_points": entry_points,
        "major_modules": major_modules[:30],
        "authentication": sorted(set(authentication)),
        "database": sorted(set(database)),
        "api_routes": sorted(set(api_routes)),
        "services": sorted(set(services)),
        "configuration": sorted(set(configuration)),
        "tests": sorted(set(tests)),
        "dependencies": parse_manifest_dependencies(repo_root),
        "symbols_sampled": len(parsed_symbols),
    }
