# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - Raahul

import uuid
from typing import List, Optional

from pebbling.utils.logging import get_logger
from pebbling.protocol.types import (
    AgentManifest,
    AgentCapabilities, 
    AgentSkill,
)

logger = get_logger("pebbling.agent.metadata.setup_metadata")

def setup_agent_metadata(
    manifest: AgentManifest, 
    name: Optional[str] = None
):
    if name is None:
        name = getattr(manifest, 'name', manifest.__class__.__name__)
        
    manifest.name: str = name
    manifest.id: str = getattr(manifest, 'id', str(uuid.uuid4()))
    
    # Extract or create capabilities and skills
    manifest.capabilities: AgentCapabilities = get_agent_capabilities(manifest)
    manifest.skills: List[AgentSkill] = get_agent_skills(manifest)