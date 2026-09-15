from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import PurePosixPath

from app.services.parsing import ParsedFile, Symbol


REQUIRED_METADATA = (
    "repository_id",
    "repository_name",
    "file_path",
    "language",
    "symbol",
    "symbol_type",
    "class_name",
    "start_line",
    "end_line",
    "signature",
    "commit_sha",
)


@dataclass
class SemanticChunk:
    id: str
    text: str
    repository_id: str
    repository_name: str
    file_path: str
    language: str | None
    symbol: str | None
    symbol_type: str | None
    class_name: str | None
    start_line: int
    end_line: int
    signature: str | None
    commit_sha: str | None

    def metadata(self) -> dict:
        meta = asdict(self)
        meta.pop("id")
        meta.pop("text")
        # Chroma metadata values must be scalars
        for key in list(meta.keys()):
            if meta[key] is None:
                meta[key] = ""
        return meta


def _chunk_id(repository_id: str, file_path: str, start_line: int, end_line: int, symbol: str | None) -> str:
    safe = str(PurePosixPath(file_path)).replace("\\", "/")
    return f"{repository_id}:{safe}:{start_line}:{end_line}:{symbol or 'file'}"


def _split_large_symbol(
    source_lines: list[str],
    symbol: Symbol,
    max_lines: int,
    overlap: int,
) -> list[tuple[int, int]]:
    length = symbol.end_line - symbol.start_line + 1
    if length <= max_lines:
        return [(symbol.start_line, symbol.end_line)]
    ranges: list[tuple[int, int]] = []
    start = symbol.start_line
    while start <= symbol.end_line:
        end = min(symbol.end_line, start + max_lines - 1)
        ranges.append((start, end))
        if end >= symbol.end_line:
            break
        start = end - overlap + 1
    return ranges


def chunk_parsed_file(
    parsed: ParsedFile,
    source: str,
    repository_id: str,
    repository_name: str,
    commit_sha: str | None,
    max_lines: int = 80,
    overlap: int = 8,
) -> list[SemanticChunk]:
    lines = source.splitlines()
    chunks: list[SemanticChunk] = []
    if not lines:
        return chunks

    def make_chunk(
        start: int,
        end: int,
        symbol: str | None,
        symbol_type: str | None,
        class_name: str | None,
        signature: str | None,
    ) -> SemanticChunk:
        text = "\n".join(lines[start - 1 : end])
        return SemanticChunk(
            id=_chunk_id(repository_id, parsed.file_path, start, end, symbol),
            text=text,
            repository_id=repository_id,
            repository_name=repository_name,
            file_path=parsed.file_path.replace("\\", "/"),
            language=parsed.language,
            symbol=symbol,
            symbol_type=symbol_type,
            class_name=class_name,
            start_line=start,
            end_line=end,
            signature=signature,
            commit_sha=commit_sha,
        )

    covered: set[int] = set()
    for symbol in parsed.symbols:
        for start, end in _split_large_symbol(lines, symbol, max_lines, overlap):
            chunks.append(
                make_chunk(
                    start,
                    end,
                    symbol.name,
                    symbol.symbol_type,
                    symbol.class_name,
                    symbol.signature,
                )
            )
            covered.update(range(start, end + 1))

    leftover = [i + 1 for i in range(len(lines)) if (i + 1) not in covered and lines[i].strip()]
    if leftover and not parsed.symbols:
        start = 1
        while start <= len(lines):
            end = min(len(lines), start + max_lines - 1)
            chunks.append(make_chunk(start, end, None, "file", None, None))
            if end >= len(lines):
                break
            start = end - overlap + 1
    elif leftover and parsed.language not in {None}:
        # keep uncovered non-empty regions as file-level context chunks
        start = leftover[0]
        prev = start
        regions: list[tuple[int, int]] = []
        for line_no in leftover[1:]:
            if line_no == prev + 1:
                prev = line_no
                continue
            regions.append((start, prev))
            start = line_no
            prev = line_no
        regions.append((start, prev))
        for start, end in regions:
            if end - start + 1 < 4:
                continue
            chunk_start = start
            while chunk_start <= end:
                chunk_end = min(end, chunk_start + max_lines - 1)
                chunks.append(make_chunk(chunk_start, chunk_end, None, "file", None, None))
                if chunk_end >= end:
                    break
                chunk_start = chunk_end - overlap + 1

    return chunks
