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
from pebble.adapters import AgnoAdapter, CrewAdapter

# Server and configuration
from pebble.api.server import create_app, start_server

# Authentication
from pebble.security.auth import get_auth_token

# Security
from pebble.security.keys import create_api_key, validate_api_key

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
    
    # Authentication
    "get_auth_token",
    
    # Security
    "create_api_key", "validate_api_key",
    
    # Configuration
    "get_project_root", "ensure_env_file", "load_env_vars"
]
