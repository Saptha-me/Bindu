"""
Adapter modules for different agent frameworks.
"""

from typing import Any, Dict, List, Optional, Union, Type
from uuid import UUID

from pebble.adapters.base import BaseAdapter, BaseCognitiveAdapter
from pebble.core.protocol import AgentProtocol

def get_adapter_for_agent(
    agent: Any,
    agent_id: Optional[UUID] = None,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AgentProtocol:
    """Get the appropriate adapter for an agent.
    
    Args:
        agent: The agent to adapt
        agent_id: Unique identifier for the agent
        name: Name of the agent
        metadata: Additional metadata for the agent
        
    Returns:
        AgentProtocol: The agent protocol adapter
        
    Raises:
        ValueError: If the agent type is not supported
    """
    # Import agent frameworks here to avoid dependency issues
    try:
        from agno.agent import Agent as AgnoAgent
        from pebble.adapters.agno_adapter import AgnoAdapter
        has_agno = True
    except ImportError:
        has_agno = False
    
    try:
        from crewai.agent import Agent as CrewAgent
        from pebble.adapters.crewai_adapter import CrewAdapter
        has_crew = True
    except ImportError:
        has_crew = False
        
    try:
        from langchain.agents import Agent as LangchainAgent
        from pebble.adapters.langchain_adapter import LangchainAdapter
        has_langchain = True
    except ImportError:
        has_langchain = False
        
    try:
        from llama_index.agent import Agent as LlamaIndexAgent
        from pebble.adapters.llamaindex_adapter import LlamaIndexAdapter
        has_llamaindex = True
    except ImportError:
        has_llamaindex = False
    
    # Check agent type and create appropriate adapter
    if has_agno and isinstance(agent, AgnoAgent):
        return AgnoAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    if has_crew and isinstance(agent, CrewAgent):
        return CrewAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
        
    if has_langchain and isinstance(agent, LangchainAgent):
        return LangchainAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
        
    if has_llamaindex and isinstance(agent, LlamaIndexAgent):
        return LlamaIndexAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    # If no adapter found, look at the class hierarchy
    if has_agno and inspect.isclass(type(agent)) and issubclass(type(agent), AgnoAgent):
        return AgnoAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    if has_crew and inspect.isclass(type(agent)) and issubclass(type(agent), CrewAgent):
        return CrewAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
        
    if has_langchain and inspect.isclass(type(agent)) and issubclass(type(agent), LangchainAgent):
        return LangchainAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
        
    if has_llamaindex and inspect.isclass(type(agent)) and issubclass(type(agent), LlamaIndexAgent):
        return LlamaIndexAdapter(agent, agent_id=agent_id, name=name, metadata=metadata)
    
    # If still no match, raise an error
    raise ValueError(
        f"Unsupported agent type: {type(agent).__name__}. "
        "Currently supported frameworks: Agno, CrewAI, Langchain, LlamaIndex"
    )

# Export the adapters and helper functions
from pebble.adapters.agno_adapter import AgnoAdapter

# Import other adapters conditionally to avoid import errors
try:
    from pebble.adapters.crewai_adapter import CrewAdapter
    __all__ = ["BaseAdapter", "BaseCognitiveAdapter", "AgnoAdapter", "CrewAdapter", "get_adapter_for_agent"]
except ImportError:
    __all__ = ["BaseAdapter", "BaseCognitiveAdapter", "AgnoAdapter", "get_adapter_for_agent"]

try:
    from pebble.adapters.langchain_adapter import LangchainAdapter
    __all__.append("LangchainAdapter")
except ImportError:
    pass

try:
    from pebble.adapters.llamaindex_adapter import LlamaIndexAdapter
    __all__.append("LlamaIndexAdapter")
except ImportError:
    pass