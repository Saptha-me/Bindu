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
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bindu.server.storage.schema import tasks_table, task_feedback_table
from bindu.utils.logging import get_logger

from .config import MAX_INTERACTIONS_QUERY_LIMIT
from .models import Interaction

logger = get_logger("bindu.dspy.postgres")


async def fetch_interactions(
    limit: int = MAX_INTERACTIONS_QUERY_LIMIT,
) -> list[Interaction]:
    """Fetch interaction data from PostgreSQL for training.

    This function reads task data from the database and converts it into
    Interaction objects suitable for DSPy training. It joins tasks with
    their feedback to create complete training examples.

    Args:
        limit: Maximum number of interactions to fetch

    Returns:
        List of Interaction objects containing task data

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

    logger.info(f"Fetching up to {limit} interactions from database")

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

        interactions: list[Interaction] = []

        async with session_factory() as session:
            # Simple query: fetch tasks with their metadata
            # We assume tasks.history contains the interaction text
            # and tasks.metadata contains additional context
            stmt = (
                select(
                    tasks_table.c.id,
                    tasks_table.c.history,
                    tasks_table.c.metadata,
                )
                .order_by(tasks_table.c.created_at.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.fetchall()

            for row in rows:
                # Extract text from history (last message)
                history = row.history or []
                if not history:
                    continue

                # Get the last message content as the interaction text
                last_message = history[-1] if history else {}
                text = last_message.get("content", "")
                if not text:
                    continue

                interactions.append(
                    Interaction(
                        id=row.id,
                        text=text,
                        metadata=row.metadata or {},
                    )
                )

        await engine.dispose()
        logger.info(f"Fetched {len(interactions)} interactions from database")
        return interactions

    except Exception as e:
        logger.error(f"Failed to fetch interactions from database: {e}")
        raise ConnectionError(f"Failed to fetch interactions: {e}") from e