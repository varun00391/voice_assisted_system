import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, conversations, health, modes, user_context, voice
from app.config.settings import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging, request_id_var
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware, error_response
from app.models.database import create_database, init_database
from app.providers.llm.base import LLMProvider
from app.providers.llm.factory import build_llm_providers
from app.providers.stt.base import STTProvider
from app.providers.stt.faster_whisper import FasterWhisperProvider
from app.services.llm.router import LLMRouter
from app.services.stt.service import TranscriptionService

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    stt_provider: STTProvider | None = None,
    llm_providers: list[LLMProvider] | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine, sessionmaker = create_database(settings.database_url)
        await init_database(engine)
        http_client = httpx.AsyncClient()

        providers = llm_providers if llm_providers is not None else build_llm_providers(settings, http_client)
        stt = stt_provider or FasterWhisperProvider(
            model_size=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            language=settings.whisper_language,
        )

        app.state.settings = settings
        app.state.sessionmaker = sessionmaker
        app.state.llm_router = LLMRouter(
            providers,
            failure_threshold=settings.circuit_breaker_failure_threshold,
            cooldown_seconds=settings.circuit_breaker_cooldown_seconds,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            max_continuations=settings.llm_max_continuations,
        )
        app.state.transcription_service = TranscriptionService(stt, settings)

        warm_up_task = asyncio.create_task(_warm_up(stt)) if settings.whisper_preload else None
        logger.info("application started", extra={"app_env": settings.app_env, "database": engine.dialect.name})
        try:
            yield
        finally:
            if warm_up_task and not warm_up_task.done():
                warm_up_task.cancel()
            await http_client.aclose()
            await engine.dispose()

    app = FastAPI(title="Voice-Assisted AI Assistant", version="1.0.0", lifespan=lifespan)

    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return error_response(exc, request_id_var.get())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in error["loc"] if part != "body"), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "The request is invalid.",
                    "details": details,
                    "request_id": request_id_var.get(),
                }
            },
        )

    for module in (health, modes, chat, voice, conversations, user_context):
        app.include_router(module.router)

    return app


async def _warm_up(stt: STTProvider) -> None:
    try:
        await asyncio.to_thread(stt.warm_up)
    except Exception:
        logger.exception("stt warm-up failed; the model will load on first request")


app = create_app()
