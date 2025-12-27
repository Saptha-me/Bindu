"""PostgreSQL storage implementation using SQLAlchemy with imperative mapping.

This implementation provides a persistent storage backend suitable for:
- Production deployments
- Multi-pod/distributed systems
- Long-term data retention
- Enterprise environments

Hybrid Agent Pattern Support:
- Stores tasks with flexible state transitions (working → input-required → completed)
- Maintains conversation context across multiple tasks
- Supports incremental message history updates
- Enables task refinements through context-based task lookup
- Survives pod restarts and redeployments

Features:
- SQLAlchemy imperative mapping with protocol TypedDicts
- No duplicate ORM models - uses protocol types directly
- Connection pooling for performance
- Automatic retry logic for transient failures
- JSONB for efficient storage of A2A protocol objects
- Transaction support for data consistency
- Indexed queries for fast lookups
"""

from __future__ import annotations as _annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update, cast
from sqlalchemy.dialects.postgresql import insert, JSONB, JSON
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing_extensions import TypeVar

from bindu.common.protocol.types import (
    Artifact,
    Message,
    PushNotificationConfig,
    Task,
    TaskState,
    TaskStatus,
)
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .base import Storage
from .schema import (
    contexts_table,
    task_feedback_table,
    tasks_table,
    webhook_configs_table,
)

logger = get_logger("bindu.server.storage.postgres_storage")

ContextT = TypeVar("ContextT", default=Any)


def _serialize_for_jsonb(obj: Any) -> Any:
    """Recursively convert UUID objects to strings for JSONB serialization.

    Args:
        obj: Object to serialize (dict, list, or primitive)

    Returns:
        Object with all UUIDs converted to strings
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: _serialize_for_jsonb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_for_jsonb(item) for item in obj]
    else:
        return obj


class PostgresStorage(Storage[ContextT]):
    """PostgreSQL storage implementation using SQLAlchemy imperative mapping.

    Storage Structure:
    - tasks_table: All tasks with JSONB history and artifacts
    - contexts_table: Context metadata and message history
    - task_feedback_table: Optional feedback storage

    Uses protocol TypedDicts directly - no ORM model classes needed.

    Connection Management:
    - Uses SQLAlchemy async engine with connection pool
    - Automatic reconnection on connection loss
    - Configurable pool size and timeouts
    """

    def __init__(
        self,
        database_url: str | None = None,
        pool_min: int | None = None,
        pool_max: int | None = None,
        timeout: int | None = None,
        command_timeout: int | None = None,
    ):
        """Initialize PostgreSQL storage with SQLAlchemy.

        Args:
            database_url: PostgreSQL connection URL (defaults to settings)
            pool_min: Minimum pool size (defaults to settings)
            pool_max: Maximum pool size (defaults to settings)
            timeout: Connection timeout in seconds (defaults to settings)
            command_timeout: Command timeout in seconds (defaults to settings)
        """
        # Convert postgresql:// to postgresql+asyncpg://
        db_url = database_url or app_settings.storage.postgres_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif not db_url.startswith("postgresql+asyncpg://"):
            db_url = f"postgresql+asyncpg://{db_url}"

        self.database_url = db_url
        self.pool_min = pool_min or app_settings.storage.postgres_pool_min
        self.pool_max = pool_max or app_settings.storage.postgres_pool_max
        self.timeout = timeout or app_settings.storage.postgres_timeout
        self.command_timeout = (
            command_timeout or app_settings.storage.postgres_command_timeout
        )

        self._engine = None
        self._session_factory = None

    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in database URL for safe logging.

        Args:
            url: Database URL (e.g., postgresql+asyncpg://user:password@host:port/db)  # pragma: allowlist secret

        Returns:
            URL with password masked (e.g., postgresql+asyncpg://user:***@host:port/db)  # pragma: allowlist secret
        """
        try:
            # Handle URLs like postgresql+asyncpg://user:password@host:port/db  # pragma: allowlist secret
            if "://" in url and "@" in url:
                scheme, rest = url.split("://", 1)
                if "@" in rest:
                    auth, host_part = rest.rsplit("@", 1)
                    if ":" in auth:
                        user, _ = auth.split(":", 1)
                        return f"{scheme}://{user}:***@{host_part}"
            return url
        except Exception:
            # If parsing fails, return as-is (better than crashing)
            return url

    async def connect(self) -> None:
        """Initialize SQLAlchemy engine and session factory.

        Raises:
            ConnectionError: If unable to connect to database
        """
        try:
            # Mask password in URL for logging
            masked_url = self._mask_password(self.database_url)
            logger.info("Connecting to PostgreSQL database with SQLAlchemy...")

            # Create async engine
            self._engine = create_async_engine(
                self.database_url,
                pool_size=self.pool_max,
                max_overflow=0,
                pool_timeout=self.timeout,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,  # Set to True for SQL query logging
            )

            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Test connection
            async with self._engine.begin() as conn:
                await conn.execute(select(1))

            logger.info(
                f"PostgreSQL storage connected to {masked_url} (pool_size={self.pool_max})"
            )

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}") from e

    async def disconnect(self) -> None:
        """Close SQLAlchemy engine and connection pool."""
        if self._engine:
            await self._engine.dispose()
            logger.info("PostgreSQL connection pool closed")
            self._engine = None
            self._session_factory = None

    def _ensure_connected(self) -> None:
        """Ensure engine is initialized.

        Raises:
            RuntimeError: If engine is not initialized
        """
        if self._engine is None or self._session_factory is None:
            raise RuntimeError(
                "PostgreSQL engine not initialized. Call connect() first."
            )

    async def _retry_on_connection_error(self, func, *args, **kwargs):
        """Retry function on connection errors using Tenacity.

        Args:
            func: Async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            Exception: If all retries fail
        """
        # Use Tenacity-based retry with storage configuration
        from bindu.utils.retry import execute_with_retry

        max_retries = app_settings.storage.postgres_max_retries
        retry_delay = app_settings.storage.postgres_retry_delay

        return await execute_with_retry(
            func,
            *args,
            max_attempts=max_retries,
            min_wait=retry_delay,
            max_wait=retry_delay * max_retries,
            **kwargs,
        )

    def _row_to_task(self, row) -> Task:
        """Convert database row to Task protocol type.

        Args:
            row: SQLAlchemy Row object

        Returns:
            Task TypedDict from protocol
        """
        return Task(
            id=row.id,
            context_id=row.context_id,
            kind=row.kind,
            status=TaskStatus(
                state=row.state, timestamp=row.state_timestamp.isoformat()
            ),
            history=row.history or [],
            artifacts=row.artifacts or [],
            metadata=row.metadata or {},
        )

    # -------------------------------------------------------------------------
    # Task Operations
    # -------------------------------------------------------------------------

    async def load_task(
        self, task_id: UUID, history_length: int | None = None
    ) -> Task | None:
        """Load a task from PostgreSQL using SQLAlchemy.

        Args:
            task_id: Unique identifier of the task
            history_length: Optional limit on message history length

        Returns:
            Task object if found, None otherwise

        Raises:
            TypeError: If task_id is not UUID
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._ensure_connected()

        async def _load():
            async with self._session_factory() as session:
                stmt = select(tasks_table).where(tasks_table.c.id == task_id)
                result = await session.execute(stmt)
                row = result.first()

                if row is None:
                    return None

                task = self._row_to_task(row)

                # Limit history if requested
                if history_length is not None and history_length > 0:
                    task["history"] = task["history"][-history_length:]

                return task

        return await self._retry_on_connection_error(_load)

    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Create a new task or continue an existing non-terminal task.

        Task-First Pattern (Bindu):
        - If task exists and is in non-terminal state: Append message and reset to 'submitted'
        - If task exists and is in terminal state: Raise error (immutable)
        - If task doesn't exist: Create new task

        Args:
            context_id: Context to associate the task with
            message: Initial message containing task request

        Returns:
            Task in 'submitted' state (new or continued)

        Raises:
            TypeError: If IDs are invalid types
            ValueError: If attempting to continue a terminal task
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        # Parse and normalize task ID
        task_id_raw = message.get("task_id")
        task_id: UUID

        if isinstance(task_id_raw, str):
            task_id = UUID(task_id_raw)
        elif isinstance(task_id_raw, UUID):
            task_id = task_id_raw
        else:
            raise TypeError(
                f"task_id must be UUID or str, got {type(task_id_raw).__name__}"
            )

        # Normalize message fields
        message["task_id"] = task_id
        message["context_id"] = context_id

        message_id_raw = message.get("message_id")
        if isinstance(message_id_raw, str):
            message["message_id"] = UUID(message_id_raw)
        elif message_id_raw is not None and not isinstance(message_id_raw, UUID):
            raise TypeError(
                f"message_id must be UUID or str, got {type(message_id_raw).__name__}"
            )

        # Normalize reference_task_ids
        ref_ids_key = "reference_task_ids"
        if ref_ids_key in message:
            ref_ids = message[ref_ids_key]
            if ref_ids is not None:
                normalized_refs = []
                for ref_id in ref_ids:
                    if isinstance(ref_id, str):
                        normalized_refs.append(UUID(ref_id))
                    elif isinstance(ref_id, UUID):
                        normalized_refs.append(ref_id)
                    else:
                        raise TypeError(
                            f"reference_task_id must be UUID or str, got {type(ref_id).__name__}"
                        )
                message["reference_task_ids"] = normalized_refs

        self._ensure_connected()

        async def _submit():
            async with self._session_factory() as session:
                async with session.begin():
                    # Check if task exists
                    stmt = select(tasks_table).where(tasks_table.c.id == task_id)
                    result = await session.execute(stmt)
                    existing = result.first()

                    if existing:
                        # Task exists - check if mutable
                        current_state = existing.state

                        if current_state in app_settings.agent.terminal_states:
                            raise ValueError(
                                f"Cannot continue task {task_id}: Task is in terminal state '{current_state}' and is immutable. "
                                f"Create a new task with referenceTaskIds to continue the conversation."
                            )

                        # Append message to history
                        logger.info(
                            f"Continuing existing task {task_id} from state '{current_state}'"
                        )

                        # Update using JSONB concatenation
                        # Serialize message to convert UUIDs to strings
                        serialized_message = _serialize_for_jsonb(message)
                        stmt = (
                            update(tasks_table)
                            .where(tasks_table.c.id == task_id)
                            .values(
                                history=func.jsonb_concat(
                                    tasks_table.c.history,
                                    cast([serialized_message], JSONB),
                                ),
                                state="submitted",
                                state_timestamp=datetime.now(timezone.utc),
                                updated_at=datetime.now(timezone.utc),
                            )
                            .returning(tasks_table)
                        )
                        result = await session.execute(stmt)
                        updated_row = result.first()

                        return self._row_to_task(updated_row)

                    # Ensure context exists BEFORE creating task (foreign key constraint)
                    stmt = insert(contexts_table).values(
                        id=context_id,
                        context_data={},
                        message_history=[],
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                    await session.execute(stmt)

                    # Create new task
                    # Serialize message to convert UUIDs to strings
                    serialized_message = _serialize_for_jsonb(message)
                    now = datetime.now(timezone.utc)
                    stmt = (
                        insert(tasks_table)
                        .values(
                            id=task_id,
                            context_id=context_id,
                            kind="task",
                            state="submitted",
                            state_timestamp=now,
                            history=[serialized_message],
                            artifacts=[],
                            metadata={},
                        )
                        .returning(tasks_table)
                    )
                    result = await session.execute(stmt)
                    new_row = result.first()

                    return self._row_to_task(new_row)

        return await self._retry_on_connection_error(_submit)

    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Update task state and append new content using SQLAlchemy.

        Args:
            task_id: Task to update
            state: New task state
            new_artifacts: Optional artifacts to append
            new_messages: Optional messages to append to history
            metadata: Optional metadata to update/merge

        Returns:
            Updated task object

        Raises:
            TypeError: If task_id is not UUID
            KeyError: If task not found
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._ensure_connected()

        async def _update():
            async with self._session_factory() as session:
                async with session.begin():
                    # Check if task exists
                    stmt = select(tasks_table).where(tasks_table.c.id == task_id)
                    result = await session.execute(stmt)
                    task_row = result.first()

                    if task_row is None:
                        raise KeyError(f"Task {task_id} not found")

                    # Build update values
                    now = datetime.now(timezone.utc)
                    update_values = {
                        "state": state,
                        "state_timestamp": now,
                        "updated_at": now,
                    }

                    # Update metadata (merge with existing)
                    if metadata:
                        serialized_metadata = _serialize_for_jsonb(metadata)
                        update_values["metadata"] = func.jsonb_concat(
                            tasks_table.c.metadata, cast(serialized_metadata, JSONB)
                        )

                    # Append artifacts
                    if new_artifacts:
                        serialized_artifacts = _serialize_for_jsonb(new_artifacts)
                        update_values["artifacts"] = func.jsonb_concat(
                            tasks_table.c.artifacts, cast(serialized_artifacts, JSONB)
                        )

                    # Append messages
                    if new_messages:
                        # Add task_id and context_id to messages
                        for message in new_messages:
                            if not isinstance(message, dict):
                                raise TypeError(
                                    f"Message must be dict, got {type(message).__name__}"
                                )
                            message["task_id"] = task_id
                            message["context_id"] = task_row.context_id

                        serialized_messages = _serialize_for_jsonb(new_messages)
                        update_values["history"] = func.jsonb_concat(
                            tasks_table.c.history, cast(serialized_messages, JSONB)
                        )

                    # Execute update
                    stmt = (
                        update(tasks_table)
                        .where(tasks_table.c.id == task_id)
                        .values(**update_values)
                        .returning(tasks_table)
                    )
                    result = await session.execute(stmt)
                    updated_row = result.first()

                    return self._row_to_task(updated_row)

        return await self._retry_on_connection_error(_update)

    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks using SQLAlchemy.

        Args:
            length: Optional limit on number of tasks to return

        Returns:
            List of tasks
        """
        self._ensure_connected()

        async def _list():
            async with self._session_factory() as session:
                stmt = select(tasks_table).order_by(tasks_table.c.created_at.desc())

                if length is not None:
                    stmt = stmt.limit(length)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [self._row_to_task(row) for row in rows]

        return await self._retry_on_connection_error(_list)

    async def list_tasks_by_context(
        self, context_id: UUID, length: int | None = None
    ) -> list[Task]:
        """List tasks belonging to a specific context.

        Args:
            context_id: Context to filter tasks by
            length: Optional limit on number of tasks to return

        Returns:
            List of tasks in the context

        Raises:
            TypeError: If context_id is not UUID
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        self._ensure_connected()

        async def _list():
            async with self._session_factory() as session:
                stmt = (
                    select(tasks_table)
                    .where(tasks_table.c.context_id == context_id)
                    .order_by(tasks_table.c.created_at.asc())
                )

                if length is not None:
                    stmt = stmt.limit(length)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [self._row_to_task(row) for row in rows]

        return await self._retry_on_connection_error(_list)

    # -------------------------------------------------------------------------
    # Context Operations
    # -------------------------------------------------------------------------

    async def load_context(self, context_id: UUID) -> dict[str, Any] | None:
        """Load context from storage using SQLAlchemy.

        Args:
            context_id: Unique identifier of the context

        Returns:
            Context data if found, None otherwise

        Raises:
            TypeError: If context_id is not UUID
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        self._ensure_connected()

        async def _load():
            async with self._session_factory() as session:
                stmt = select(contexts_table).where(contexts_table.c.id == context_id)
                result = await session.execute(stmt)
                row = result.first()

                return row.context_data if row else None

        return await self._retry_on_connection_error(_load)

    async def update_context(self, context_id: UUID, context: ContextT) -> None:
        """Store or update context using SQLAlchemy.

        Args:
            context_id: Context identifier
            context: Context data

        Raises:
            TypeError: If context_id is not UUID
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        self._ensure_connected()

        async def _update():
            async with self._session_factory() as session:
                async with session.begin():
                    # Upsert context
                    # Serialize context data to convert UUIDs to strings
                    serialized_context = _serialize_for_jsonb(
                        context if isinstance(context, dict) else {}
                    )
                    stmt = insert(contexts_table).values(
                        id=context_id,
                        context_data=serialized_context,
                        message_history=[],
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            "context_data": serialized_context,
                            "updated_at": datetime.now(timezone.utc),
                        },
                    )
                    await session.execute(stmt)

        await self._retry_on_connection_error(_update)

    async def append_to_contexts(
        self, context_id: UUID, messages: list[Message]
    ) -> None:
        """Append messages to context history using SQLAlchemy.

        Args:
            context_id: Context to update
            messages: Messages to append to history

        Raises:
            TypeError: If context_id is not UUID or messages is not a list
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        if not isinstance(messages, list):
            raise TypeError(f"messages must be list, got {type(messages).__name__}")

        self._ensure_connected()

        async def _append():
            async with self._session_factory() as session:
                async with session.begin():
                    # Ensure context exists
                    stmt = insert(contexts_table).values(
                        id=context_id,
                        context_data={},
                        message_history=[],
                    )
                    stmt = stmt.on_conflict_do_nothing(index_elements=["id"])
                    await session.execute(stmt)

                    # Append messages
                    # Serialize messages to convert UUIDs to strings
                    serialized_messages = _serialize_for_jsonb(messages)
                    stmt = (
                        update(contexts_table)
                        .where(contexts_table.c.id == context_id)
                        .values(
                            message_history=func.jsonb_concat(
                                contexts_table.c.message_history,
                                cast(serialized_messages, JSONB),
                            ),
                            updated_at=datetime.now(timezone.utc),
                        )
                    )
                    await session.execute(stmt)

        await self._retry_on_connection_error(_append)

    async def list_contexts(self, length: int | None = None) -> list[dict[str, Any]]:
        """List all contexts using SQLAlchemy.

        Args:
            length: Optional limit on number of contexts to return

        Returns:
            List of context objects with task counts
        """
        self._ensure_connected()

        async def _list():
            async with self._session_factory() as session:
                # Query contexts with task counts
                stmt = (
                    select(
                        contexts_table.c.id.label("context_id"),
                        func.count(tasks_table.c.id).label("task_count"),
                        func.coalesce(
                            func.json_agg(tasks_table.c.id).filter(
                                tasks_table.c.id.isnot(None)
                            ),
                            cast("[]", JSON),
                        ).label("task_ids"),
                    )
                    .outerjoin(
                        tasks_table, contexts_table.c.id == tasks_table.c.context_id
                    )
                    .group_by(contexts_table.c.id)
                    .order_by(contexts_table.c.created_at.desc())
                )

                if length is not None:
                    stmt = stmt.limit(length)

                result = await session.execute(stmt)
                rows = result.fetchall()

                return [
                    {
                        "context_id": row.context_id,
                        "task_count": row.task_count,
                        "task_ids": row.task_ids,
                    }
                    for row in rows
                ]

        return await self._retry_on_connection_error(_list)

    # -------------------------------------------------------------------------
    # Utility Operations
    # -------------------------------------------------------------------------

    async def clear_context(self, context_id: UUID) -> None:
        """Clear all tasks associated with a specific context.

        Args:
            context_id: The context ID to clear

        Raises:
            TypeError: If context_id is not UUID
            ValueError: If context does not exist

        Warning: This is a destructive operation.
        """
        if not isinstance(context_id, UUID):
            raise TypeError(f"context_id must be UUID, got {type(context_id).__name__}")

        self._ensure_connected()

        async def _clear():
            async with self._session_factory() as session:
                async with session.begin():
                    # Check if context exists
                    stmt = select(contexts_table).where(
                        contexts_table.c.id == context_id
                    )
                    result = await session.execute(stmt)
                    context = result.first()

                    if context is None:
                        raise ValueError(f"Context {context_id} not found")

                    # Delete tasks (cascade will delete feedback)
                    stmt = delete(tasks_table).where(
                        tasks_table.c.context_id == context_id
                    )
                    result = await session.execute(stmt)
                    deleted_count = result.rowcount

                    # Delete context
                    stmt = delete(contexts_table).where(
                        contexts_table.c.id == context_id
                    )
                    await session.execute(stmt)

                    logger.info(
                        f"Cleared context {context_id}: removed {deleted_count} tasks"
                    )

        await self._retry_on_connection_error(_clear)

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage.

        Warning: This is a destructive operation.
        """
        self._ensure_connected()

        async def _clear():
            async with self._session_factory() as session:
                async with session.begin():
                    await session.execute(delete(webhook_configs_table))
                    await session.execute(delete(task_feedback_table))
                    await session.execute(delete(tasks_table))
                    await session.execute(delete(contexts_table))
                    logger.info("Cleared all tasks, contexts, feedback, and webhook configs")

        await self._retry_on_connection_error(_clear)

    # -------------------------------------------------------------------------
    # Feedback Operations
    # -------------------------------------------------------------------------

    async def store_task_feedback(
        self, task_id: UUID, feedback_data: dict[str, Any]
    ) -> None:
        """Store user feedback for a task using SQLAlchemy.

        Args:
            task_id: Task to associate feedback with
            feedback_data: Feedback content

        Raises:
            TypeError: If task_id is not UUID or feedback_data is not dict
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        if not isinstance(feedback_data, dict):
            raise TypeError(
                f"feedback_data must be dict, got {type(feedback_data).__name__}"
            )

        self._ensure_connected()

        async def _store():
            async with self._session_factory() as session:
                async with session.begin():
                    # Serialize feedback data to convert UUIDs to strings
                    serialized_feedback = _serialize_for_jsonb(feedback_data)
                    stmt = insert(task_feedback_table).values(
                        task_id=task_id, feedback_data=serialized_feedback
                    )
                    await session.execute(stmt)

        await self._retry_on_connection_error(_store)

    async def get_task_feedback(self, task_id: UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task using SQLAlchemy.

        Args:
            task_id: Task to get feedback for

        Returns:
            List of feedback entries or None if no feedback exists

        Raises:
            TypeError: If task_id is not UUID
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._ensure_connected()

        async def _get():
            async with self._session_factory() as session:
                stmt = (
                    select(task_feedback_table)
                    .where(task_feedback_table.c.task_id == task_id)
                    .order_by(task_feedback_table.c.created_at.asc())
                )
                result = await session.execute(stmt)
                rows = result.fetchall()

                if not rows:
                    return None

                return [row.feedback_data for row in rows]

        return await self._retry_on_connection_error(_get)

    # -------------------------------------------------------------------------
    # Webhook Persistence Operations (for long-running tasks)
    # -------------------------------------------------------------------------

    async def save_webhook_config(
        self, task_id: UUID, config: PushNotificationConfig
    ) -> None:
        """Save a webhook configuration for a task using SQLAlchemy.

        Uses upsert to handle both insert and update scenarios.

        Args:
            task_id: Task to associate the webhook config with
            config: Push notification configuration to persist

        Raises:
            TypeError: If task_id is not UUID
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._ensure_connected()

        async def _save():
            async with self._session_factory() as session:
                async with session.begin():
                    # Serialize config to convert UUIDs to strings
                    serialized_config = _serialize_for_jsonb(config)
                    stmt = insert(webhook_configs_table).values(
                        task_id=task_id,
                        config=serialized_config,
                    )
                    # On conflict (task already has config), update it
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["task_id"],
                        set_={
                            "config": serialized_config,
                            "updated_at": datetime.now(timezone.utc),
                        },
                    )
                    await session.execute(stmt)
                    logger.debug(f"Saved webhook config for task {task_id}")

        await self._retry_on_connection_error(_save)

    async def load_webhook_config(
        self, task_id: UUID
    ) -> PushNotificationConfig | None:
        """Load a webhook configuration for a task using SQLAlchemy.

        Args:
            task_id: Task to load the webhook config for

        Returns:
            The webhook configuration if found, None otherwise

        Raises:
            TypeError: If task_id is not UUID
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._ensure_connected()

        async def _load():
            async with self._session_factory() as session:
                stmt = select(webhook_configs_table).where(
                    webhook_configs_table.c.task_id == task_id
                )
                result = await session.execute(stmt)
                row = result.first()

                if row is None:
                    return None

                return row.config

        return await self._retry_on_connection_error(_load)

    async def delete_webhook_config(self, task_id: UUID) -> None:
        """Delete a webhook configuration for a task using SQLAlchemy.

        Args:
            task_id: Task to delete the webhook config for

        Raises:
            TypeError: If task_id is not UUID

        Note: Does not raise if the config doesn't exist.
        """
        if not isinstance(task_id, UUID):
            raise TypeError(f"task_id must be UUID, got {type(task_id).__name__}")

        self._ensure_connected()

        async def _delete():
            async with self._session_factory() as session:
                async with session.begin():
                    stmt = delete(webhook_configs_table).where(
                        webhook_configs_table.c.task_id == task_id
                    )
                    result = await session.execute(stmt)
                    if result.rowcount > 0:
                        logger.debug(f"Deleted webhook config for task {task_id}")

        await self._retry_on_connection_error(_delete)

    async def load_all_webhook_configs(self) -> dict[UUID, PushNotificationConfig]:
        """Load all stored webhook configurations using SQLAlchemy.

        Used during initialization to restore webhook state after restart.

        Returns:
            Dictionary mapping task IDs to their webhook configurations
        """
        self._ensure_connected()

        async def _load_all():
            async with self._session_factory() as session:
                stmt = select(webhook_configs_table)
                result = await session.execute(stmt)
                rows = result.fetchall()

                return {row.task_id: row.config for row in rows}

        return await self._retry_on_connection_error(_load_all)
