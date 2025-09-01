# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
# POSTGRESQL STORAGE IMPLEMENTATION WITH ORM:
# 
# This is the PostgreSQL implementation of the Storage interface for the Pebbling framework.
# It provides persistent, scalable storage for tasks and contexts with ACID compliance using SQLAlchemy ORM.
#
# BURGER STORE ANALOGY:
# 
# Think of this as the restaurant's computerized order management system:
# 
# 1. DIGITAL ORDER SYSTEM (PostgreSQLStorage):
#    - Orders stored in secure database with backup systems
#    - Survives power outages and system restarts
#    - Handles thousands of concurrent orders
#    - Complete audit trail of all order history
# 
# 2. ORM MODELS:
#    - TaskModel: All orders with status, timestamps, and details
#    - ContextModel: Customer profiles and conversation history
#    - Relationships and constraints handled by ORM
#    - Type-safe operations with automatic validation
# 
# 3. ENTERPRISE FEATURES:
#    - ACID transactions: Orders never get lost or corrupted
#    - Concurrent access: Multiple kitchen stations can work simultaneously
#    - Backup and recovery: Complete order history preserved
#    - Scalability: Handles restaurant chains with multiple locations
#
# WHEN TO USE POSTGRESQL STORAGE:
# - Production environments requiring data persistence
# - Multi-server deployments with shared state
# - High-volume agent interactions
# - Compliance requirements for audit trails
# - Long-running workflows that span server restarts
# - Team collaboration with shared task history
#
# ORM BENEFITS:
# - Type-safe database operations
# - Automatic schema migrations
# - Relationship management
# - Query optimization
# - Connection pooling
# - Transaction management
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations as _annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from typing_extensions import TypeVar

from sqlalchemy import Column, String, DateTime, Text, Index, func, select, delete
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

from pebbling.protocol.types import Artifact, Message, Task, TaskState, TaskStatus
from pebbling.storage.base import Storage

ContextT = TypeVar('ContextT', default=Any)

# SQLAlchemy Base
Base = declarative_base()


class TaskModel(Base):
    """SQLAlchemy model for tasks table."""
    __tablename__ = 'tasks'

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default='task')
    state: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    artifacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Indexes for performance
    __table_args__ = (
        Index('idx_tasks_context_id', 'context_id'),
        Index('idx_tasks_state', 'state'),
        Index('idx_tasks_created_at', 'created_at'),
    )


class ContextModel(Base):
    """SQLAlchemy model for contexts table."""
    __tablename__ = 'contexts'

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    context_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class PostgreSQLStorage(Storage[ContextT]):
    """A storage implementation using PostgreSQL with SQLAlchemy ORM for persistent task and context storage.
    
    This implementation provides ACID-compliant storage with support for:
    - Type-safe ORM operations with SQLAlchemy
    - Concurrent access from multiple workers
    - Persistent storage across server restarts
    - Efficient querying with proper indexing
    - Automatic schema migrations
    """

    def __init__(self, connection_string: str, pool_size: int = 10):
        """Initialize PostgreSQL storage with SQLAlchemy.
        
        Args:
            connection_string: PostgreSQL connection string (e.g., "postgresql+asyncpg://user:pass@host:port/db")
            pool_size: Maximum number of connections in the pool
        """
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.engine = None
        self.session_factory = None

    async def initialize(self) -> None:
        """Initialize the database engine and create tables if needed."""
        self.engine = create_async_engine(
            self.connection_string,
            pool_size=self.pool_size,
            max_overflow=20,
            echo=False  # Set to True for SQL debugging
        )
        
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()

    def _get_session(self) -> AsyncSession:
        """Get a new database session."""
        if not self.session_factory:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return self.session_factory()

    async def load_task(self, task_id: str, history_length: int | None = None) -> Task | None:
        """Load a task using ORM.

        Args:
            task_id: The id of the task to load.
            history_length: The number of messages to return in the history.

        Returns:
            The task or None if not found.
        """
        async with self._get_session() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()
            
            if not task_model:
                return None

            history = task_model.history
            if history_length and len(history) > history_length:
                history = history[-history_length:]

            task_status = TaskStatus(state=task_model.state, timestamp=task_model.timestamp.isoformat())
            task = Task(
                id=task_model.id,
                context_id=task_model.context_id,
                kind=task_model.kind,
                status=task_status,
                history=history,
                artifacts=task_model.artifacts or []
            )
            
            return task

    async def submit_task(self, context_id: str, message: Message) -> Task:
        """Submit a task using ORM."""
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Add IDs to the message for A2A protocol
        message['task_id'] = task_id
        message['context_id'] = context_id

        task_status = TaskStatus(state='submitted', timestamp=datetime.now().isoformat())
        
        async with self._get_session() as session:
            task_model = TaskModel(
                id=task_id,
                context_id=context_id,
                kind='task',
                state='submitted',
                timestamp=datetime.now(),
                history=[message],
                artifacts=[]
            )
            
            session.add(task_model)
            await session.commit()

        task = Task(
            id=task_id,
            context_id=context_id,
            kind='task',
            status=task_status,
            history=[message]
        )
        
        return task

    async def update_task(
        self,
        task_id: str,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task using ORM."""
        async with self._get_session() as session:
            # Start a transaction
            async with session.begin():
                # Get current task
                stmt = select(TaskModel).where(TaskModel.id == task_id)
                result = await session.execute(stmt)
                task_model = result.scalar_one_or_none()
                
                if not task_model:
                    raise ValueError(f"Task {task_id} not found")

                # Update task data
                task_model.state = state
                task_model.timestamp = datetime.now()
                
                if new_messages:
                    # Add IDs to messages for consistency
                    for message in new_messages:
                        message['task_id'] = task_id
                        message['context_id'] = task_model.context_id
                    task_model.history.extend(new_messages)
                
                if new_artifacts:
                    task_model.artifacts.extend(new_artifacts)

                await session.commit()

        # Return updated task
        task_status = TaskStatus(state=state, timestamp=datetime.now().isoformat())
        task = Task(
            id=task_id,
            context_id=task_model.context_id,
            kind=task_model.kind,
            status=task_status,
            history=task_model.history,
            artifacts=task_model.artifacts
        )
        
        return task

    async def load_context(self, context_id: str) -> ContextT | None:
        """Retrieve the stored context using ORM."""
        async with self._get_session() as session:
            stmt = select(ContextModel).where(ContextModel.id == context_id)
            result = await session.execute(stmt)
            context_model = result.scalar_one_or_none()
            
            if not context_model:
                return None
                
            return context_model.context_data

    async def update_context(self, context_id: str, context: ContextT) -> None:
        """Update the context using ORM."""
        async with self._get_session() as session:
            # Try to get existing context
            stmt = select(ContextModel).where(ContextModel.id == context_id)
            result = await session.execute(stmt)
            context_model = result.scalar_one_or_none()
            
            if context_model:
                # Update existing
                context_model.context_data = context
                context_model.updated_at = datetime.now()
            else:
                # Create new
                context_model = ContextModel(
                    id=context_id,
                    context_data=context
                )
                session.add(context_model)
            
            await session.commit()

    async def get_tasks_by_context(self, context_id: str, limit: int = 100) -> list[Task]:
        """Get all tasks for a specific context using ORM."""
        async with self._get_session() as session:
            stmt = (
                select(TaskModel)
                .where(TaskModel.context_id == context_id)
                .order_by(TaskModel.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            tasks = []
            for task_model in task_models:
                task_status = TaskStatus(state=task_model.state, timestamp=task_model.timestamp.isoformat())
                task = Task(
                    id=task_model.id,
                    context_id=task_model.context_id,
                    kind=task_model.kind,
                    status=task_status,
                    history=task_model.history or [],
                    artifacts=task_model.artifacts or []
                )
                tasks.append(task)
            
            return tasks

    async def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up tasks older than specified days using ORM."""
        async with self._get_session() as session:
            cutoff_date = datetime.now() - datetime.timedelta(days=days)
            stmt = delete(TaskModel).where(TaskModel.created_at < cutoff_date)
            result = await session.execute(stmt)
            await session.commit()
            
            return result.rowcount