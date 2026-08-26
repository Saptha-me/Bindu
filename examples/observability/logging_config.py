# examples/observability/logging_config.py
"""
Structured logging + request metrics for Starlette/FastAPI apps (Bindu server).

What you get:
- JSON logs (toggle on/off)
- Request/response timing in ms
- Per-request correlation ID (request_id) auto-injected into every log line
- Stdlib + Uvicorn logs routed through Loguru (single, consistent format)

Usage (see README snippet below):
    from examples.observability.logging_config import setup_logging, instrument_starlette
    setup_logging(level="INFO", json_logs=True)
    instrument_starlette(app)
"""

from __future__ import annotations

import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Callable, Optional

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# -----------------------------------------------------------------------------
# Log context (request_id) handling
# -----------------------------------------------------------------------------
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the current request ID from context."""
    return _request_id_ctx.get()


def _set_request_id(value: str) -> None:
    """Set the request ID in the context variable."""
    _request_id_ctx.set(value)


# -----------------------------------------------------------------------------
# Route stdlib + Uvicorn logs into Loguru
# -----------------------------------------------------------------------------
class InterceptHandler(logging.Handler):
    """Bridge stdlib logging records into Loguru for unified structured logging."""

    def emit(self, record: logging.LogRecord) -> None:
        """Forward stdlib records to Loguru, preserving level and exception info."""
        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno

        logger.bind(request_id=get_request_id()).opt(
            depth=6, exception=record.exc_info
        ).log(level, record.getMessage())


def _patch_logging() -> None:
    """Patch stdlib and Uvicorn loggers to route logs through Loguru."""
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "asyncio"):
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False


# -----------------------------------------------------------------------------
# Public: setup logging
# -----------------------------------------------------------------------------
def setup_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure Loguru as the single logging sink for structured output.

    Args:
        level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
        json_logs: If True, emit logs as structured JSON.
    """
    logger.remove()
    logger.add(
        sys.stdout,
        serialize=json_logs,
        level=level.upper(),
        backtrace=True,
        diagnose=False,  # keep logs concise in production
        enqueue=True,  # safer in multi-worker setups
    )

    _patch_logging()
    logger.bind(request_id="-").info(
        "Structured logging configured | level={} | json_logs={}",
        level.upper(),
        json_logs,
    )


# -----------------------------------------------------------------------------
# Starlette middleware to inject request_id and measure latency
# -----------------------------------------------------------------------------
class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request IDs and logs request metrics."""

    def __init__(
        self,
        app,
        *,
        get_request_id_header: Optional[str] = "X-Request-ID",
        response_request_id_header: Optional[str] = "X-Request-ID",
        sample: float = 1.0,
    ) -> None:
        """Initialize middleware.

        Args:
            get_request_id_header: Header to reuse request ID if available.
            response_request_id_header: Header to include in response for correlation.
            sample: Fraction (0.0–1.0) of requests to log (default: 1.0 for all).
        """
        super().__init__(app)
        self.get_request_id_header = get_request_id_header
        self.response_request_id_header = response_request_id_header
        self.sample = sample

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Measure latency and emit structured log lines for each request."""
        rid = request.headers.get(self.get_request_id_header) or str(uuid.uuid4())
        _set_request_id(rid)

        start_ns = time.perf_counter_ns()
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
            logger.bind(request_id=rid).info(
                "HTTP {method} {path} -> {status} in {duration_ms:.2f} ms",
                method=request.method,
                path=request.url.path,
                status=getattr(response, "status_code", "-"),
                duration_ms=duration_ms,
            )

        if self.response_request_id_header:
            response.headers[self.response_request_id_header] = rid
        return response


def instrument_starlette(app) -> None:
    """Add RequestContextLogMiddleware to a Starlette or FastAPI app."""
    app.add_middleware(RequestContextLogMiddleware)
