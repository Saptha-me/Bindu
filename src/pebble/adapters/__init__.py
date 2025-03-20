"""
Adapters for different agent frameworks.

This module provides adapters that translate between different agent frameworks
and the unified pebble protocol.
"""

from pebble.adapters.agno_adapter import AgnoAdapter
from pebble.adapters.crew_adapter import CrewAdapter

__all__ = ["AgnoAdapter", "CrewAdapter"]
