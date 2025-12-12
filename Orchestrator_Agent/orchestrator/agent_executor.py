import logging
import time
from typing import Optional, Dict, Any
from models.task import SubTask
from utils.logger import get_logger


class AgentExecutor:
    """Executes tasks on agents via A2A protocol"""
    
    def __init__(self, orchestrator_did: str):
        self.logger = get_logger(__name__)
        self.orchestrator_did = orchestrator_did
        self.execution_results: Dict[str, Dict[str, Any]] = {}
    
    def execute_subtask(self, agent_did: str, subtask: SubTask) -> Dict[str, Any]:

        self.logger.info(f"Executing subtask {subtask.id} on agent {agent_did}")
        
        try:
            subtask.mark_assigned(agent_did)
            subtask.mark_executing()
            
            # In production, would send A2A message and wait for response
            # For now, simulate execution
            result = self._simulate_execution(subtask)
            
            # Store result
            self.execution_results[subtask.id] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing subtask {subtask.id}: {str(e)}")
            subtask.mark_failed(str(e))
            raise
    
    def _simulate_execution(self, subtask: SubTask) -> Dict[str, Any]:
        """Simulate task execution (mock)"""
        # In production, this would call actual agent API
        time.sleep(0.1)  # Simulate execution time
        
        result = {
            "subtask_id": subtask.id,
            "agent_did": subtask.assigned_agent_did,
            "status": "completed",
            "data": {
                "result": f"Execution result for {subtask.description}",
                "quality_score": 0.95,
                "execution_time": subtask.estimated_duration,
            },
            "timestamp": time.time()
        }
        
        subtask.mark_completed(result)
        self.logger.info(f"Subtask {subtask.id} completed successfully")
        
        return result
    
    def execute_parallel(self, tasks: list) -> Dict[str, Dict[str, Any]]:

        results = {}
        for agent_did, subtask in tasks:
            result = self.execute_subtask(agent_did, subtask)
            results[subtask.id] = result
        return results
    
    def get_execution_result(self, subtask_id: str) -> Optional[Dict[str, Any]]:
        """Get result of executed subtask"""
        return self.execution_results.get(subtask_id)
    
    def retry_subtask(self, agent_did: str, subtask: SubTask) -> Dict[str, Any]:
        """Retry execution of a subtask"""
        self.logger.info(f"Retrying subtask {subtask.id}")
        return self.execute_subtask(agent_did, subtask)
    
    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """Get all execution results"""
        return self.execution_results.copy()
    
    def get_result_count(self) -> int:
        """Get count of execution results"""
        return len(self.execution_results)
    
    def clear_results(self) -> None:
        """Clear all execution results"""
        self.execution_results.clear()
        self.logger.info("Cleared all execution results")