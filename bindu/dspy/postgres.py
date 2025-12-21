# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - Bindu 🌻

"""PostgreSQL data access layer for DSPy training data.

This module provides read-only access to interaction data from the database
for offline prompt optimization. It uses SQLAlchemy Core with simple SQL
queries to fetch and convert task data into training examples.

The module implements a singleton pattern for database connections to avoid
creating new connection pools on every call, which improves performance
significantly for repeated training runs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bindu.server.storage.schema import task_feedback_table, tasks_table
from bindu.utils.logging import get_logger

from .config import MAX_INTERACTIONS_QUERY_LIMIT

logger = get_logger("bindu.dspy.postgres")


# =============================================================================
# Connection Pool Configuration
# =============================================================================

# Pool size settings
# Single-threaded training uses 1 connection; pool allows burst capacity if needed
POOL_SIZE = 1  # Base connections (1 active + 1 standby)
MAX_OVERFLOW = 1  # Additional connections for concurrent/burst scenarios

# Timeout settings (in seconds)
POOL_TIMEOUT = 30  # Seconds to wait for a connection from the pool
POOL_RECYCLE = 1800  # Recycle connections after 30 minutes (prevents stale connections)
POOL_PRE_PING = True  # Verify connection is alive before using

# Idle connection settings
POOL_IDLE_TIMEOUT = 300  # Close idle connections after 5 minutes (asyncpg specific)


# =============================================================================
# Global Connection Pool (Singleton)
# =============================================================================

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_database_url() -> str:
    """Get and validate the database URL from environment.

    Returns:
        Properly formatted async database URL

    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL is not set
    """
    database_url = os.getenv("STORAGE__POSTGRES_URL")
    if not database_url:
        raise RuntimeError("STORAGE__POSTGRES_URL environment variable not set")

    # Convert to async driver URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        database_url = f"postgresql+asyncpg://{database_url}"

    return database_url


def _get_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Get or create the database engine and session factory.

    This implements a singleton pattern - the engine is created once
    and reused for all subsequent calls. This avoids the overhead of
    creating new connection pools on every query.

    Returns:
        Tuple of (engine, session_factory)

    Raises:
        RuntimeError: If database URL is not configured
    """
    global _engine, _session_factory

    if _engine is not None and _session_factory is not None:
        return _engine, _session_factory

    database_url = _get_database_url()

    logger.info("Creating database engine for DSPy training")

    # Create async engine with connection pooling
    _engine = create_async_engine(
        database_url,
        # Pool size configuration
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        # Connection health checks
        pool_pre_ping=POOL_PRE_PING,
        # Connection lifecycle
        pool_recycle=POOL_RECYCLE,
        pool_timeout=POOL_TIMEOUT,
        # asyncpg-specific: close idle connections
        connect_args={
            "command_timeout": 60,  # Query timeout in seconds
            "timeout": POOL_TIMEOUT,  # Connection timeout
        },
        # Disable SQL echo for performance
        echo=False,
    )

    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info(
        f"Database engine created (pool_size={POOL_SIZE}, "
        f"max_overflow={MAX_OVERFLOW}, recycle={POOL_RECYCLE}s)"
    )

    return _engine, _session_factory


async def dispose_engine() -> None:
    """Dispose the database engine and close all connections.

    Call this when shutting down the application or when you want to
    force-close all database connections. After calling this, the next
    call to fetch_raw_task_data() will create a new engine.

    This is useful for:
    - Application shutdown
    - Testing (to ensure clean state between tests)
    - Forcing reconnection after database restart
    """
    global _engine, _session_factory

    if _engine is not None:
        logger.info("Disposing database engine")
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")


def is_engine_initialized() -> bool:
    """Check if the database engine has been initialized.

    Returns:
        True if engine exists, False otherwise
    """
    return _engine is not None


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class RawTaskData:
    """Raw task data fetched from the database.

    This represents the raw data before interaction extraction.

    Attributes:
        id: Task UUID
        history: List of message dictionaries from the conversation
        created_at: Timestamp when the task was created
        feedback_data: Optional feedback dictionary (ratings, thumbs up/down)
    """

    id: UUID
    history: list[dict[str, Any]]
    created_at: Any
    feedback_data: dict[str, Any] | None = None


# =============================================================================
# Data Access Functions
# =============================================================================


async def fetch_raw_task_data(
    limit: int = MAX_INTERACTIONS_QUERY_LIMIT,
) -> list[RawTaskData]:
    """Fetch raw task data with feedback from PostgreSQL.

    This function reads task data from the database along with associated
    feedback using a LEFT JOIN. It returns raw data that needs to be
    processed by the extraction and filtering pipeline.

    The function uses a global connection pool for efficiency. The first
    call creates the pool, and subsequent calls reuse it.

    Args:
        limit: Maximum number of tasks to fetch (default: 10000)

    Returns:
        List of RawTaskData objects containing task history and feedback

    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL environment variable is not set
        ConnectionError: If unable to connect to database or query fails
    """
    logger.info(f"Fetching up to {limit} tasks from database")

    try:
        # Get or create engine (singleton)
        _, session_factory = _get_engine()

        async with session_factory() as session:
            # Query tasks with LEFT JOIN to feedback
            # This gets all tasks and their associated feedback (if any)
            stmt = (
                select(
                    tasks_table.c.id,
                    tasks_table.c.history,
                    tasks_table.c.created_at,
                    task_feedback_table.c.feedback_data,
                )
                .select_from(
                    tasks_table.outerjoin(
                        task_feedback_table,
                        tasks_table.c.id == task_feedback_table.c.task_id,
                    )
                )
                .order_by(tasks_table.c.created_at.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.fetchall()

            # Convert rows to dataclass instances
            raw_tasks = [
                RawTaskData(
                    id=row.id,
                    history=row.history or [],
                    created_at=row.created_at,
                    feedback_data=row.feedback_data,
                )
                for row in rows
            ]

        logger.info(f"Fetched {len(raw_tasks)} raw tasks from database")
        return raw_tasks

    except Exception as e:
        logger.error(f"Failed to fetch raw task data from database: {e}")
        raise ConnectionError(f"Failed to fetch raw task data: {e}") from e