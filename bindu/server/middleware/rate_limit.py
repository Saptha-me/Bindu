"""Rate Limiting Middleware for Bindu server.

This middleware provides rate limiting capabilities using various backends
(Memory, Redis, Memcached). It helps prevent abuse and improves server stability.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.rate_limit")


class RateLimitBackend(ABC):
    """Abstract base class for rate limit backends."""

    @abstractmethod
    async def increment(self, key: str, window: int) -> int:
        """Increment the counter for the given key.

        Args:
            key: Rate limit key
            window: Time window in seconds

        Returns:
            Current count after increment
        """
        ...


class MemoryBackend(RateLimitBackend):
    """In-memory rate limit backend (not shared across processes)."""

    def __init__(self):
        self._counts: dict[str, list[int]] = {}

    async def increment(self, key: str, window: int) -> int:
        now = int(time.time())
        if key not in self._counts:
            self._counts[key] = []
        
        # Filter out old requests
        self._counts[key] = [t for t in self._counts[key] if t > now - window]
        self._counts[key].append(now)
        
        return len(self._counts[key])


class RedisBackend(RateLimitBackend):
    """Redis-based rate limit backend."""

    def __init__(self, redis_url: str):
        import redis.asyncio as redis
        self._redis = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)

    async def increment(self, key: str, window: int) -> int:
        pipeline = self._redis.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, window)
        result = await pipeline.execute()
        return result[0]


class MemcachedBackend(RateLimitBackend):
    """Memcached-based rate limit backend."""

    def __init__(self, host: str, port: int):
        import aiomcache
        self._client = aiomcache.Client(host, port)

    async def increment(self, key: str, window: int) -> int:
        # Memcached incr doesn't create key if not exists, so we need add/incr logic
        # However, aiomcache implementation of incr is a bit specific
        # We'll use a simple strategy: try incr, if fails (returns None), set to 1
        
        # Note: aiomcache key must be bytes
        b_key = key.encode('utf-8')
        
        try:
            val = await self._client.incr(b_key, 1)
        except Exception:
             val = None

        if val is None:
            # Key might not exist, try adding it
            try:
                await self._client.add(b_key, b"1", exptime=window)
                return 1
            except Exception:
                # If add fails, it might have been created concurrently, try incr again
                 try:
                    val = await self._client.incr(b_key, 1)
                    return val or 1 # Fallback
                 except: 
                     return 1
        
        return val


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.enabled = app_settings.rate_limit.enabled
        self.limit = app_settings.rate_limit.default_limit
        self.window = 60  # 1 minute window
        
        if not self.enabled:
            self.backend = None
            return

        backend_type = app_settings.rate_limit.backend
        if backend_type == "redis":
            if app_settings.scheduler.redis_url:
                 self.backend = RedisBackend(app_settings.scheduler.redis_url)
            else:
                 logger.warning("Redis URL not configured, falling back to memory backend")
                 self.backend = MemoryBackend()
        elif backend_type == "memcached":
            self.backend = MemcachedBackend(
                host=app_settings.rate_limit.memcached_host,
                port=app_settings.rate_limit.memcached_port
            )
        else:
            self.backend = MemoryBackend()
            
        logger.info(f"Rate limiting enabled with backend: {backend_type}, limit: {self.limit}/min")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled or not self.backend:
            return await call_next(request)

        # Identify client (simple IP based for now, can be extended to API key)
        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"

        try:
            current_count = await self.backend.increment(key, self.window)
            
            remaining = max(0, self.limit - current_count)
            reset_time = int(time.time()) + self.window

            headers = {
                "X-RateLimit-Limit": str(self.limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_time),
            }

            if current_count > self.limit:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return JSONResponse(
                    {"error": "Too Many Requests", "retry_after": self.window},
                    status_code=429,
                    headers=headers
                )
            
            response = await call_next(request)
            
            # Add headers to successful response
            for k, v in headers.items():
                response.headers[k] = v
                
            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Fail open if rate limiting fails
            return await call_next(request)
