import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, conversations, demo, documents, health, plans
from app.core.config import get_settings
from app.core.logging import RequestContextMiddleware, configure_logging
from app.services.embeddings import EmbeddingError
from app.services.llm import LLMError

logger = logging.getLogger("api.errors")
settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="Academic Assistant API", version="0.1.0", docs_url="/docs")
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
for router in (
    health.router,
    demo.router,
    chat.router,
    conversations.router,
    plans.router,
    documents.router,
):
    app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(LLMError)
async def llm_error(request: Request, exc: LLMError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "llm_unavailable",
            "detail": "The language model is currently unavailable. Please try again.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(EmbeddingError)
async def embedding_error(request: Request, exc: EmbeddingError):
    return JSONResponse(
        status_code=503,
        content={
            "error": "embedding_unavailable",
            "detail": "Document search is currently unavailable. Please try again.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    logger.exception(
        "request_id=%s unhandled_error=%s",
        getattr(request.state, "request_id", None),
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "The request could not be completed.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )
