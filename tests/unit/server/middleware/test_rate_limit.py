"""Unit tests for Rate Limit Middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from bindu.server.middleware.rate_limit import (
    MemoryBackend,
    RateLimitMiddleware,
    RedisBackend,
    MemcachedBackend
)
from bindu.settings import app_settings

# --- Mock App ---
async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
    response = JSONResponse({"status": "ok"})
    await response(scope, receive, send)

# --- Backend Tests ---

@pytest.mark.asyncio
async def test_memory_backend():
    backend = MemoryBackend()
    key = "test_key"
    window = 1
    
    # 1st increment
    count = await backend.increment(key, window)
    assert count == 1
    
    # 2nd increment
    count = await backend.increment(key, window)
    assert count == 2
    
    # Wait for window to expire (mock time would be better but simple sleep works for unit test if short)
    # However, for robustness, we should mock time.time()
    # But for now let's rely on logic verification:
    
    backend._counts[key] = [0] # Set a very old timestamp
    count = await backend.increment(key, window)
    # the old timestamp [0] should be filtered out, leaving only the new one
    assert count == 1


@pytest.mark.asyncio
async def test_redis_backend_mock():
    # Mock redis client
    mock_redis = MagicMock()
    mock_pipeline = MagicMock()
    mock_redis.pipeline.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock(return_value=[1, True]) # incr result, expire result
    
    # We can't easily instantiate RedisBackend without a real connection in __init__
    # So we patch the class or mock the instance.
    # Let's mock the internal _redis
    
    # Create instance with dummy url, it will try to connect. 
    # Better to mock redis.from_url
    with pytest.MonkeyPatch.context() as m:
        m.setattr("redis.asyncio.from_url", MagicMock(return_value=mock_redis))
        backend = RedisBackend("redis://localhost")
        
        count = await backend.increment("test_key", 60)
        assert count == 1
        mock_pipeline.incr.assert_called_with("test_key")
        mock_pipeline.expire.assert_called_with("test_key", 60)


@pytest.mark.asyncio
async def test_memcached_backend_mock():
    # Mock aiomcache client
    mock_client = MagicMock()
    mock_client.incr = AsyncMock(return_value=1)
    
    with pytest.MonkeyPatch.context() as m:
        # Mocking aiomcache.Client constructor isn't enough because it's instantiated in __init__
        # We need to mock the module
        mock_module = MagicMock()
        mock_module.Client.return_value = mock_client
        m.setitem(sys.modules, "aiomcache", mock_module)
        
        # We need to import inside to pick up the mock if we haven't imported it yet,
        # but we already imported classes.
        # So we have to rely on patching where it's used.
        # Just manually setting _client is easier for unit testing the logic.
        
        # Bypass __init__
        backend = MemcachedBackend.__new__(MemcachedBackend)
        backend._client = mock_client
        
        count = await backend.increment("test_key", 60)
        assert count == 1
        mock_client.incr.assert_called()


# --- Middleware Tests ---

@pytest.mark.asyncio
async def test_middleware_disabled():
    app_settings.rate_limit.enabled = False
    middleware = RateLimitMiddleware(mock_app)
    
    scope = {"type": "http", "client": ("127.0.0.1", 1234)}
    
    # It should just call next
    # We can verify by checking if backend is None
    assert middleware.backend is None


@pytest.mark.asyncio
async def test_middleware_enforces_limit():
    app_settings.rate_limit.enabled = True
    app_settings.rate_limit.default_limit = 2
    app_settings.rate_limit.backend = "memory"
    
    middleware = RateLimitMiddleware(mock_app)
    
    # Mock request
    async def call_next(request):
        return JSONResponse({"status": "ok"})
    
    request = Request(scope={"type": "http", "client": ("127.0.0.1", 1234)})
    
    # 1st request - OK
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Remaining"] == "1"
    
    # 2nd request - OK
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Remaining"] == "0"
    
    # 3rd request - 429
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert response.headers["X-RateLimit-Remaining"] == "0"
    import json
    body = json.loads(response.body.decode())
    assert body["error"] == "Too Many Requests"

import sys
