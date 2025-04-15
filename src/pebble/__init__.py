"""
Pebble Framework

A standardized protocol for deploying and communicating with AI agents from different frameworks.
"""

__version__ = "0.1.0"

# Core deployment functionality
from pebble.core.pebblify import deploy, get_adapter_for_agent

# Protocol and models
from pebble.core.protocol import AgentProtocol
from pebble.schemas.models import (
    ActionRequest, ActionResponse, StatusResponse,
    Message, MessageRole, AgentStatus, DeploymentConfig
)

# Adapters
from pebble.adapters import AgnoAdapter

# Server and configuration
from pebble.api.server import create_app, start_server

# Configuration
from pebble.utils.config import get_project_root, ensure_env_file, load_env_vars

__all__ = [
    # Core functionality
    "deploy", "get_adapter_for_agent",
    
    # Protocol and models
    "AgentProtocol", "ActionRequest", "ActionResponse", "StatusResponse",
    "Message", "MessageRole", "AgentStatus",
    
    # Adapters
    "AgnoAdapter", "CrewAdapter",
    
    # Server and configuration
    "DeploymentConfig", "create_app", "start_server",
    
    # Configuration
    "get_project_root", "ensure_env_file", "load_env_vars"
]
