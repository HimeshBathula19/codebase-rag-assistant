from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from app.services.parsing import parse_source


EXTERNAL_HINTS = {
    "react",
    "fastapi",
    "flask",
    "django",
    "numpy",
    "pandas",
    "express",
    "vue",
    "angular",
    "torch",
    "tensorflow",
}


def _normalize_module(value: str) -> str:
    return value.replace("\\", "/").strip().strip("'\"")


def resolve_internal_import(current_file: str, imported: str, files: set[str]) -> str | None:
    imported = _normalize_module(imported)
    if not imported:
        return None
    current_dir = str(PurePosixPath(current_file).parent)
    candidates: list[str] = []
    if imported.startswith("."):
        base = PurePosixPath(current_dir)
        rel = imported
        while rel.startswith("../"):
            base = base.parent
            rel = rel[3:]
        if rel.startswith("./"):
            rel = rel[2:]
        rel = rel.lstrip("./")
        stem = str((base / rel).as_posix()).replace("/./", "/")
        candidates.extend(
            [
                f"{stem}.py",
                f"{stem}.ts",
                f"{stem}.tsx",
                f"{stem}.js",
                f"{stem}.jsx",
                f"{stem}/index.ts",
                f"{stem}/index.js",
                f"{stem}/__init__.py",
                stem,
            ]
        )
    else:
        dotted = imported.replace(".", "/")
        candidates.extend(
            [
                f"{dotted}.py",
                f"{dotted}.ts",
                f"{dotted}.js",
                f"{dotted}/__init__.py",
                f"{imported}.go",
                imported,
            ]
        )
        # match any file ending with the module path
        suffix = f"/{dotted}.py"
        for path in files:
            if path.endswith(suffix) or path.endswith(f"/{dotted}.ts") or path == f"{dotted}.py":
                candidates.append(path)
    for candidate in candidates:
        normalized = candidate.lstrip("./")
        if normalized in files:
            return normalized
    return None


def build_architecture(repo_root: Path, relative_files: list[str]) -> dict[str, Any]:
    files = {path.replace("\\", "/") for path in relative_files}
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str]] = set()

    def add_node(node_id: str, label: str, kind: str, language: str | None = None) -> None:
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "kind": kind, "language": language}

    for rel in sorted(files):
        path = repo_root / rel
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = parse_source(rel, source)
        add_node(rel, rel, "file", parsed.language)
        for imported in parsed.imports:
            internal = resolve_internal_import(rel, imported, files)
            if internal:
                add_node(internal, internal, "file")
                key = (rel, internal)
                if key not in edge_keys and rel != internal:
                    edge_keys.add(key)
                    edges.append({"source": rel, "target": internal, "kind": "internal_import"})
            else:
                # only add an external node when the import string is a real parsed import
                name = imported.split("/")[0].split(".")[0]
                if not name or name in {".", ".."}:
                    continue
                node_id = f"ext:{name}"
                add_node(node_id, name, "external")
                key = (rel, node_id)
                if key not in edge_keys:
                    edge_keys.add(key)
                    edges.append({"source": rel, "target": node_id, "kind": "external_import"})

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "internal_nodes": sum(1 for n in nodes.values() if n["kind"] == "file"),
        "external_nodes": sum(1 for n in nodes.values() if n["kind"] == "external"),
    }


def parse_manifest_dependencies(repo_root: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    req = repo_root / "requirements.txt"
    if req.exists():
        pkgs = []
        for line in req.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pkgs.append(re.split(r"[<>=\[]", line, 1)[0].strip())
        if pkgs:
            found["python"] = pkgs
    pkg = repo_root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="replace"))
            deps = sorted(set(list((data.get("dependencies") or {}).keys()) + list((data.get("devDependencies") or {}).keys())))
            if deps:
                found["javascript"] = deps
        except json.JSONDecodeError:
            pass
    gomod = repo_root / "go.mod"
    if gomod.exists():
        mods = []
        for line in gomod.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Za-z0-9./_-]+)\s+v\d", line)
            if m:
                mods.append(m.group(1))
        if mods:
            found["go"] = mods
    cargo = repo_root / "Cargo.toml"
    if cargo.exists():
        deps = []
        in_deps = False
        for line in cargo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip() == "[dependencies]":
                in_deps = True
                continue
            if line.startswith("["):
                in_deps = False
            if in_deps and "=" in line:
                deps.append(line.split("=", 1)[0].strip())
        if deps:
            found["rust"] = deps
    pom = repo_root / "pom.xml"
    if pom.exists():
        arts = re.findall(r"<artifactId>([^<]+)</artifactId>", pom.read_text(encoding="utf-8", errors="replace"))
        if arts:
            found["java"] = arts
    return found
