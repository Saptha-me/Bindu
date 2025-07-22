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
from typing import List

from pebbling.protocol.types import AgentManifest, AgentSkill
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.agent.metadata.agent_skills")

def get_agent_skills(agent: AgentManifest):
    """
    Extract skills from agent for registration.
    
    This function checks if the agent already has skills defined in the proper format.
    If not, it tries to extract skill-related attributes from the agent object.
    
    Args:
        agent: The agent object
        
    Returns:
        List[AgentSkill]: List of skills the agent supports
    """
    logger.debug("Extracting agent skills")
    
    # If agent already has skills property
    if hasattr(agent, 'skills'):
        if callable(agent.skills):
            skill_list: List[AgentSkill] = agent.skills()
            if isinstance(skill_list, list):
                if all(isinstance(skill, AgentSkill) for skill in skill_list):
                    return skill_list
                elif all(isinstance(skill, dict) for skill in skill_list):
                    return [AgentSkill(**skill) for skill in skill_list if 'id' in skill and 'name' in skill]
        elif isinstance(agent.skills, list):
            if all(isinstance(skill, AgentSkill) for skill in agent.skills):
                return agent.skills
            elif all(isinstance(skill, dict) for skill in agent.skills):
                return [AgentSkill(**skill) for skill in agent.skills if 'id' in skill and 'name' in skill]
    
    # If we can't extract skills, create a basic skill
    if hasattr(agent, 'name') and hasattr(agent, 'description'):
        # Extract input/output modes if available
        input_modes: List[str] = ["text"]  # Default to text
        output_modes: List[str] = ["text"]  # Default to text
        
        if hasattr(agent, 'input_content_types') and agent.input_content_types:
            if any("image" in content_type for content_type in agent.input_content_types):
                input_modes.append("image")
            if any("audio" in content_type for content_type in agent.input_content_types):
                input_modes.append("audio")
                
        if hasattr(agent, 'output_content_types') and agent.output_content_types:
            if any("image" in content_type for content_type in agent.output_content_types):
                output_modes.append("image")
            if any("audio" in content_type for content_type in agent.output_content_types):
                output_modes.append("audio")
        
        # Create a default skill
        default_skill: AgentSkill = AgentSkill(
            id=str(uuid.uuid4()),
            name=agent.name,
            description=agent.description,
            input_modes=input_modes,
            output_modes=output_modes,
            tags=["ai", "agent"]
        )
        
        return [default_skill]
    
    # If we can't create a skill, return empty list
    logger.warning("Could not extract or create skills for agent")
    return []
