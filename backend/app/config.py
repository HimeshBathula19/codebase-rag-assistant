from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret_key: str = "change-me-to-a-long-random-string"

    data_dir: Path = ROOT_DIR / "data"
    chroma_dir: Path = ROOT_DIR / "data" / "chroma"
    repos_dir: Path = ROOT_DIR / "data" / "repos"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_provider: str = "local"
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_api_model: str = "text-embedding-3-small"
    use_fake_embeddings: bool = False

    semantic_weight: float = 0.7
    keyword_weight: float = 0.3
    default_top_k: int = 8

    github_token: str = ""

    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    max_file_bytes: int = 1_000_000
    chunk_max_lines: int = 80
    chunk_overlap_lines: int = 8

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
