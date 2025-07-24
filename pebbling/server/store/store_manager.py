# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Store manager for coordinating all stores.

Provides a unified interface to all store types and handles
cross-store operations and consistency.
"""

from typing import Optional
from uuid import UUID, uuid4

from pebbling.protocol.types import Task, TaskState, TaskStatus, Message, AgentManifest
from .task_store import TaskStore
from .session_store import SessionStore, AgentContext, Session
from .agent_store import AgentStore


class StoreManager:
    """Unified manager for all store types."""
    
    def __init__(self):
        self.tasks = TaskStore()
        self.sessions = SessionStore()
        self.agents = AgentStore()
    
    # Task operations
    async def create_task(self, session_id: str, agent_id: str, input_data: dict, 
                         protocol: str = "unknown") -> Task:
        """Create a task and update session context."""
        task_id = str(uuid4())
        
        # Create the task
        task = Task(
            id=task_id,
            contextId=UUID(session_id),
            status=TaskStatus(state=TaskState.submitted),
            metadata={"protocol": protocol, "agent_id": agent_id, "input": input_data}
        )
        
        await self.tasks.create_task(task)
        
        # Update session context
        await self.sessions.add_task_to_context(session_id, agent_id, task_id)
        
        return task
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return await self.tasks.get_task(task_id)
    
    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update task status."""
        return await self.tasks.update_task_status(task_id, status)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        return await self.tasks.cancel_task(task_id)
    
    # Session operations
    async def get_or_create_session(self, session_id: str) -> Session:
        """Get or create a session."""
        return await self.sessions.get_or_create_session(session_id)
    
    async def get_agent_context(self, session_id: str, agent_id: str) -> Optional[AgentContext]:
        """Get agent context within a session."""
        return await self.sessions.get_agent_context(session_id, agent_id)
    
    async def get_or_create_agent_context(self, session_id: str, agent_id: str) -> AgentContext:
        """Get or create agent context within a session."""
        return await self.sessions.get_or_create_agent_context(session_id, agent_id)
    
    async def add_message_to_context(self, session_id: str, agent_id: str, message: Message) -> bool:
        """Add a message to agent's conversation history."""
        return await self.sessions.add_message_to_context(session_id, agent_id, message)
    
    # Agent operations
    async def register_agent(self, manifest: AgentManifest) -> None:
        """Register a new agent."""
        await self.agents.register_agent(manifest)
    
    async def get_agent(self, agent_id: str) -> Optional[AgentManifest]:
        """Get an agent by ID."""
        return await self.agents.get_agent(agent_id)
    
    async def get_agent_by_name(self, name: str) -> Optional[AgentManifest]:
        """Get an agent by name."""
        return await self.agents.get_agent_by_name(name)
    
    async def list_agents(self) -> list[AgentManifest]:
        """List all registered agents."""
        return await self.agents.list_agents()
    
    # Cross-store operations
    async def get_session_tasks(self, session_id: str) -> list[Task]:
        """Get all tasks for a session."""
        return await self.tasks.get_tasks_by_context(UUID(session_id))
    
    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session and its associated data."""
        # Get all tasks for the session
        tasks = await self.get_session_tasks(session_id)
        
        # Cancel any running tasks
        for task in tasks:
            if task.status.state in [TaskState.submitted, TaskState.working]:
                await self.cancel_task(task.id)
        
        # Remove the session
        return await self.sessions.delete(session_id)
    
    async def get_agent_task_history(self, session_id: str, agent_id: str) -> list[Task]:
        """Get task history for a specific agent in a session."""
        context = await self.get_agent_context(session_id, agent_id)
        if not context:
            return []
        
        tasks = []
        for task_id in context.task_history:
            task = await self.get_task(task_id)
            if task:
                tasks.append(task)
        
        return tasks
    
    # Health and stats
    async def get_stats(self) -> dict:
        """Get store statistics."""
        return {
            "tasks": await self.tasks.size(),
            "sessions": await self.sessions.size(),
            "agents": await self.agents.size()
        }
    
    async def clear_all(self) -> None:
        """Clear all stores (for testing)."""
        await self.tasks.clear()
        await self.sessions.clear()
        await self.agents.clear()
