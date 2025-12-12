import logging
from typing import List, Dict, Any, Tuple
from models.task import Task, SubTask, TaskStatus, SubTaskStatus, TaskPriority
from utils.logger import get_logger


class TaskDecomposer:
    """Decomposes complex tasks into manageable subtasks"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def decompose(self, task: Task) -> List[SubTask]:

        self.logger.info(f"Decomposing task {task.id}: {task.title}")
        
        subtasks = []
        
        # Parse objective to identify subtask needs
        capabilities_needed = task.required_capabilities
        
        # Distribute budget across capabilities
        budget_per_capability = task.max_budget / len(capabilities_needed) if capabilities_needed else task.max_budget
        
        # Create subtasks for each capability
        for i, capability in enumerate(capabilities_needed):
            subtask = SubTask(
                description=f"Execute {capability} capability",
                required_capabilities=[capability],
                estimated_duration=60,  # Default 1 minute
                max_budget=budget_per_capability,
            )
            task.add_subtask(subtask)
            subtasks.append(subtask)
            self.logger.debug(f"Created subtask {subtask.id} for capability {capability}")
        
        # Parse objective for additional structure
        subtasks = self._parse_objective(task, subtasks)
        
        # Mark task as decomposed
        task.mark_decomposed()
        self.logger.info(f"Task decomposed into {len(subtasks)} subtasks")
        
        return subtasks
    
    def _parse_objective(self, task: Task, initial_subtasks: List[SubTask]) -> List[SubTask]:
        """Parse objective text for more specific subtask requirements"""
        # Advanced parsing could be done here
        # For now, return initial subtasks as-is
        return initial_subtasks
    
    def validate_decomposition(self, task: Task) -> Tuple[bool, str]:

        if not task.subtasks:
            return False, "Task has no subtasks"
        
        # Check total budget
        total_subtask_budget = sum(st.max_budget for st in task.subtasks)
        if total_subtask_budget > task.max_budget * 1.1:  # Allow 10% buffer
            return False, f"Subtask budgets exceed task budget: {total_subtask_budget} > {task.max_budget}"
        
        # Check capabilities coverage
        subtask_capabilities = set()
        for subtask in task.subtasks:
            subtask_capabilities.update(subtask.required_capabilities)
        
        required_capabilities = set(task.required_capabilities)
        if not required_capabilities.issubset(subtask_capabilities):
            missing = required_capabilities - subtask_capabilities
            return False, f"Missing required capabilities: {missing}"
        
        return True, "Task decomposition is valid"
    
    def replan_failed_subtasks(self, task: Task, failed_subtask_ids: List[str]) -> List[SubTask]:

        self.logger.info(f"Replanning {len(failed_subtask_ids)} failed subtasks")
        
        new_subtasks = []
        for failed_id in failed_subtask_ids:
            # Find original failed subtask
            original = next((st for st in task.subtasks if st.id == failed_id), None)
            if not original:
                continue
            
            # Create retry subtask with same specification
            retry_subtask = SubTask(
                description=f"[RETRY] {original.description}",
                required_capabilities=original.required_capabilities,
                estimated_duration=original.estimated_duration,
                max_budget=original.max_budget,
            )
            
            task.add_subtask(retry_subtask)
            new_subtasks.append(retry_subtask)
            self.logger.info(f"Created retry subtask {retry_subtask.id}")
        
        return new_subtasks
    
    def estimate_total_duration(self, task: Task) -> int:
        """Estimate total execution duration"""
        # Simple sum of all subtask durations
        # In production, would account for parallelization
        return sum(st.estimated_duration for st in task.subtasks)
    
    def estimate_total_cost(self, task: Task) -> float:
        """Estimate total cost"""
        return sum(st.max_budget for st in task.subtasks)