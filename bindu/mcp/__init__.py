"""MCP (Model Context Protocol) integration module.

Provides MCP server configuration and credential injection for external services.
"""

from bindu.mcp.credential_injector import CredentialInjector
from bindu.mcp.server_config import (
    MCP_SERVER_CONFIG,
    get_mcp_server_config,
    get_supported_providers,
    is_provider_supported,
)

__all__ = [
    "CredentialInjector",
    "MCP_SERVER_CONFIG",
    "get_mcp_server_config",
    "get_supported_providers",
    "is_provider_supported",
]
