def test_invalid_github_url_rejected(client):
    response = client.post(
        "/repositories",
        json={"url": "https://gitlab.com/foo/bar", "analysis_mode": "standard", "top_k": 8},
    )
    assert response.status_code == 400
    payload = response.json()
    assert payload["code"] == "invalid_github_url"
    assert "token" not in str(payload).lower() or "github" in payload["error"].lower()
