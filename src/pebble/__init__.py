"""Pebble: A communication protocol for different agent types.

Pebble provides a standardized communication protocol for various agent types
(smolagent, agno, crew) to interact with each other.
"""

__version__ = "0.1.0"

from .pebble import pebble
from .protocol.protocol import Protocol, Message, MessageType, AgentType
from .protocol.coordinator import ProtocolCoordinator
from .protocol.adapters import SmolAdapter, AgnoAdapter, CrewAdapter

__all__ = [
    'pebble',
    'Protocol',
    'Message',
    'MessageType',
    'AgentType',
    'ProtocolCoordinator',
    'SmolAdapter',
    'AgnoAdapter',
    'CrewAdapter',
]