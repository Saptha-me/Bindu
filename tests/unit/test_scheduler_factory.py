"""Unit tests for scheduler factory."""

from unittest.mock import AsyncMock, patch

import pytest

from bindu.common.models import SchedulerConfig
from bindu.server.scheduler.factory import create_scheduler
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.scheduler.redis_scheduler import RedisScheduler


class TestSchedulerFactory:
    """Test scheduler factory creation."""

    @pytest.mark.asyncio
    async def test_create_scheduler_default(self):
        """Test creating scheduler with no config (defaults to memory)."""
        scheduler = await create_scheduler(None)

        assert isinstance(scheduler, InMemoryScheduler)

    @pytest.mark.asyncio
    async def test_create_scheduler_memory(self):
        """Test creating memory scheduler explicitly."""
        config = SchedulerConfig(type="memory")
        scheduler = await create_scheduler(config)

        assert isinstance(scheduler, InMemoryScheduler)

    @pytest.mark.asyncio
    async def test_create_scheduler_redis_with_url(self):
        """Test creating Redis scheduler with URL."""
        config = SchedulerConfig(type="redis", redis_url="redis://localhost:6379/0")

        scheduler = await create_scheduler(config)

        assert isinstance(scheduler, RedisScheduler)
        assert scheduler.redis_url == "redis://localhost:6379/0"
        # Connection is tested when entering context manager, not in factory

    @pytest.mark.asyncio
    async def test_create_scheduler_redis_with_components(self):
        """Test creating Redis scheduler with individual components."""
        config = SchedulerConfig(
            type="redis",
            redis_host="redis.example.com",
            redis_port=6380,
            redis_password="secret",  # pragma: allowlist secret
            redis_db=1,
            queue_name="custom:queue",
        )

        scheduler = await create_scheduler(config)

        assert isinstance(scheduler, RedisScheduler)
        # URL should be constructed from components
        assert "redis.example.com" in scheduler.redis_url
        assert "6380" in scheduler.redis_url
        assert scheduler.queue_name == "custom:queue"

    @pytest.mark.asyncio
    async def test_create_scheduler_redis_connection_failure(self):
        """Test Redis scheduler connection failure when entering context."""
        config = SchedulerConfig(type="redis", redis_url="redis://invalid:6379/0")

        scheduler = await create_scheduler(config)
        assert isinstance(scheduler, RedisScheduler)

        # Connection failure happens when entering context manager
        import redis.asyncio as redis

        mock_redis_client = AsyncMock()
        mock_redis_client.ping.side_effect = redis.RedisError("Connection refused")

        with patch("redis.asyncio.from_url", return_value=mock_redis_client):
            with pytest.raises(ConnectionError, match="Unable to connect to Redis"):
                await scheduler.__aenter__()

    @pytest.mark.asyncio
    async def test_create_scheduler_unknown_type(self):
        """Test creating scheduler with unknown type."""
        # This would fail at Pydantic validation level in real usage
        # but we can test the factory's error handling
        with pytest.raises(ValueError):
            # Bypass Pydantic validation for testing
            config = SchedulerConfig.__new__(SchedulerConfig)
            object.__setattr__(config, "type", "unknown")
            await create_scheduler(config)


class TestSchedulerFactoryRedisAvailability:
    """Test scheduler factory with Redis availability checks."""

    @pytest.mark.asyncio
    async def test_redis_not_available(self):
        """Test creating Redis scheduler when redis package is not available."""
        config = SchedulerConfig(type="redis", redis_url="redis://localhost:6379/0")

        # Mock Redis as not available
        with patch("bindu.server.scheduler.factory.REDIS_AVAILABLE", False):
            with patch("bindu.server.scheduler.factory.RedisScheduler", None):
                with pytest.raises(
                    ValueError, match="Redis scheduler requires redis package"
                ):
                    await create_scheduler(config)
