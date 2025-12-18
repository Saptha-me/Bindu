"""MCP server configuration for OAuth providers.

This module maps OAuth providers to their corresponding MCP server packages
and defines how credentials should be injected as environment variables.
"""

from typing import Any

# MCP server configuration mapping
# Maps provider names to MCP server package information
MCP_SERVER_CONFIG: dict[str, dict[str, Any]] = {
    "notion": {
        "package": "@modelcontextprotocol/server-notion",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-notion"],
        "env_vars": {
            "NOTION_TOKEN": "access_token",  # Maps to credential field
        },
        "description": "Notion MCP server for workspace access",
    },
    "google": {
        "package": "@modelcontextprotocol/server-google-maps",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-maps"],
        "env_vars": {
            "GOOGLE_MAPS_API_KEY": "access_token",
        },
        "description": "Google Maps MCP server",
    },
    "slack": {
        "package": "@modelcontextprotocol/server-slack",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "env_vars": {
            "SLACK_BOT_TOKEN": "access_token",
            "SLACK_TEAM_ID": "team_id",
        },
        "description": "Slack MCP server for workspace integration",
    },
    "github": {
        "package": "@modelcontextprotocol/server-github",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env_vars": {
            "GITHUB_TOKEN": "access_token",
        },
        "description": "GitHub MCP server for repository access",
    },
}


def get_mcp_server_config(provider: str) -> dict[str, Any] | None:
    """Get MCP server configuration for a provider.
    
    Args:
        provider: OAuth provider name
    
    Returns:
        MCP server configuration or None if not supported
    """
    return MCP_SERVER_CONFIG.get(provider)


def get_supported_providers() -> list[str]:
    """Get list of supported MCP providers.
    
    Returns:
        List of provider names
    """
    return list(MCP_SERVER_CONFIG.keys())


def is_provider_supported(provider: str) -> bool:
    """Check if provider has MCP server support.
    
    Args:
        provider: OAuth provider name
    
    Returns:
        True if provider is supported
    """
    return provider in MCP_SERVER_CONFIG
