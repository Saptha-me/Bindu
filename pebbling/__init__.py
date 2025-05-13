"""
🐧 pebbling Protocol Framework.

A protocol framework for agent-to-agent communication.
"""

__version__ = "0.1.0"

# Define public API
__all__ = ["pebblingProtocol", "ProtocolMethod", "pebblify"]

from pebbling.core.protocol import ProtocolMethod, pebblingProtocol
from pebbling.server.pebbling_server import pebblify
