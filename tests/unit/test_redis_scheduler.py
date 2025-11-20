"""Unit tests for Redis Scheduler implementation."""

import asyncio
import os
from uuid import uuid4

import pytest

# Skip tests if Redis is not available
redis_available = os.getenv("REDIS_URL") is not None
skip_redis = pytest.mark.skipif(
    not redis_available,
    reason="Redis URL not configured. Set REDIS_URL environment variable to run these tests.",
)


@skip_redis
@pytest.mark.asyncio
async def test_scheduler_initialization():
    """Test that scheduler initializes and connects to Redis."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        assert scheduler._redis_client is not None
        health = await scheduler.health_check()
        assert health is True


@skip_redis
@pytest.mark.asyncio
async def test_scheduler_basic_flow():
    """Test scheduler can send and receive operations."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        await scheduler.clear_queue()
        task_id = uuid4()
        context_id = uuid4()
        received = []

        async def consumer():
            """Consume one task operation."""
            async for op in scheduler.receive_task_operations():
                received.append(op)
                return

        # Start consumer
        consumer_task = asyncio.create_task(consumer())

        # Give consumer time to start
        await asyncio.sleep(0.1)

        # Send task
        await scheduler.run_task({"task_id": task_id, "context_id": context_id})

        # Wait for consumer
        await asyncio.wait_for(consumer_task, timeout=5.0)

        assert len(received) == 1
        assert received[0]["operation"] == "run"
        # UUIDs are serialized as strings in Redis
        assert received[0]["params"]["task_id"] == str(task_id)


@skip_redis
@pytest.mark.asyncio
async def test_scheduler_all_operations():
    """Test all scheduler operations."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        await scheduler.clear_queue()
        task_id = uuid4()
        context_id = uuid4()
        received = []

        async def consumer():
            """Consume operations."""
            count = 0
            async for op in scheduler.receive_task_operations():
                received.append(op)
                count += 1
                if count >= 4:
                    return

        # Start consumer
        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.1)

        # Send operations
        await scheduler.run_task({"task_id": task_id, "context_id": context_id})
        await scheduler.cancel_task({"task_id": task_id})
        await scheduler.pause_task({"task_id": task_id})
        await scheduler.resume_task({"task_id": task_id})

        # Wait for consumer
        await asyncio.wait_for(consumer_task, timeout=5.0)

        assert len(received) == 4
        assert received[0]["operation"] == "run"
        assert received[1]["operation"] == "cancel"
        assert received[2]["operation"] == "pause"
        assert received[3]["operation"] == "resume"


@skip_redis
@pytest.mark.asyncio
async def test_queue_length():
    """Test getting queue length."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        await scheduler.clear_queue()
        task_id = uuid4()
        context_id = uuid4()

        # Queue should be empty initially
        length = await scheduler.get_queue_length()
        assert length == 0

        # Add tasks
        await scheduler.run_task({"task_id": task_id, "context_id": context_id})
        await scheduler.run_task({"task_id": uuid4(), "context_id": context_id})
        await scheduler.run_task({"task_id": uuid4(), "context_id": context_id})

        # Check length
        length = await scheduler.get_queue_length()
        assert length == 3


@skip_redis
@pytest.mark.asyncio
async def test_clear_queue():
    """Test clearing the queue."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        await scheduler.clear_queue()
        task_id = uuid4()
        context_id = uuid4()

        # Add some tasks
        await scheduler.run_task({"task_id": task_id, "context_id": context_id})
        await scheduler.run_task({"task_id": uuid4(), "context_id": context_id})

        # Verify tasks were added
        length = await scheduler.get_queue_length()
        assert length == 2

        # Clear queue
        deleted = await scheduler.clear_queue()
        assert deleted == 1  # Redis delete returns 1 for key deletion

        # Verify queue is empty
        length = await scheduler.get_queue_length()
        assert length == 0


@skip_redis
@pytest.mark.asyncio
async def test_multiple_producers_single_consumer():
    """Test multiple producers sending to single consumer."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        await scheduler.clear_queue()
        num_tasks = 10
        received = []

        async def consumer():
            """Consume all tasks."""
            count = 0
            async for op in scheduler.receive_task_operations():
                received.append(op)
                count += 1
                if count >= num_tasks:
                    return

        async def producer(task_num):
            """Produce a single task."""
            await scheduler.run_task(
                {"task_id": uuid4(), "context_id": uuid4(), "task_num": task_num}
            )

        # Start consumer
        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.1)

        # Start multiple producers
        producer_tasks = [asyncio.create_task(producer(i)) for i in range(num_tasks)]
        await asyncio.gather(*producer_tasks)

        # Wait for consumer
        await asyncio.wait_for(consumer_task, timeout=10.0)

        assert len(received) == num_tasks
        assert all(op["operation"] == "run" for op in received)


@skip_redis
@pytest.mark.asyncio
async def test_health_check():
    """Test health check functionality."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    test_queue = f"bindu:test:queue:{uuid4()}"

    async with RedisScheduler(redis_url=redis_url, queue_name=test_queue) as scheduler:
        # Should be healthy
        assert await scheduler.health_check() is True

        # Close connection
        if scheduler._redis_client:
            await scheduler._redis_client.aclose()
            scheduler._redis_client = None

        # Should be unhealthy
        assert await scheduler.health_check() is False


@pytest.mark.asyncio
async def test_redis_scheduler_context_manager_error_handling():
    """Test error handling in context manager."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    # Invalid Redis URL should raise an error
    scheduler = RedisScheduler(
        redis_url="redis://invalid-host:9999", socket_connect_timeout=1
    )

    with pytest.raises(Exception):
        async with scheduler:
            pass  # Should never reach here


@pytest.mark.asyncio
async def test_redis_scheduler_requires_context_manager():
    """Test that scheduler requires context manager."""
    from bindu.server.scheduler.redis_scheduler import RedisScheduler

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    scheduler = RedisScheduler(redis_url=redis_url)

    # Should raise error if used without context manager
    with pytest.raises(RuntimeError, match="Redis client not initialized"):
        await scheduler.run_task({"task_id": uuid4(), "context_id": uuid4()})
