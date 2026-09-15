from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.filtering import language_for_path


@dataclass
class Symbol:
    name: str
    symbol_type: str
    start_line: int
    end_line: int
    signature: str
    class_name: str | None = None


@dataclass
class ParsedFile:
    file_path: str
    language: str | None
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    warning: str | None = None


def _line_starts(source: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def offset_to_line(starts: list[int], offset: int) -> int:
    lo, hi = 0, len(starts) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi + 1


def _block_end(lines: list[str], start_idx: int, language: str) -> int:
    if language in {"python"}:
        base_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip(" "))
        last = start_idx
        for i in range(start_idx + 1, len(lines)):
            stripped = lines[i].strip()
            if not stripped or stripped.startswith("#"):
                last = i
                continue
            indent = len(lines[i]) - len(lines[i].lstrip(" "))
            if indent <= base_indent and not stripped.startswith((")", "]", "}")):
                return last + 1
            last = i
        return len(lines)
    # brace languages
    depth = 0
    seen = False
    for i in range(start_idx, len(lines)):
        depth += lines[i].count("{") - lines[i].count("}")
        if "{" in lines[i]:
            seen = True
        if seen and depth <= 0:
            return i + 1
    return min(len(lines), start_idx + 80)


def _parse_python(source: str) -> tuple[list[Symbol], list[str]]:
    lines = source.splitlines()
    symbols: list[Symbol] = []
    imports: list[str] = []
    class_stack: list[tuple[str, int]] = []
    class_re = re.compile(r"^(?P<indent>\s*)class\s+(?P<name>\w+)")
    func_re = re.compile(r"^(?P<indent>\s*)(?:async\s+)?def\s+(?P<name>\w+)\s*\((?P<rest>[^\)]*)\)")
    import_re = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))")

    for idx, line in enumerate(lines):
        imp = import_re.match(line)
        if imp:
            imports.append((imp.group(1) or imp.group(2) or "").split(" as ")[0])
        cm = class_re.match(line)
        if cm:
            indent = len(cm.group("indent"))
            while class_stack and class_stack[-1][1] >= indent:
                class_stack.pop()
            name = cm.group("name")
            end = _block_end(lines, idx, "python")
            symbols.append(
                Symbol(
                    name=name,
                    symbol_type="class",
                    start_line=idx + 1,
                    end_line=end,
                    signature=line.strip(),
                )
            )
            class_stack.append((name, indent))
            continue
        fm = func_re.match(line)
        if fm:
            indent = len(fm.group("indent"))
            while class_stack and class_stack[-1][1] >= indent:
                class_stack.pop()
            name = fm.group("name")
            end = _block_end(lines, idx, "python")
            parent = class_stack[-1][0] if class_stack else None
            symbols.append(
                Symbol(
                    name=name,
                    symbol_type="method" if parent else "function",
                    start_line=idx + 1,
                    end_line=end,
                    signature=line.strip().rstrip(":"),
                    class_name=parent,
                )
            )
    return symbols, imports


def _parse_js_family(source: str) -> tuple[list[Symbol], list[str]]:
    lines = source.splitlines()
    symbols: list[Symbol] = []
    imports: list[str] = []
    import_re = re.compile(
        r"""(?:import\s+(?:.+?\s+from\s+)?['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|export\s+\*\s+from\s+['"]([^'"]+)['"])"""
    )
    class_re = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)")
    func_re = re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\("
    )
    method_re = re.compile(r"^\s+(?:async\s+)?(\w+)\s*\([^;]*\)\s*\{")
    arrow_re = re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w]+)\s*=>"
    )
    current_class: str | None = None
    class_end = 0
    for idx, line in enumerate(lines):
        for m in import_re.finditer(line):
            imports.append(next(g for g in m.groups() if g))
        cm = class_re.match(line)
        if cm:
            end = _block_end(lines, idx, "js")
            current_class = cm.group(1)
            class_end = end
            symbols.append(
                Symbol(cm.group(1), "class", idx + 1, end, line.strip())
            )
            continue
        if current_class and idx + 1 > class_end:
            current_class = None
        fm = func_re.match(line) or arrow_re.match(line)
        if fm:
            end = _block_end(lines, idx, "js")
            symbols.append(
                Symbol(fm.group(1), "function", idx + 1, end, line.strip())
            )
            continue
        mm = method_re.match(line)
        if mm and current_class and mm.group(1) not in {"if", "for", "while", "switch", "catch"}:
            end = _block_end(lines, idx, "js")
            symbols.append(
                Symbol(mm.group(1), "method", idx + 1, end, line.strip(), current_class)
            )
    return symbols, imports


def _parse_java(source: str) -> tuple[list[Symbol], list[str]]:
    lines = source.splitlines()
    symbols: list[Symbol] = []
    imports = [
        m.group(1)
        for line in lines
        if (m := re.match(r"^\s*import\s+([\w.]+)", line))
    ]
    class_re = re.compile(r"^\s*(?:public|protected|private)?\s*(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)")
    method_re = re.compile(
        r"^\s*(?:public|protected|private|static|final|synchronized|\s)+[\w<>\[\]]+\s+(\w+)\s*\("
    )
    current_class = None
    class_end = 0
    for idx, line in enumerate(lines):
        cm = class_re.search(line)
        if cm:
            end = _block_end(lines, idx, "java")
            current_class = cm.group(1)
            class_end = end
            symbols.append(Symbol(cm.group(1), "class", idx + 1, end, line.strip()))
            continue
        if current_class and idx + 1 > class_end:
            current_class = None
        mm = method_re.match(line)
        if mm and mm.group(1) not in {"if", "for", "while", "switch", "catch"}:
            end = _block_end(lines, idx, "java")
            symbols.append(
                Symbol(
                    mm.group(1),
                    "method" if current_class else "function",
                    idx + 1,
                    end,
                    line.strip(),
                    current_class,
                )
            )
    return symbols, imports


def _parse_go(source: str) -> tuple[list[Symbol], list[str]]:
    lines = source.splitlines()
    symbols: list[Symbol] = []
    imports: list[str] = []
    in_import = False
    for line in lines:
        if line.strip().startswith("import ("):
            in_import = True
            continue
        if in_import:
            if ")" in line:
                in_import = False
            m = re.search(r'"([^"]+)"', line)
            if m:
                imports.append(m.group(1))
            continue
        m = re.match(r'^\s*import\s+"([^"]+)"', line)
        if m:
            imports.append(m.group(1))
    func_re = re.compile(r"^func\s+(?:\((?P<recv>[^)]+)\)\s+)?(?P<name>\w+)\s*\(")
    type_re = re.compile(r"^type\s+(\w+)\s+(?:struct|interface)")
    for idx, line in enumerate(lines):
        tm = type_re.match(line)
        if tm:
            end = _block_end(lines, idx, "go")
            symbols.append(Symbol(tm.group(1), "class", idx + 1, end, line.strip()))
            continue
        fm = func_re.match(line)
        if fm:
            end = _block_end(lines, idx, "go")
            recv = fm.group("recv")
            class_name = None
            if recv:
                class_name = recv.split()[-1].lstrip("*")
            symbols.append(
                Symbol(
                    fm.group("name"),
                    "method" if class_name else "function",
                    idx + 1,
                    end,
                    line.strip(),
                    class_name,
                )
            )
    return symbols, imports


def _parse_rust(source: str) -> tuple[list[Symbol], list[str]]:
    lines = source.splitlines()
    imports = [
        m.group(1)
        for line in lines
        if (m := re.match(r"^\s*use\s+([\w:]+)", line))
    ]
    symbols: list[Symbol] = []
    item_re = re.compile(r"^\s*(?:pub(?:\([^)]+\))?\s+)?(fn|struct|enum|impl|mod)\s+(\w+)?")
    for idx, line in enumerate(lines):
        m = item_re.match(line)
        if not m:
            continue
        kind, name = m.group(1), m.group(2) or "impl"
        end = _block_end(lines, idx, "rust")
        stype = {"fn": "function", "struct": "class", "enum": "class", "impl": "class", "mod": "module"}[kind]
        if kind == "fn" and "impl" in "\n".join(lines[max(0, idx - 20) : idx]):
            stype = "method"
        symbols.append(Symbol(name, stype, idx + 1, end, line.strip()))
    return symbols, imports


def _parse_c_family(source: str) -> tuple[list[Symbol], list[str]]:
    lines = source.splitlines()
    imports = [
        m.group(1)
        for line in lines
        if (m := re.match(r'^\s*#include\s+[<"]([^>"]+)[>"]', line))
    ]
    symbols: list[Symbol] = []
    func_re = re.compile(r"^[A-Za-z_][\w\s\*]+\s+([A-Za-z_]\w+)\s*\([^;]*\)\s*\{?\s*$")
    struct_re = re.compile(r"^\s*(?:typedef\s+)?struct\s+(\w+)")
    for idx, line in enumerate(lines):
        sm = struct_re.match(line)
        if sm:
            end = _block_end(lines, idx, "c")
            symbols.append(Symbol(sm.group(1), "class", idx + 1, end, line.strip()))
            continue
        fm = func_re.match(line.strip())
        if fm and fm.group(1) not in {"if", "for", "while", "switch"}:
            end = _block_end(lines, idx, "c")
            symbols.append(Symbol(fm.group(1), "function", idx + 1, end, line.strip()))
    return symbols, imports


def parse_source(file_path: str, source: str, language: str | None = None) -> ParsedFile:
    language = language or language_for_path(file_path)
    parsers = {
        "python": _parse_python,
        "javascript": _parse_js_family,
        "typescript": _parse_js_family,
        "tsx": _parse_js_family,
        "java": _parse_java,
        "go": _parse_go,
        "rust": _parse_rust,
        "c": _parse_c_family,
        "cpp": _parse_c_family,
    }
    if not language:
        return ParsedFile(file_path=file_path, language=None, warning="unsupported_language")
    parser = parsers.get(language)
    if not parser:
        return ParsedFile(file_path=file_path, language=language, warning="unsupported_language")
    try:
        symbols, imports = parser(source)
        return ParsedFile(file_path=file_path, language=language, symbols=symbols, imports=imports)
    except Exception as exc:  # pragma: no cover - defensive
        return ParsedFile(
            file_path=file_path,
            language=language,
            warning=f"parser_failure:{type(exc).__name__}",
        )
