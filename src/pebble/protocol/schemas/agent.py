"""
Agent schemas for communication protocol.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from ...constants import AgentType


class AgentCapability(str, Enum):
    """Enumeration of agent capabilities."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    TASK_PLANNING = "task_planning"
    TOOL_USAGE = "tool_usage"
    MEMORY = "memory"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    MULTI_AGENT_COOPERATION = "multi_agent_cooperation"


class AgentInfo(BaseModel):
    """Schema for agent information."""
    agent_id: str
    name: str
    agent_type: AgentType
    capabilities: List[AgentCapability] = []
    supported_protocols: List[str] = []
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentRegistration(BaseModel):
    """Schema for agent registration with the protocol server."""
    agent_info: AgentInfo
    endpoint_url: Optional[str] = None  # Only needed for remote agents
    api_key: Optional[str] = None  # For authentication if required
