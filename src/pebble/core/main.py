"""
Main entry point for the Pebble framework.

This module serves as the main entry point for the Pebble framework,
providing a unified interface for agent deployment and interaction.
"""

from pebble.core.pebblify import deploy, get_adapter_for_agent
from pebble.core.protocol import AgentProtocol
from pebble.api.server import create_app, start_server
from pebble.schemas.models import DeploymentConfig

__all__ = [
    "deploy",
    "get_adapter_for_agent",
    "AgentProtocol",
    "create_app",
    "start_server",
    "DeploymentConfig"
]
