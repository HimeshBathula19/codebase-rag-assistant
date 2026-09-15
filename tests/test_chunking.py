from app.services.chunking import REQUIRED_METADATA, chunk_parsed_file
from app.services.parsing import parse_source


PYTHON_SRC = '''\
import os

class Greeter:
    def hello(self, name: str) -> str:
        return f"hi {name}"

def run():
    return Greeter().hello("world")
'''


def test_python_symbols_and_chunks():
    parsed = parse_source("app/greeter.py", PYTHON_SRC)
    assert {s.name for s in parsed.symbols} >= {"Greeter", "hello", "run"}
    assert any(s.symbol_type == "class" for s in parsed.symbols)
    assert any(s.symbol_type == "method" and s.class_name == "Greeter" for s in parsed.symbols)
    chunks = chunk_parsed_file(parsed, PYTHON_SRC, "repo-1", "acme/demo", "abc123")
    assert chunks
    hello = next(c for c in chunks if c.symbol == "hello")
    assert hello.start_line >= 1
    assert hello.end_line >= hello.start_line
    assert "return f" in hello.text


def test_chunk_metadata_fields():
    parsed = parse_source("app/greeter.py", PYTHON_SRC)
    chunk = chunk_parsed_file(parsed, PYTHON_SRC, "repo-1", "acme/demo", "abc123")[0]
    meta = chunk.metadata()
    for key in REQUIRED_METADATA:
        assert key in meta
    assert meta["repository_id"] == "repo-1"
    assert meta["commit_sha"] == "abc123"
    assert meta["file_path"] == "app/greeter.py"
