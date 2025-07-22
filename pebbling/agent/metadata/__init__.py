"""
Agent metadata extraction and management module.

This module provides functions for extracting and managing agent metadata,
including capabilities and skills information.
"""

from pebbling.agent.metadata.agent_capabilities import get_agent_capabilities
from pebbling.agent.metadata.agent_skills import get_agent_skills
from pebbling.agent.metadata.setup_metadata import setup_agent_metadata

__all__ = [
    "get_agent_capabilities",
    "get_agent_skills",
    "setup_agent_metadata"
]