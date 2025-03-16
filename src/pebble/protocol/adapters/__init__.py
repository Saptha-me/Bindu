"""
Adapters for different agent types to communicate using the protocol.
"""
from .base import BaseAdapter
from .smol_adapter import SmolAdapter
from .agno_adapter import AgnoAdapter
from .crew_adapter import CrewAdapter

__all__ = ["BaseAdapter", "SmolAdapter", "AgnoAdapter", "CrewAdapter"]
