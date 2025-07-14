"""Protocol handler setup for different agent frameworks."""

from typing import Any
from loguru import logger

def setup_protocol_handler(
    agent: Any,
    agent_id: str
) -> Any:
    """Set up the appropriate protocol handler based on the agent framework.
    
    Args:
        agent: The agent to be served
        agent_id: Unique identifier for the agent
        
    Returns:
        Protocol handler for the agent
    """
    # For now we'll create a simple handler class in this file
    # In a future iteration, this could be moved to a dedicated module
    
    class GenericProtocolHandler:
        """Generic protocol handler for agents."""
        
        def __init__(self, agent, agent_id):
            self.agent = agent
            self.agent_id = agent_id
            logger.debug(f"Initialized GenericProtocolHandler for agent {agent_id}")
            
        async def handle_request(self, method, params):
            """Handle protocol request."""
            # Default implementation delegates to the agent if possible
            if hasattr(self.agent, method):
                handler = getattr(self.agent, method)
                if callable(handler):
                    return await handler(**params)
            
            raise NotImplementedError(f"Method {method} not implemented")
    
    # Detect the agent framework and use the appropriate adapter
    if hasattr(agent, "__module__") and "agno" in getattr(agent, "__module__", ""):
        logger.debug(f"Setting up handler for Agno agent {agent_id}")
        return GenericProtocolHandler(agent, agent_id)
    else:
        # Generic handler for other frameworks
        logger.debug(f"Using default handler for agent {agent_id}")
        return GenericProtocolHandler(agent, agent_id)
