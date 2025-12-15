# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""PostgreSQL data access layer for DSPy training data.

This module provides read-only access to interaction data from the database
for offline prompt optimization. It uses SQLAlchemy Core with simple SQL
queries to fetch and convert task data into training examples.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bindu.server.storage.schema import tasks_table, task_feedback_table
from bindu.utils.logging import get_logger

from .config import MAX_INTERACTIONS_QUERY_LIMIT

logger = get_logger("bindu.dspy.postgres")


@dataclass
class RawTaskData:
    """Raw task data fetched from the database.
    
    This represents the raw data before interaction extraction.
    """

    id: UUID
    history: list[dict[str, Any]]
    created_at: Any
    feedback_data: dict[str, Any] | None = None


async def fetch_raw_task_data(
    limit: int = MAX_INTERACTIONS_QUERY_LIMIT,
) -> list[RawTaskData]:
    """Fetch raw task data with feedback from PostgreSQL.

    This function reads task data from the database along with associated
    feedback using a LEFT JOIN. It returns raw data that needs to be
    processed by the extraction and filtering pipeline.

    Args:
        limit: Maximum number of tasks to fetch

    Returns:
        List of RawTaskData objects containing task history and feedback

    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL environment variable is not set
        ConnectionError: If unable to connect to database
    """
    database_url = os.getenv("STORAGE__POSTGRES_URL")
    if not database_url:
        raise RuntimeError("STORAGE__POSTGRES_URL environment variable not set")

    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not database_url.startswith("postgresql+asyncpg://"):
        database_url = f"postgresql+asyncpg://{database_url}"

    logger.info(f"Fetching up to {limit} tasks from database")

    try:
        # Create async engine
        engine = create_async_engine(
            database_url,
            pool_size=5,
            max_overflow=0,
            pool_pre_ping=True,
            echo=False,
        )

        # Create session factory
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        raw_tasks: list[RawTaskData] = []

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

            for row in rows:
                raw_tasks.append(
                    RawTaskData(
                        id=row.id,
                        history=row.history or [],
                        created_at=row.created_at,
                        feedback_data=row.feedback_data,
                    )
                )

        await engine.dispose()
        logger.info(f"Fetched {len(raw_tasks)} raw tasks from database")
        return raw_tasks

    except Exception as e:
        logger.error(f"Failed to fetch raw task data from database: {e}")
        raise ConnectionError(f"Failed to fetch raw task data: {e}") from e