from app.services.chunking import REQUIRED_METADATA, chunk_parsed_file
from app.services.parsing import parse_source

JS_SRC = """
import { Router } from 'express'

export function createRouter() {
  const router = Router()
  return router
}
"""


def test_metadata_never_omits_required_keys():
    parsed = parse_source("src/router.ts", JS_SRC, "typescript")
    chunks = chunk_parsed_file(parsed, JS_SRC, "rid", "owner/name", "sha")
    assert chunks
    for chunk in chunks:
        meta = chunk.metadata()
        assert set(REQUIRED_METADATA) <= set(meta)
        assert meta["repository_id"] == "rid"
        assert meta["repository_name"] == "owner/name"
        assert isinstance(meta["start_line"], int)
        assert isinstance(meta["end_line"], int)
