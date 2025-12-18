"""SQLAlchemy table definitions using imperative mapping.

This module defines the database schema using SQLAlchemy's imperative (classical) mapping
approach. Instead of creating separate ORM model classes, we map directly to the protocol
TypedDicts defined in bindu.common.protocol.types.

This approach:
- Eliminates duplication between protocol types and database models
- Maintains single source of truth in protocol definitions
- Provides SQLAlchemy query capabilities while using protocol types
- Simplifies maintenance by avoiding schema drift

The tables are defined using SQLAlchemy Core's Table objects, which can be used
with both ORM queries and the protocol TypedDicts.
"""

from __future__ import annotations as _annotations


from sqlalchemy import (
    TIMESTAMP,
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

# Create metadata instance for table definitions
metadata = MetaData()

# -----------------------------------------------------------------------------
# Tasks Table
# -----------------------------------------------------------------------------

tasks_table = Table(
    "tasks",
    metadata,
    # Primary key
    Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
    # Foreign keys
    Column(
        "context_id",
        PG_UUID(as_uuid=True),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    # Task metadata
    Column("kind", String(50), nullable=False, default="task"),
    Column("state", String(50), nullable=False),
    Column("state_timestamp", TIMESTAMP(timezone=True), nullable=False),
    # JSONB columns for A2A protocol data
    Column("history", JSONB, nullable=False, server_default="[]"),
    Column("artifacts", JSONB, nullable=True, server_default="[]"),
    Column("metadata", JSONB, nullable=True, server_default="{}"),
    # Timestamps
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    # Indexes
    Index("idx_tasks_context_id", "context_id"),
    Index("idx_tasks_state", "state"),
    Index("idx_tasks_created_at", "created_at"),
    Index("idx_tasks_updated_at", "updated_at"),
    Index("idx_tasks_history_gin", "history", postgresql_using="gin"),
    Index("idx_tasks_metadata_gin", "metadata", postgresql_using="gin"),
    Index("idx_tasks_artifacts_gin", "artifacts", postgresql_using="gin"),
    # Table comment
    comment="A2A protocol tasks with JSONB history and artifacts",
)

# -----------------------------------------------------------------------------
# Contexts Table
# -----------------------------------------------------------------------------

contexts_table = Table(
    "contexts",
    metadata,
    # Primary key
    Column("id", PG_UUID(as_uuid=True), primary_key=True, nullable=False),
    # JSONB columns
    Column("context_data", JSONB, nullable=False, server_default="{}"),
    Column("message_history", JSONB, nullable=True, server_default="[]"),
    # Timestamps
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    # Indexes
    Index("idx_contexts_created_at", "created_at"),
    Index("idx_contexts_updated_at", "updated_at"),
    Index("idx_contexts_data_gin", "context_data", postgresql_using="gin"),
    Index("idx_contexts_history_gin", "message_history", postgresql_using="gin"),
    # Table comment
    comment="Conversation contexts with message history",
)

# -----------------------------------------------------------------------------
# Task Feedback Table
# -----------------------------------------------------------------------------

task_feedback_table = Table(
    "task_feedback",
    metadata,
    # Primary key
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    # Foreign key
    Column(
        "task_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    ),
    # JSONB column
    Column("feedback_data", JSONB, nullable=False),
    # Timestamp
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    # Indexes
    Index("idx_task_feedback_task_id", "task_id"),
    Index("idx_task_feedback_created_at", "created_at"),
    # Table comment
    comment="User feedback for tasks",
)

# -----------------------------------------------------------------------------
# Webhook Configs Table (for long-running task notifications)
# -----------------------------------------------------------------------------

webhook_configs_table = Table(
    "webhook_configs",
    metadata,
    # Primary key is task_id (one config per task)
    Column(
        "task_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    # Webhook configuration stored as JSONB
    Column("config", JSONB, nullable=False),
    # Timestamps
    Column(
        "created_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Column(
        "updated_at",
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    ),
    # Indexes
    Index("idx_webhook_configs_created_at", "created_at"),
    # Table comment
    comment="Webhook configurations for long-running task notifications",
)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def get_table(table_name: str) -> Table:
    """Get a table by name.

    Args:
        table_name: Name of the table

    Returns:
        SQLAlchemy Table object

    Raises:
        KeyError: If table not found
    """
    return metadata.tables[table_name]


def create_all_tables(engine):
    """Create all tables in the database.

    Args:
        engine: SQLAlchemy engine

    Note:
        This is typically handled by Alembic migrations in production.
        Use this only for testing or initial setup.
    """
    metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all tables from the database.

    Args:
        engine: SQLAlchemy engine

    Warning:
        This is a destructive operation. Use with caution!
    """
    metadata.drop_all(engine)
