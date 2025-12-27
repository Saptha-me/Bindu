from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class SubTaskResult:
    """Result from a single subtask execution"""
    subtask_id: str
    agent_did: str
    status: str  # "completed", "failed", "timeout"
    data: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.95
    execution_time: int = 0  # seconds
    cost: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subtask_id": self.subtask_id,
            "agent_did": self.agent_did,
            "status": self.status,
            "data": self.data,
            "quality_score": self.quality_score,
            "execution_time": self.execution_time,
            "cost": self.cost,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class AggregatedResult:
    """Final aggregated result for a task"""
    task_id: str
    task_title: str
    status: str  # "completed", "partial", "failed"
    subtask_results: List[SubTaskResult] = field(default_factory=list)
    summary: str = ""
    quality_score: float = 0.0
    total_execution_time: int = 0  # seconds
    total_cost: float = 0.0
    completion_percentage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_subtask_result(self, result: SubTaskResult) -> None:
        """Add a subtask result"""
        self.subtask_results.append(result)
        self.total_cost += result.cost

    def calculate_metrics(self) -> None:
        """Calculate overall metrics"""
        if not self.subtask_results:
            return
        
        # Calculate quality score
        quality_scores = [r.quality_score for r in self.subtask_results if r.quality_score > 0]
        self.quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Calculate execution time
        self.total_execution_time = sum(r.execution_time for r in self.subtask_results)
        
        # Calculate completion percentage
        completed = len([r for r in self.subtask_results if r.status == "completed"])
        self.completion_percentage = (completed / len(self.subtask_results)) * 100 if self.subtask_results else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_title": self.task_title,
            "status": self.status,
            "subtask_results": [r.to_dict() for r in self.subtask_results],
            "summary": self.summary,
            "quality_score": self.quality_score,
            "total_execution_time": self.total_execution_time,
            "total_cost": self.total_cost,
            "completion_percentage": self.completion_percentage,
            "metadata": self.metadata,
            "completed_at": self.completed_at,
        }