import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import init_db
from app.errors import AppError, app_error_handler, http_error_handler
from app.routers.health import router as health_router
from app.routers.repositories import router as repositories_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("codebase_rag")


def create_app() -> FastAPI:
    get_settings().ensure_dirs()
    init_db()
    app = FastAPI(
        title="Codebase RAG Assistant",
        version="0.1.0",
        description="Grounded code intelligence over GitHub repositories.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "code": "validation_error", "details": {"errors": exc.errors()}},
        )

    app.include_router(health_router)
    app.include_router(repositories_router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)


if __name__ == "__main__":
    main()
