"""
Pebble constants and enumerations.

This module contains centralized definitions of constants and enumerations
used throughout the pebble library.
"""

from enum import Enum


class AgentType(str, Enum):
    """Enumeration of supported agent types.
    
    These values should be used consistently across all pebble modules when
    referring to different agent frameworks.
    """
    AGNO = "agno"
    SMOL = "smol"
    CREW = "crew"
    CUSTOM = "custom"  # For user-defined agent types
