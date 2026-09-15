def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "codebase-rag-assistant"
    assert payload["embeddings"]["model"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert "llm" in payload
    assert "api_key" not in str(payload).lower() or payload["llm"]["configured"] is False
