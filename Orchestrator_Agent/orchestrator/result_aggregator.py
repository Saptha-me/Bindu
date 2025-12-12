import logging
from typing import List, Dict, Any
from models.task import Task, SubTask
from models.results import SubTaskResult, AggregatedResult
from utils.logger import get_logger


class ResultAggregator:
    """Aggregates results from multiple agent executions"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def aggregate(self, task: Task, results: Dict[str, Dict[str, Any]]) -> AggregatedResult:
        """
        Aggregate results from all subtasks
        
        Args:
            task: Original task
            results: Dictionary of subtask results
            
        Returns:
            AggregatedResult with combined metrics
        """
        self.logger.info(f"Aggregating results for task {task.id}")
        
        aggregated = AggregatedResult(
            task_id=task.id,
            task_title=task.title,
            status="completed",
        )
        
        # Process each subtask result
        for subtask in task.subtasks:
            result = results.get(subtask.id)
            if result:
                subtask_result = SubTaskResult(
                    subtask_id=subtask.id,
                    agent_did=subtask.assigned_agent_did or "unknown",
                    status=result.get("status", "unknown"),
                    data=result.get("data", {}),
                    quality_score=result.get("data", {}).get("quality_score", 0.5),
                    execution_time=result.get("data", {}).get("execution_time", 0),
                    cost=subtask.max_budget,
                )
                aggregated.add_subtask_result(subtask_result)
        
        # Calculate metrics
        aggregated.calculate_metrics()
        
        # Generate summary
        aggregated.summary = self._generate_summary(task, aggregated)
        
        self.logger.info(f"Aggregation complete: {len(aggregated.subtask_results)} results")
        
        return aggregated
    
    def _generate_summary(self, task: Task, aggregated: AggregatedResult) -> str:
        """Generate a summary of results"""
        num_subtasks = len(aggregated.subtask_results)
        avg_quality = aggregated.quality_score
        completion = aggregated.completion_percentage
        
        summary = f"Task '{task.title}' execution complete. "
        summary += f"Processed {num_subtasks} subtasks with {completion:.0f}% completion. "
        summary += f"Average quality score: {avg_quality:.2%}. "
        summary += f"Total cost: ${aggregated.total_cost:.2f}. "
        summary += f"Execution time: {aggregated.total_execution_time}s."
        
        return summary
    
    def validate_results(self, results: Dict[str, Dict[str, Any]]) -> tuple:
        """
        Validate aggregated results
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not results:
            return False, "No results to aggregate"
        
        failed_tasks = [r for r in results.values() if r.get("status") == "failed"]
        if failed_tasks:
            return False, f"{len(failed_tasks)} tasks failed"
        
        return True, "Results valid"
    
    def merge_results(self, result1: AggregatedResult, result2: AggregatedResult) -> AggregatedResult:
        """Merge two aggregated results"""
        merged = AggregatedResult(
            task_id=result1.task_id,
            task_title=result1.task_title,
            status="completed",
        )
        
        # Combine subtask results
        for subtask_result in result1.subtask_results:
            merged.add_subtask_result(subtask_result)
        
        for subtask_result in result2.subtask_results:
            merged.add_subtask_result(subtask_result)
        
        merged.calculate_metrics()
        return merged
