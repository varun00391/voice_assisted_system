import logging
import re
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import AppError, RateLimitExceededError
from app.core.logging import request_id_var

logger = logging.getLogger("app.request")

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def error_response(error: AppError, request_id: str | None) -> JSONResponse:
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.code, "message": error.message, "request_id": request_id}},
        headers=headers,
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, logs request outcome and converts unhandled errors to safe JSON."""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _VALID_REQUEST_ID.match(incoming) else uuid4().hex
        token = request_id_var.set(request_id)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("unhandled error", extra={"path": request.url.path})
                response = error_response(AppError(), request_id)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            return response
        finally:
            request_id_var.reset(token)


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0, clock=time.monotonic):
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        if len(self._hits) > 10_000:
            self._prune(now)
        return True

    def _prune(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] >= self._window]:
            del self._hits[key]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client in-memory rate limit for /api routes (single backend process)."""

    def __init__(self, app, limit_per_minute: int):
        super().__init__(app)
        self._limiter = SlidingWindowRateLimiter(limit_per_minute) if limit_per_minute > 0 else None

    async def dispatch(self, request: Request, call_next):
        if self._limiter and request.url.path.startswith("/api/") and request.method != "OPTIONS":
            client = request.client.host if request.client else "unknown"
            if not self._limiter.allow(client):
                return error_response(RateLimitExceededError(), request_id_var.get())
        return await call_next(request)
