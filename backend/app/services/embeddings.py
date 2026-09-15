from __future__ import annotations

import hashlib
import logging
import threading
from typing import Sequence

import numpy as np

from app.config import get_settings
from app.errors import AppError

logger = logging.getLogger("codebase_rag.embeddings")


def _is_blocked_native(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(
        needle in text
        for needle in (
            "dll load failed",
            "application control",
            "winerror 5",
            "blocked this file",
            "error loading",
        )
    )


class OpenAICompatibleEmbedder:
    def __init__(self, base_url: str, api_key: str, model: str, dimension: int = 1536):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        import httpx

        url = self.base_url + "/embeddings"
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "input": list(texts)},
                )
        except httpx.HTTPError as exc:
            raise AppError("embedding_failure", "Embedding API request failed.", 502) from exc
        if response.status_code >= 400:
            raise AppError("embedding_failure", "Embedding API request failed.", 502)
        data = response.json()
        items = sorted(data.get("data") or [], key=lambda row: row.get("index", 0))
        vectors = [row["embedding"] for row in items]
        if vectors:
            self.dimension = len(vectors[0])
        return vectors


class OnnxMiniLMEmbedder:
    """Real all-MiniLM-L6-v2 embeddings via ONNX Runtime (no PyTorch)."""

    def __init__(self) -> None:
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.dimension = 384
        self._session = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._session is not None:
            return
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        cache = get_settings().data_dir / "models"
        cache.mkdir(parents=True, exist_ok=True)
        onnx_path = hf_hub_download(
            "Xenova/all-MiniLM-L6-v2",
            "onnx/model.onnx",
            cache_dir=str(cache),
        )
        tokenizer_path = hf_hub_download(
            "Xenova/all-MiniLM-L6-v2",
            "tokenizer.json",
            cache_dir=str(cache),
        )
        self._tokenizer = Tokenizer.from_file(tokenizer_path)
        self._tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        self._tokenizer.enable_truncation(max_length=256)
        self._session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        self._load()
        encoded = self._tokenizer.encode_batch(list(texts))
        input_ids = np.array([item.ids for item in encoded], dtype=np.int64)
        attention_mask = np.array([item.attention_mask for item in encoded], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)
        feeds = {"input_ids": input_ids, "attention_mask": attention_mask}
        input_names = {i.name for i in self._session.get_inputs()}
        if "token_type_ids" in input_names:
            feeds["token_type_ids"] = token_type_ids
        outputs = self._session.run(None, feeds)[0]
        mask = attention_mask.astype(np.float32)[:, :, None]
        summed = (outputs * mask).sum(axis=1)
        counts = np.clip(mask.sum(axis=1), 1e-9, None)
        pooled = summed / counts
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        pooled = pooled / np.clip(norms, 1e-9, None)
        return pooled.astype(float).tolist()


class EmbeddingService:
    def __init__(self) -> None:
        self._impl = None
        self._lock = threading.Lock()
        self.model_name = get_settings().embedding_model
        self.dimension = 384
        self.provider = "uninitialized"

    def _openai_fallback(self, reason: str) -> OpenAICompatibleEmbedder:
        settings = get_settings()
        api_key = settings.embedding_api_key or settings.llm_api_key
        base = settings.embedding_base_url or settings.llm_base_url
        if not api_key:
            raise AppError(
                "embedding_failure",
                f"Local embeddings failed ({reason}). Configure EMBEDDING_API_KEY for an OpenAI-compatible embedding API.",
                500,
            )
        logger.warning("Using OpenAI-compatible embeddings because local model failed: %s", reason)
        self.provider = "openai"
        self.model_name = settings.embedding_api_model
        return OpenAICompatibleEmbedder(base, api_key, settings.embedding_api_model)

    def _load_local(self):
        settings = get_settings()
        requested = (settings.embedding_provider or "local").strip().lower()
        if requested == "openai":
            return self._openai_fallback("provider=openai")
        if requested == "onnx":
            self.provider = "onnx"
            self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
            return OnnxMiniLMEmbedder()
        from sentence_transformers import SentenceTransformer

        self.provider = "sentence-transformers"
        self.model_name = settings.embedding_model
        return SentenceTransformer(settings.embedding_model)

    def _load(self):
        if self._impl is not None:
            return self._impl
        with self._lock:
            if self._impl is not None:
                return self._impl
            settings = get_settings()
            if settings.use_fake_embeddings:
                self._impl = "fake"
                self.provider = "test"
                return self._impl
            try:
                self._impl = self._load_local()
                return self._impl
            except AppError:
                raise
            except Exception as exc:
                if not _is_blocked_native(exc) and (settings.embedding_provider or "local").lower() == "openai":
                    raise AppError("embedding_failure", f"Embedding generation failed: {type(exc).__name__}", 500) from exc
                logger.warning("sentence-transformers failed (%s); trying ONNX MiniLM", type(exc).__name__)
                try:
                    onnx = OnnxMiniLMEmbedder()
                    onnx._load()
                    self._impl = onnx
                    self.provider = "onnx"
                    self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
                    return self._impl
                except Exception as onnx_exc:
                    logger.warning("ONNX MiniLM failed: %s", type(onnx_exc).__name__)
                    self._impl = self._openai_fallback(str(type(exc).__name__))
                    return self._impl

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        if model == "fake":
            return [self._fake_vector(text) for text in texts]
        if isinstance(model, (OnnxMiniLMEmbedder, OpenAICompatibleEmbedder)):
            return model.encode(texts)
        vectors = model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [vec.astype(float).tolist() for vec in np.atleast_2d(vectors)]

    def _fake_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        vec = rng.standard_normal(self.dimension)
        vec = vec / (np.linalg.norm(vec) or 1.0)
        for token in set(text.lower().split()):
            h = hashlib.md5(token.encode("utf-8")).digest()
            idx = int.from_bytes(h[:2], "little") % self.dimension
            vec[idx] += 0.15
        vec = vec / (np.linalg.norm(vec) or 1.0)
        return vec.astype(float).tolist()


_service: EmbeddingService | None = None


def get_embedder() -> EmbeddingService:
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service


def reset_embedder() -> None:
    global _service
    _service = None
