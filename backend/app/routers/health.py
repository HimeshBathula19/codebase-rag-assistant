from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    settings = get_settings()
    llm_configured = bool(settings.llm_api_key)
    return {
        "status": "ok",
        "service": "codebase-rag-assistant",
        "embeddings": {
            "model": settings.embedding_model,
            "provider": settings.embedding_provider,
            "fake": settings.use_fake_embeddings,
        },
        "llm": {
            "configured": llm_configured,
            "model": settings.llm_model if llm_configured else None,
            "base_url": settings.llm_base_url if llm_configured else None,
        },
        "retrieval": {
            "semantic_weight": settings.semantic_weight,
            "keyword_weight": settings.keyword_weight,
            "default_top_k": settings.default_top_k,
        },
        "chroma_dir": str(settings.chroma_dir),
    }
