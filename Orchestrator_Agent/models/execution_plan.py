import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum


class ExecutionStepStatus(Enum):
    """Execution step status"""
    PENDING = "pending"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    """Represents a single execution step"""
    subtask_id: str
    agent_did: str
    description: str
    step_number: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ExecutionStepStatus = ExecutionStepStatus.PENDING
    dependencies: List[str] = field(default_factory=list)  # IDs of steps this depends on
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time: int = 0  # seconds
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def start(self) -> None:
        """Mark step as started"""
        self.status = ExecutionStepStatus.EXECUTING
        self.started_at = datetime.utcnow().isoformat()

    def complete(self, result: Dict[str, Any]) -> None:
        """Mark step as completed"""
        self.status = ExecutionStepStatus.COMPLETED
        self.completed_at = datetime.utcnow().isoformat()
        self.result = result
        
        # Calculate execution time
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            self.execution_time = int((end - start).total_seconds())

    def fail(self, error: str) -> None:
        """Mark step as failed"""
        self.completed_at = datetime.utcnow().isoformat()
        self.error = error
        
        if self.retry_count < self.max_retries:
            self.status = ExecutionStepStatus.PENDING
            self.retry_count += 1
        else:
            self.status = ExecutionStepStatus.FAILED

    def mark_ready(self) -> None:
        """Mark step as ready to execute"""
        self.status = ExecutionStepStatus.READY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "subtask_id": self.subtask_id,
            "agent_did": self.agent_did,
            "description": self.description,
            "step_number": self.step_number,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time": self.execution_time,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class ExecutionContext:
    """Execution context for a task"""
    task_id: str
    orchestrator_did: str
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None
    total_execution_time: int = 0
    
    # State tracking
    variables: Dict[str, Any] = field(default_factory=dict)
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    
    # Logging
    events: List[Dict[str, Any]] = field(default_factory=list)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable"""
        self.variables[key] = value
        self.add_event("variable_set", {"key": key, "value": str(value)})

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable"""
        return self.variables.get(key, default)

    def add_error(self, error: str) -> None:
        """Add an error to context"""
        self.errors.append(error)
        self.add_event("error", {"message": error})

    def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Add an event to context"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "data": data,
        }
        self.events.append(event)

    def complete(self) -> None:
        """Mark execution as completed"""
        self.completed_at = datetime.utcnow().isoformat()
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            self.total_execution_time = int((end - start).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "orchestrator_did": self.orchestrator_did,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_execution_time": self.total_execution_time,
            "variables": self.variables,
            "errors_count": len(self.errors),
            "events_count": len(self.events),
        }


@dataclass
class ExecutionPlan:
    """Represents a complete execution plan with dependencies"""
    task_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[ExecutionStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Validation state
    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)

    def add_step(self, step: ExecutionStep) -> None:
        """Add a step to the plan"""
        self.steps.append(step)

    def get_step(self, step_id: str) -> Optional[ExecutionStep]:
        """Get a step by ID"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_ready_steps(self) -> List[ExecutionStep]:
        """Get all steps ready to execute"""
        return [step for step in self.steps if step.status == ExecutionStepStatus.READY]

    def get_pending_steps(self) -> List[ExecutionStep]:
        """Get all pending steps"""
        return [step for step in self.steps if step.status == ExecutionStepStatus.PENDING]

    def get_completed_steps(self) -> List[ExecutionStep]:
        """Get all completed steps"""
        return [step for step in self.steps if step.status == ExecutionStepStatus.COMPLETED]

    def get_failed_steps(self) -> List[ExecutionStep]:
        """Get all failed steps"""
        return [step for step in self.steps if step.status == ExecutionStepStatus.FAILED]

    def validate(self) -> tuple[bool, List[str]]:
        """Validate the execution plan"""
        errors = []
        
        # Check for circular dependencies
        if self._has_circular_dependency():
            errors.append("Execution plan has circular dependencies")
        
        # Check if all dependencies exist
        step_ids = {step.id for step in self.steps}
        for step in self.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"Step {step.id} depends on non-existent step {dep_id}")
        
        self.is_valid = len(errors) == 0
        self.validation_errors = errors
        return self.is_valid, errors

    def _has_circular_dependency(self) -> bool:
        """Check if there are circular dependencies"""
        def has_cycle(step_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(step_id)
            rec_stack.add(step_id)
            
            step = self.get_step(step_id)
            if step:
                for dep_id in step.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id, visited, rec_stack):
                            return True
                    elif dep_id in rec_stack:
                        return True
            
            rec_stack.remove(step_id)
            return False
        
        visited: Set[str] = set()
        for step in self.steps:
            if step.id not in visited:
                if has_cycle(step.id, visited, set()):
                    return True
        
        return False

    def update_dependent_steps(self, completed_step_id: str) -> None:
        """Update steps that depend on a completed step"""
        for step in self.steps:
            if completed_step_id in step.dependencies:
                # Check if all dependencies are completed
                all_deps_completed = all(
                    self.get_step(dep_id).status == ExecutionStepStatus.COMPLETED
                    for dep_id in step.dependencies
                    if self.get_step(dep_id)
                )
                
                if all_deps_completed:
                    step.mark_ready()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "is_valid": self.is_valid,
            "steps_count": len(self.steps),
            "completed_steps": len(self.get_completed_steps()),
            "failed_steps": len(self.get_failed_steps()),
            "pending_steps": len(self.get_pending_steps()),
            "ready_steps": len(self.get_ready_steps()),
            "validation_errors": self.validation_errors,
        }
