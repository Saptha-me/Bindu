"""Scheduler factory for creating scheduler backend instances.

This module provides a factory function to create schedulers based on
configuration settings. It supports easy switching between scheduler implementations
without changing application code.

Usage:
    from bindu.server.scheduler.factory import create_scheduler

    # Create scheduler based on config
    scheduler = await create_scheduler(config)

    # Use scheduler
    await scheduler.run_task(params)
"""

from __future__ import annotations as _annotations

from bindu.common.models import SchedulerConfig
from bindu.utils.logging import get_logger

from .base import Scheduler
from .memory_scheduler import InMemoryScheduler

# Import RedisScheduler conditionally
try:
    from .redis_scheduler import RedisScheduler

    REDIS_AVAILABLE = True
except ImportError:
    RedisScheduler = None  # type: ignore[assignment]  # redis not installed
    REDIS_AVAILABLE = False

logger = get_logger("bindu.server.scheduler.factory")


async def create_scheduler(config: SchedulerConfig | None = None) -> Scheduler:
    """Create scheduler backend based on configuration.

    Reads the scheduler type from config and creates the appropriate scheduler instance.

    Supported backends:
    - "memory": InMemoryScheduler (default, single-process)
    - "redis": RedisScheduler (distributed, multi-process)

    Args:
        config: Scheduler configuration. If None, defaults to InMemoryScheduler.

    Returns:
        Scheduler instance ready to use

    Raises:
        ValueError: If unknown scheduler backend is specified or Redis is not available
        ConnectionError: If unable to connect to Redis

    Example:
        >>> config = SchedulerConfig(type="redis", redis_url="redis://localhost:6379")
        >>> scheduler = await create_scheduler(config)
        >>> await scheduler.run_task(params)
    """
    # Default to memory scheduler if no config provided
    if config is None:
        logger.info("No scheduler config provided, using in-memory scheduler")
        return InMemoryScheduler()

    backend = config.type.lower()

    logger.info(f"Creating scheduler backend: {backend}")

    if backend == "memory":
        logger.info("Using in-memory scheduler (single-process)")
        return InMemoryScheduler()

    elif backend == "redis":
        if not REDIS_AVAILABLE or RedisScheduler is None:
            raise ValueError(
                "Redis scheduler requires redis package. "
                "Install with: pip install redis[hiredis]"
            )

        logger.info("Using Redis scheduler (distributed, multi-process)")

        # Build Redis URL if not provided
        redis_url = config.redis_url
        if not redis_url:
            # Construct URL from individual components
            auth = f":{config.redis_password}@" if config.redis_password else ""
            redis_url = f"redis://{auth}{config.redis_host}:{config.redis_port}/{config.redis_db}"

        scheduler = RedisScheduler(
            redis_url=redis_url,
            queue_name=config.queue_name,
            max_connections=config.max_connections,
            retry_on_timeout=config.retry_on_timeout,
        )

        # Test connection by entering context manager
        try:
            await scheduler.__aenter__()
            logger.info("Redis scheduler connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ConnectionError(f"Unable to connect to Redis at {redis_url}: {e}")

        return scheduler

    else:
        raise ValueError(
            f"Unknown scheduler backend: {backend}. Supported backends: memory, redis"
        )


async def close_scheduler(scheduler: Scheduler) -> None:
    """Close scheduler connection gracefully.

    Args:
        scheduler: Scheduler instance to close

    Example:
        >>> scheduler = await create_scheduler(config)
        >>> # ... use scheduler ...
        >>> await close_scheduler(scheduler)
    """
    if REDIS_AVAILABLE and isinstance(scheduler, RedisScheduler):
        await scheduler.__aexit__(None, None, None)
        logger.info("Redis scheduler connection closed")
    else:
        logger.debug(f"Scheduler {type(scheduler).__name__} does not require cleanup")
