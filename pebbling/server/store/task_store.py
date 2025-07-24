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
Task store for managing task lifecycle across protocols.

Handles task creation, updates, and retrieval for both JSON-RPC and HTTP protocols.
"""

from typing import List, Optional
from uuid import UUID

from pebbling.protocol.types import Task, TaskState, TaskStatus
from .memory_store import MemoryStore


class TaskStore(MemoryStore[Task]):
    """Store for managing tasks across both JSON-RPC and HTTP protocols."""
    
    async def create_task(self, task: Task) -> None:
        """Create a new task."""
        await self.set(task.id, task)
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return await self.get(task_id)
    
    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """Update task status."""
        task = await self.get(task_id)
        if task is None:
            return False
        
        task.status = status
        await self.set(task_id, task)
        return True
    
    async def get_tasks_by_context(self, context_id: UUID) -> List[Task]:
        """Get all tasks for a specific context (session)."""
        all_tasks = []
        keys = await self.list_keys()
        
        for key in keys:
            task = await self.get(key)
            if task and task.contextId == context_id:
                all_tasks.append(task)
        
        return all_tasks
    
    async def get_tasks_by_state(self, state: TaskState) -> List[Task]:
        """Get all tasks with a specific state."""
        all_tasks = []
        keys = await self.list_keys()
        
        for key in keys:
            task = await self.get(key)
            if task and task.status.state == state:
                all_tasks.append(task)
        
        return all_tasks
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task by setting its state to canceled."""
        task = await self.get(task_id)
        if task is None:
            return False
        
        # Only cancel if task is not in a terminal state
        if task.status.state in [TaskState.completed, TaskState.failed, TaskState.canceled]:
            return False
        
        task.status.state = TaskState.canceled
        await self.set(task_id, task)
        return True
