# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Agent metadata setup utilities for the Pebbling framework."""

import uuid
from typing import List, Optional

from pebbling.agent.metadata.agent_capabilities import get_agent_capabilities
from pebbling.agent.metadata.agent_skills import get_agent_skills
from pebbling.protocol.types import (
    AgentCapabilities,
    AgentManifest,
    AgentSkill,
)
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.agent.metadata.setup_metadata")

def setup_agent_metadata(
    manifest: AgentManifest, 
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    examples: Optional[List[str]] = None,
) -> None:
    """Set up agent metadata for proper registration and discovery.
    
    This function configures an agent's metadata including name, description,
    tags, and usage examples. These properties are essential for agent
    discovery in the registry and for proper integration with the 
    Pebbling framework.
    
    Args:
        manifest: The agent manifest to attach metadata to
        name: The name of the agent (defaults to function name if None)
        description: Human-readable description of the agent's capabilities
        tags: List of tags for categorizing the agent
        examples: List of example prompts that demonstrate agent usage
    """
    if name is None:
        name = getattr(manifest, 'name', manifest.__class__.__name__)
        
    manifest.name: str = name
    manifest.id: str = getattr(manifest, 'id', str(uuid.uuid4()))
    
    # Extract or create capabilities and skills
    manifest.capabilities: AgentCapabilities = get_agent_capabilities(manifest)
    manifest.skills: List[AgentSkill] = get_agent_skills(manifest)