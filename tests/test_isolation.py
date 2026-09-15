from app.services.chunking import chunk_parsed_file
from app.services.parsing import parse_source
from app.services.retrieval import hybrid_search
from app.services.vectorstore import upsert_chunks


def _index_file(repo_id: str, path: str, source: str, secret: str) -> None:
    parsed = parse_source(path, source, "python")
    chunks = chunk_parsed_file(parsed, source, repo_id, f"owner/{repo_id}", "sha")
    assert chunks
    upsert_chunks(chunks)


def test_repository_isolation(isolated_env):
    _index_file("repo-a", "a.py", "def alpha_unique_symbol():\n    return 'alpha'\n", "alpha")
    _index_file("repo-b", "b.py", "def beta_unique_symbol():\n    return 'beta'\n", "beta")

    a_hits = hybrid_search("repo-a", "alpha_unique_symbol", top_k=5, mode="hybrid")
    b_hits = hybrid_search("repo-b", "beta_unique_symbol", top_k=5, mode="hybrid")
    assert a_hits
    assert b_hits
    assert all((hit.get("metadata") or {}).get("repository_id") == "repo-a" for hit in a_hits)
    assert all((hit.get("metadata") or {}).get("repository_id") == "repo-b" for hit in b_hits)
    assert all("beta_unique_symbol" not in (hit.get("text") or "") for hit in a_hits)
    assert all("alpha_unique_symbol" not in (hit.get("text") or "") for hit in b_hits)


def test_create_repository_reuses_record(client):
    first = client.post(
        "/repositories",
        json={"url": "https://github.com/acme/demo", "analysis_mode": "quick", "top_k": 3},
    )
    second = client.post(
        "/repositories",
        json={"url": "https://github.com/acme/demo", "analysis_mode": "standard", "top_k": 8},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    listed = client.get("/repositories")
    names = [row["full_name"] for row in listed.json()]
    assert names.count("acme/demo") == 1
