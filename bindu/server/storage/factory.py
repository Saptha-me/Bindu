"""Storage factory for creating storage backend instances.

This module provides a factory function to create storage backends based on
configuration settings. It supports easy switching between storage implementations
without changing application code.

Usage:
    from bindu.server.storage.factory import create_storage
    
    # Create storage based on settings
    storage = await create_storage()
    
    # Use storage
    task = await storage.load_task(task_id)
"""

from __future__ import annotations as _annotations

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .base import Storage
from .memory_storage import InMemoryStorage

# Import PostgresStorage conditionally
try:
    from .postgres_storage import PostgresStorage
    POSTGRES_AVAILABLE = True
except ImportError:
    PostgresStorage = None  # type: ignore[assignment]  # SQLAlchemy not installed
    POSTGRES_AVAILABLE = False

logger = get_logger("bindu.server.storage.factory")


async def create_storage() -> Storage:
    """Create storage backend based on configuration.

    Reads the storage backend type from app_settings.storage.backend and
    creates the appropriate storage instance.

    Supported backends:
    - "memory": InMemoryStorage (default, non-persistent)
    - "postgres": PostgresStorage (persistent)

    Returns:
        Storage instance ready to use

    Raises:
        ValueError: If unknown storage backend is specified
        ConnectionError: If unable to connect to storage backend

    Example:
        >>> storage = await create_storage()
        >>> task = await storage.load_task(task_id)
    """
    backend = app_settings.storage.backend.lower()

    logger.info(f"Creating storage backend: {backend}")

    if backend == "memory":
        logger.info("Using in-memory storage (non-persistent)")
        return InMemoryStorage()

    elif backend == "postgres":
        if not POSTGRES_AVAILABLE or PostgresStorage is None:
            raise ValueError(
                "PostgreSQL storage requires SQLAlchemy. "
                "Install with: pip install sqlalchemy[asyncio] asyncpg"
            )
        
        logger.info("Using PostgreSQL storage with SQLAlchemy (persistent)")
        storage = PostgresStorage(
            database_url=app_settings.storage.postgres_url,
            pool_min=app_settings.storage.postgres_pool_min,
            pool_max=app_settings.storage.postgres_pool_max,
            timeout=app_settings.storage.postgres_timeout,
            command_timeout=app_settings.storage.postgres_command_timeout,
        )

        # Connect to database
        await storage.connect()

        # Run migrations if enabled
        if app_settings.storage.run_migrations_on_startup:
            logger.info("Running database migrations...")
            try:
                await run_migrations()
                logger.info("Database migrations completed successfully")
            except Exception as e:
                logger.error(f"Failed to run migrations: {e}")
                # Don't fail startup, just log the error
                # Migrations can be run manually if needed

        return storage

    else:
        raise ValueError(
            f"Unknown storage backend: {backend}. "
            f"Supported backends: memory, postgres"
        )


async def run_migrations() -> None:
    """Run database migrations using Alembic.

    This function runs Alembic migrations programmatically.
    It's called automatically on startup if run_migrations_on_startup is True.

    Raises:
        Exception: If migrations fail
    """
    try:
        from alembic import command  # type: ignore[import-untyped]
        from alembic.config import Config  # type: ignore[import-untyped]

        # Create Alembic config
        alembic_cfg = Config("alembic.ini")

        # Override database URL from settings
        alembic_cfg.set_main_option("sqlalchemy.url", app_settings.storage.postgres_url)

        # Run migrations to head
        command.upgrade(alembic_cfg, "head")

    except ImportError:
        logger.warning(
            "Alembic not installed. Skipping automatic migrations. "
            "Run 'pip install alembic' or 'alembic upgrade head' manually."
        )
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise


async def close_storage(storage: Storage) -> None:
    """Close storage connection gracefully.

    Args:
        storage: Storage instance to close

    Example:
        >>> storage = await create_storage()
        >>> # ... use storage ...
        >>> await close_storage(storage)
    """
    if isinstance(storage, PostgresStorage):
        await storage.disconnect()
        logger.info("PostgreSQL storage connection closed")
    else:
        logger.debug(f"Storage {type(storage).__name__} does not require cleanup")
