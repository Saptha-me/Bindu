# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

from typing import Dict, List, Optional

from pebbling.protocol.types import AgentCapabilities, AgentExtension, AgentManifest
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.agent.metadata.agent_capabilities")

def get_agent_capabilities(agent: AgentManifest):
    """
    Extract capabilities from agent for registration.
    
    This function checks if the agent already has capabilities defined in the proper format.
    If not, it tries to extract capability-related attributes from the agent object.
    
    Args:
        agent: The agent object
        
    Returns:
        AgentCapabilities: Object containing the agent's capabilities
    """
    logger.debug("Extracting agent capabilities")
    
    # If agent already has AgentCapabilities property
    if hasattr(agent, 'capabilities'):
        if callable(agent.capabilities):
            caps: AgentCapabilities = agent.capabilities()
            if isinstance(caps, AgentCapabilities):
                return caps
            elif isinstance(caps, dict):
                return AgentCapabilities(**caps)
        elif isinstance(agent.capabilities, AgentCapabilities):
            return agent.capabilities
    
    # Extract capabilities from agent attributes
    logger.debug("Extracting capabilities from agent attributes")
    streaming: Optional[bool] = getattr(agent, 'streaming', None)
    push_notifications: Optional[bool] = getattr(agent, 'push_notifications', None)
    state_transition_history: Optional[bool] = getattr(agent, 'state_transition_history', None)
    
    # Get extensions if available
    extensions: List[Dict[str, AgentExtension]] = []
    if hasattr(agent, 'extensions'):
        ext_list = agent.extensions
        if isinstance(ext_list, list):
            for ext in ext_list:
                if isinstance(ext, dict) and 'uri' in ext:
                    extensions.append(ext)
    
    # Create and return capabilities
    return AgentCapabilities(
        streaming=streaming,
        push_notifications=push_notifications,
        state_transition_history=state_transition_history,
        extensions=extensions if extensions else None
    )
