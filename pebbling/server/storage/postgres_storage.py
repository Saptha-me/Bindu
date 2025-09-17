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
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, delete, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from typing_extensions import TypeVar

from pebbling.common.protocol.types import Artifact, Message, Task, TaskState, TaskStatus, Context

from .base import Storage

ContextT = TypeVar('ContextT', default=Any)

# SQLAlchemy Base
Base = declarative_base()


class TaskModel(Base):
    """SQLAlchemy model for tasks table."""
    __tablename__ = 'tasks'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    context_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    context_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class TaskFeedbackModel(Base):
    """SQLAlchemy model for task feedback table."""
    __tablename__ = 'task_feedback'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    feedback_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    # Index for performance
    __table_args__ = (
        Index('idx_task_feedback_task_id', 'task_id'),
        Index('idx_task_feedback_created_at', 'created_at'),
    )


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
        self.engine = create_async_engine(
            self.connection_string,
            pool_size=self.pool_size,
            max_overflow=20,
            echo=False  # Set to True for SQL debugging
        )
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        
    async def initialize(self):
        """Create tables if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def load_task(self, task_id: UUID, history_length: int = 50) -> Task | None:
        """Retrieve a task by ID using ORM."""
        print(f"PostgreSQL load_task: looking for task_id={task_id}")
        
        async with self.session_factory() as session:
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()
            
            if not task_model:
                print(f"PostgreSQL load_task: task {task_id} not found")
                return None
            
            print(f"PostgreSQL load_task: found task {task_id}, state={task_model.state}")
            
            # Get history with limit
            history = task_model.history or []
            if history_length > 0:
                history = history[-history_length:]
            
            task_status = TaskStatus(state=task_model.state, timestamp=task_model.timestamp.isoformat())
            task = Task(
                task_id=task_model.id,
                context_id=task_model.context_id,
                kind=task_model.kind,
                status=task_status,
                history=history,
                artifacts=task_model.artifacts or []
            )
            
            return task

    async def submit_task(self, context_id: UUID, message: Message) -> Task:
        """Submit a task using ORM."""
        # Use existing task ID from message or generate new one
        task_id = message.get('task_id')
        
        print(f"PostgreSQL submit_task: task_id={task_id}, context_id={context_id}")
        
        # Create a copy of message with string UUIDs for JSON serialization
        message_for_storage = message.copy()
        message_for_storage['task_id'] = str(task_id)
        message_for_storage['context_id'] = str(context_id)
        
        if 'message_id' in message_for_storage and not isinstance(message_for_storage['message_id'], str):
            message_for_storage['message_id'] = str(message_for_storage['message_id'])

        task_status = TaskStatus(state='submitted', timestamp=datetime.now().isoformat())
        
        async with self.session_factory() as session:
            try:
                task_model = TaskModel(
                    id=task_id,
                    context_id=context_id,
                    kind='task',
                    state='submitted',
                    timestamp=datetime.now(),
                    history=[message_for_storage],
                    artifacts=[]
                )
                
                session.add(task_model)
                await session.commit()
                print(f"PostgreSQL task submitted successfully: {task_id}")
            except Exception as e:
                print(f"PostgreSQL task submission failed: {e}")
                await session.rollback()
                raise

        # Ensure original message has proper UUIDs for protocol compliance
        message['task_id'] = task_id
        message['context_id'] = context_id
        
        task = Task(
            task_id=task_id,
            context_id=context_id,
            kind='task',
            status=task_status,
            history=[message]
        )
        
        return task

    async def update_task(
        self,
        task_id: UUID,
        state: TaskState,
        new_artifacts: list[Artifact] | None = None,
        new_messages: list[Message] | None = None,
    ) -> Task:
        """Update the state of a task using ORM."""
        async with self.session_factory() as session:
            # Get current task
            stmt = select(TaskModel).where(TaskModel.id == task_id)
            result = await session.execute(stmt)
            task_model = result.scalar_one_or_none()
            
            if not task_model:
                raise ValueError(f"Task {task_id} not found")

            # Update task status
            task_model.state = state
            task_model.timestamp = datetime.now()
            
            if new_artifacts:
                if not task_model.artifacts:
                    task_model.artifacts = []
                task_model.artifacts.extend(new_artifacts)

            if new_messages:
                if not task_model.history:
                    task_model.history = []
                # Add IDs to messages for consistency
                for message in new_messages:
                    # Create storage copy with string UUIDs for JSON serialization
                    message_for_storage = message.copy()
                    message_for_storage['task_id'] = str(task_id)
                    message_for_storage['context_id'] = str(task_model.context_id)
                    task_model.history.append(message_for_storage)
                    
                    # Update original message with UUID objects for protocol compliance
                    message['task_id'] = task_id
                    message['context_id'] = task_model.context_id

            await session.commit()

        # Return updated task
        task_status = TaskStatus(state=state, timestamp=datetime.now().isoformat())
        task = Task(
            task_id=task_id,
            context_id=task_model.context_id,
            kind=task_model.kind,
            status=task_status,
            history=task_model.history,
            artifacts=task_model.artifacts
        )
        
        return task

    async def load_context(self, context_id: UUID) -> Context | None:
        """Retrieve the stored context given the `context_id`."""
        async with self.session_factory() as session:
            stmt = select(ContextModel).where(ContextModel.id == context_id)
            result = await session.execute(stmt)
            context_model = result.scalar_one_or_none()
            
            if not context_model:
                return None
                
            # Return context in the same format as memory storage
            context_data = context_model.context_data or {}
            
            # Debug: Print what we're loading from PostgreSQL
            print(f"PostgreSQL context_data: {context_data}")
            message_history = context_data.get('message_history', [])
            print(f"PostgreSQL message_history: {message_history}")
            
            return {
                'context_id': context_model.id,
                'kind': 'context',
                'created_at': context_model.created_at.isoformat() if hasattr(context_model.created_at, 'isoformat') else str(context_model.created_at),
                'updated_at': context_model.updated_at.isoformat() if hasattr(context_model.updated_at, 'isoformat') else str(context_model.updated_at),
                'status': context_data.get('status', 'active'),
                'message_history': message_history
            }

    async def append_to_contexts(self, context_id: UUID, messages: list[Message]) -> None:
        """Efficiently append new messages to context history without rebuilding entire context."""
        if not messages:
            return
            
        print(f"PostgreSQL append_to_contexts called with {len(messages)} messages")
        for msg in messages:
            print(f"  Message: role={msg.get('role')}, text={msg.get('parts', [{}])[0].get('text', 'N/A')[:50]}...")
            
        existing_context = await self.load_context(context_id)
        
        if existing_context is None:
            # Create new context with message history - store in context_data field
            context_data = {
                'status': 'active',
                'message_history': messages.copy()
            }
            new_context = {
                'context_id': context_id,
                'kind': 'context',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'context_data': context_data
            }
            print(f"Creating new context with {len(messages)} messages")
            await self.update_context(context_id, new_context)
        else:
            # Append to existing message history
            if 'message_history' not in existing_context:
                existing_context['message_history'] = []
            
            print(f"Before append: {len(existing_context['message_history'])} messages")
            existing_context['message_history'].extend(messages)
            print(f"After append: {len(existing_context['message_history'])} messages")
            existing_context['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Update the context_data field for PostgreSQL storage
            context_data = {
                'status': existing_context.get('status', 'active'),
                'message_history': existing_context['message_history']
            }
            updated_context = {
                'context_id': context_id,
                'kind': 'context',
                'created_at': existing_context['created_at'],
                'updated_at': existing_context['updated_at'],
                'context_data': context_data
            }
            print(f"Updating context with {len(context_data['message_history'])} total messages")
            await self.update_context(context_id, updated_context)

    async def update_context(self, context_id: UUID, context: Context) -> None:
        """Update the context using ORM."""
        async with self.session_factory() as session:
            try:
                # Try to get existing context
                stmt = select(ContextModel).where(ContextModel.id == context_id)
                result = await session.execute(stmt)
                context_model = result.scalar_one_or_none()
                
                # Convert UUIDs to strings for JSON serialization
                json_serializable_context = self._convert_uuids_to_strings(context)
                
                if context_model:
                    # Update existing
                    context_model.context_data = json_serializable_context
                    context_model.updated_at = datetime.now(timezone.utc)
                else:
                    # Create new
                    context_model = ContextModel()
                    context_model.id = context_id
                    context_model.context_data = json_serializable_context
                    context_model.created_at = datetime.now(timezone.utc)
                    context_model.updated_at = datetime.now(timezone.utc)
                    session.add(context_model)
                
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _convert_uuids_to_strings(self, data: Any) -> Any:
        """Recursively convert UUID objects to strings for JSON serialization."""
        import uuid
        if isinstance(data, (UUID, uuid.UUID)):
            return str(data)
        elif isinstance(data, dict):
            return {self._convert_uuids_to_strings(key): self._convert_uuids_to_strings(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_uuids_to_strings(item) for item in data]
        else:
            return data

    async def get_tasks_by_context(self, context_id: UUID, limit: int = 100) -> list[Task]:
        """Get all tasks for a specific context using ORM."""
        async with self.session_factory() as session:
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
                    task_id=task_model.id,
                    context_id=task_model.context_id,
                    kind=task_model.kind,
                    status=task_status,
                    history=task_model.history or [],
                    artifacts=task_model.artifacts or []
                )
                tasks.append(task)
            
            return tasks

    async def list_tasks(self, length: int | None = None) -> list[Task]:
        """List all tasks in storage using ORM."""
        async with self.session_factory() as session:
            stmt = select(TaskModel).order_by(TaskModel.created_at.desc())
            if length:
                stmt = stmt.limit(length)
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            tasks = []
            for task_model in task_models:
                task_status = TaskStatus(state=task_model.state, timestamp=task_model.timestamp.isoformat())
                task = Task(
                    task_id=task_model.id,
                    context_id=task_model.context_id,
                    kind=task_model.kind,
                    status=task_status,
                    history=task_model.history or [],
                    artifacts=task_model.artifacts or []
                )
                tasks.append(task)
            
            return tasks

    async def list_tasks_by_context(self, context_id: UUID, length: int | None = None) -> list[Task]:
        """List all tasks in storage using ORM."""
        async with self.session_factory() as session:
            stmt = select(TaskModel).where(TaskModel.context_id == context_id).order_by(TaskModel.created_at.desc())
            if length:
                stmt = stmt.limit(length)
            
            result = await session.execute(stmt)
            task_models = result.scalars().all()
            
            tasks = []
            for task_model in task_models:
                task_status = TaskStatus(state=task_model.state, timestamp=task_model.timestamp.isoformat())
                task = Task(
                    task_id=task_model.id,
                    context_id=task_model.context_id,
                    kind=task_model.kind,
                    status=task_status,
                    history=task_model.history or [],
                    artifacts=task_model.artifacts or []
                )
                tasks.append(task)
            
            return tasks

    async def list_contexts(self, length: int | None = None) -> list[Context]:
        """List all contexts in storage using ORM."""
        async with self.session_factory() as session:
            stmt = select(ContextModel).order_by(ContextModel.created_at.desc())
            if length:
                stmt = stmt.limit(length)
            
            result = await session.execute(stmt)
            context_models = result.scalars().all()
            
            contexts = []
            for context_model in context_models:
                context = Context(
                    context_id=context_model.id,
                    context_data=context_model.context_data,
                    created_at=context_model.created_at,
                    updated_at=context_model.updated_at
                )
                contexts.append(context)
            
            return contexts

    async def clear_all(self) -> None:
        """Clear all tasks and contexts from storage using ORM."""
        async with self.session_factory() as session:
            # Delete all tasks
            await session.execute(delete(TaskModel))
            # Delete all contexts
            await session.execute(delete(ContextModel))
            # Delete all task feedback
            await session.execute(delete(TaskFeedbackModel))
            await session.commit()

    async def store_task_feedback(self, task_id: uuid.UUID, feedback_data: dict[str, Any]) -> None:
        """Store feedback for a task."""
        async with self.session_factory() as session:
            feedback_model = TaskFeedbackModel(
                task_id=task_id,
                feedback_data=feedback_data
            )
            session.add(feedback_model)
            await session.commit()

    async def get_task_feedback(self, task_id: uuid.UUID) -> list[dict[str, Any]] | None:
        """Retrieve feedback for a task."""
        async with self.session_factory() as session:
            stmt = (
                select(TaskFeedbackModel)
                .where(TaskFeedbackModel.task_id == task_id)
                .order_by(TaskFeedbackModel.created_at.asc())
            )
            result = await session.execute(stmt)
            feedback_models = result.scalars().all()
            
            if not feedback_models:
                return None
                
            return [feedback_model.feedback_data for feedback_model in feedback_models]