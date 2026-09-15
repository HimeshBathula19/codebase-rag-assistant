from __future__ import annotations

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("CHROMA_DIR", str(data / "chroma"))
    monkeypatch.setenv("REPOS_DIR", str(data / "repos"))
    monkeypatch.setenv("APP_SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("USE_FAKE_EMBEDDINGS", "true")
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.chdir(ROOT)
    from app.config import get_settings
    from app.services.embeddings import reset_embedder

    get_settings.cache_clear()
    reset_embedder()
    from app.database import init_db

    init_db()
    yield
    get_settings.cache_clear()
    reset_embedder()


@pytest.fixture
def client(isolated_env):
    from fastapi.testclient import TestClient
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
