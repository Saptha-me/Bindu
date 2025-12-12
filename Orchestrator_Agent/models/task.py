import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


class TaskStatus(Enum):
    """Task lifecycle status"""
    PENDING = "pending"
    DECOMPOSED = "decomposed"
    NEGOTIATING = "negotiating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class SubTaskStatus(Enum):
    """SubTask status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class SubTask:
    """Represents a single subtask"""
    description: str
    required_capabilities: List[str]
    estimated_duration: int  # in seconds
    max_budget: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_task_id: str = ""
    status: SubTaskStatus = SubTaskStatus.PENDING
    assigned_agent_did: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    dependencies: List[str] = field(default_factory=list)  # IDs of subtasks this depends on
    retry_count: int = 0
    max_retries: int = 3
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def mark_assigned(self, agent_did: str) -> None:
        """Mark subtask as assigned to an agent"""
        self.assigned_agent_did = agent_did
        self.status = SubTaskStatus.ASSIGNED
        self.updated_at = datetime.utcnow().isoformat()

    def mark_executing(self) -> None:
        """Mark subtask as executing"""
        self.status = SubTaskStatus.EXECUTING
        self.updated_at = datetime.utcnow().isoformat()

    def mark_completed(self, result: Dict[str, Any]) -> None:
        """Mark subtask as completed"""
        self.status = SubTaskStatus.COMPLETED
        self.result = result
        self.updated_at = datetime.utcnow().isoformat()

    def mark_failed(self, error: str) -> None:
        """Mark subtask as failed"""
        self.error_message = error
        if self.retry_count < self.max_retries:
            self.status = SubTaskStatus.RETRYING
            self.retry_count += 1
        else:
            self.status = SubTaskStatus.FAILED
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "description": self.description,
            "required_capabilities": self.required_capabilities,
            "estimated_duration": self.estimated_duration,
            "max_budget": self.max_budget,
            "parent_task_id": self.parent_task_id,
            "status": self.status.value,
            "assigned_agent_did": self.assigned_agent_did,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result,
            "error_message": self.error_message,
        }


@dataclass
class Task:
    """Represents a complex task to be orchestrated"""
    title: str
    description: str
    objective: str
    required_capabilities: List[str]
    priority: TaskPriority = TaskPriority.MEDIUM
    max_budget: float = 100.0
    
    # Auto-generated fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    
    # Task composition
    subtasks: List[SubTask] = field(default_factory=list)
    
    # Metadata
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Budget tracking
    spent_budget: float = 0.0
    
    # Execution tracking
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    execution_time: int = 0  # in seconds

    def add_subtask(self, subtask: SubTask) -> None:
        """Add a subtask to this task"""
        subtask.parent_task_id = self.id
        self.subtasks.append(subtask)
        self.updated_at = datetime.utcnow().isoformat()

    def mark_decomposed(self) -> None:
        """Mark task as decomposed"""
        self.status = TaskStatus.DECOMPOSED
        self.updated_at = datetime.utcnow().isoformat()

    def mark_negotiating(self) -> None:
        """Mark task as negotiating"""
        self.status = TaskStatus.NEGOTIATING
        self.updated_at = datetime.utcnow().isoformat()

    def mark_executing(self) -> None:
        """Mark task as executing"""
        self.status = TaskStatus.EXECUTING
        self.start_time = datetime.utcnow().isoformat()
        self.updated_at = self.start_time

    def mark_completed(self) -> None:
        """Mark task as completed"""
        self.status = TaskStatus.COMPLETED
        self.end_time = datetime.utcnow().isoformat()
        self.completed_at = self.end_time
        
        # Calculate execution time
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.execution_time = int((end - start).total_seconds())
        
        self.updated_at = self.end_time

    def mark_failed(self) -> None:
        """Mark task as failed"""
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.utcnow().isoformat()

    def add_spent_budget(self, amount: float) -> None:
        """Add to spent budget"""
        self.spent_budget += amount
        self.updated_at = datetime.utcnow().isoformat()

    def remaining_budget(self) -> float:
        """Get remaining budget"""
        return self.max_budget - self.spent_budget

    def is_budget_exceeded(self) -> bool:
        """Check if budget is exceeded"""
        return self.spent_budget > self.max_budget

    def get_pending_subtasks(self) -> List[SubTask]:
        """Get all pending subtasks"""
        return [st for st in self.subtasks if st.status == SubTaskStatus.PENDING]

    def get_completed_subtasks(self) -> List[SubTask]:
        """Get all completed subtasks"""
        return [st for st in self.subtasks if st.status == SubTaskStatus.COMPLETED]

    def get_failed_subtasks(self) -> List[SubTask]:
        """Get all failed subtasks"""
        return [st for st in self.subtasks if st.status == SubTaskStatus.FAILED]

    def completion_percentage(self) -> float:
        """Get task completion percentage"""
        if not self.subtasks:
            return 0.0
        completed = len(self.get_completed_subtasks())
        return (completed / len(self.subtasks)) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "objective": self.objective,
            "required_capabilities": self.required_capabilities,
            "priority": self.priority.name,
            "max_budget": self.max_budget,
            "spent_budget": self.spent_budget,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "subtasks_count": len(self.subtasks),
            "completed_subtasks": len(self.get_completed_subtasks()),
            "failed_subtasks": len(self.get_failed_subtasks()),
            "completion_percentage": self.completion_percentage(),
            "owner": self.owner,
            "tags": self.tags,
            "metadata": self.metadata,
            "execution_time": self.execution_time,
        }