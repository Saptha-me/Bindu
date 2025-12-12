import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class AgentStatus(Enum):
    """Agent operational status"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


@dataclass
class AgentCapability:
    """Represents a capability that an agent can perform"""
    name: str
    description: str
    cost_per_call: float
    success_rate: float  # 0.0 to 1.0
    avg_execution_time: int = 60  # seconds
    max_concurrent_calls: int = 10
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "cost_per_call": self.cost_per_call,
            "success_rate": self.success_rate,
            "avg_execution_time": self.avg_execution_time,
            "max_concurrent_calls": self.max_concurrent_calls,
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class AgentProfile:
    """Represents an agent's profile and discovery metadata"""
    did: str  # Decentralized Identifier
    name: str
    description: str
    owner: str
    endpoint_url: str
    
    # Status and availability
    status: AgentStatus = AgentStatus.AVAILABLE
    last_heartbeat: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Agent metadata
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Capabilities
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # Reputation and performance metrics
    reputation_score: float = 0.95  # 0.0 to 1.0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    average_quality_score: float = 0.95
    response_time_ms: int = 500
    
    # Pricing and availability
    hourly_rate: float = 10.0
    currency: str = "USD"
    max_tasks_per_day: int = 100
    current_task_count: int = 0
    
    # Authentication
    public_key: str = ""
    
    # Tags and metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_capability(self, capability: AgentCapability) -> None:
        """Add a capability to the agent"""
        self.capabilities.append(capability)
        self.updated_at = datetime.utcnow().isoformat()

    def remove_capability(self, capability_name: str) -> bool:
        """Remove a capability from the agent"""
        for i, cap in enumerate(self.capabilities):
            if cap.name == capability_name:
                self.capabilities.pop(i)
                self.updated_at = datetime.utcnow().isoformat()
                return True
        return False

    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """Get a specific capability"""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability"""
        return self.get_capability(capability_name) is not None

    def has_all_capabilities(self, required_capabilities: List[str]) -> bool:
        """Check if agent has all required capabilities"""
        return all(self.has_capability(cap) for cap in required_capabilities)

    def is_available(self) -> bool:
        """Check if agent is available"""
        return self.status == AgentStatus.AVAILABLE

    def is_overloaded(self) -> bool:
        """Check if agent is overloaded with tasks"""
        return self.current_task_count >= self.max_tasks_per_day

    def can_accept_task(self) -> bool:
        """Check if agent can accept a new task"""
        return self.is_available() and not self.is_overloaded()

    def update_heartbeat(self) -> None:
        """Update last heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow().isoformat()

    def update_reputation(self, quality_score: float) -> None:
        """Update reputation based on task quality"""
        # Weighted average: 70% old reputation, 30% new score
        self.reputation_score = (self.reputation_score * 0.7) + (quality_score * 0.3)
        self.reputation_score = max(0.0, min(1.0, self.reputation_score))
        self.average_quality_score = quality_score

    def increment_task_completed(self) -> None:
        """Increment completed task count"""
        self.total_tasks_completed += 1
        self.updated_at = datetime.utcnow().isoformat()

    def increment_task_failed(self) -> None:
        """Increment failed task count"""
        self.total_tasks_failed += 1
        self.updated_at = datetime.utcnow().isoformat()

    def get_success_rate(self) -> float:
        """Get overall success rate"""
        total = self.total_tasks_completed + self.total_tasks_failed
        if total == 0:
            return 0.95
        return self.total_tasks_completed / total

    def increment_current_task(self) -> None:
        """Increment current task count"""
        self.current_task_count += 1
        if self.current_task_count >= self.max_tasks_per_day:
            self.status = AgentStatus.BUSY
        self.updated_at = datetime.utcnow().isoformat()

    def decrement_current_task(self) -> None:
        """Decrement current task count"""
        self.current_task_count = max(0, self.current_task_count - 1)
        if self.current_task_count < self.max_tasks_per_day:
            self.status = AgentStatus.AVAILABLE
        self.updated_at = datetime.utcnow().isoformat()

    def get_capability_cost(self, capability_name: str) -> Optional[float]:
        """Get cost for a specific capability"""
        cap = self.get_capability(capability_name)
        if cap:
            return cap.cost_per_call
        return None

    def estimate_cost(self, capabilities: List[str]) -> float:
        """Estimate total cost for multiple capabilities"""
        total_cost = 0.0
        for cap_name in capabilities:
            cost = self.get_capability_cost(cap_name)
            if cost:
                total_cost += cost
        return total_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "did": self.did,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "endpoint_url": self.endpoint_url,
            "status": self.status.value,
            "reputation_score": self.reputation_score,
            "success_rate": self.get_success_rate(),
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_failed": self.total_tasks_failed,
            "average_quality_score": self.average_quality_score,
            "response_time_ms": self.response_time_ms,
            "hourly_rate": self.hourly_rate,
            "currency": self.currency,
            "current_task_count": self.current_task_count,
            "max_tasks_per_day": self.max_tasks_per_day,
            "capabilities": [cap.to_dict() for cap in self.capabilities],
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_heartbeat": self.last_heartbeat,
        }