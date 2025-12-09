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
    If no config is provided, uses app_settings.scheduler defaults.

    Supported backends:
    - "memory": InMemoryScheduler (default, single-process)
    - "redis": RedisScheduler (distributed, multi-process)

    Args:
        config: Scheduler configuration. If None, uses app_settings.scheduler.

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
    from bindu.settings import app_settings

    # Use settings if no config provided
    if config is None:
        backend = app_settings.scheduler.backend
        logger.info(f"No scheduler config provided, using settings: {backend}")

        if backend == "memory":
            return InMemoryScheduler()
        elif backend == "redis":
            # Build config from settings
            config = SchedulerConfig(
                type="redis",
                redis_url=app_settings.scheduler.redis_url,
                redis_host=app_settings.scheduler.redis_host,
                redis_port=app_settings.scheduler.redis_port,
                redis_password=app_settings.scheduler.redis_password,
                redis_db=app_settings.scheduler.redis_db,
                queue_name=app_settings.scheduler.queue_name,
                max_connections=app_settings.scheduler.max_connections,
                retry_on_timeout=app_settings.scheduler.retry_on_timeout,
            )
        else:
            raise ValueError(f"Unknown scheduler backend in settings: {backend}")

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
