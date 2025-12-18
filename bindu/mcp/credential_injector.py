"""Credential injection for MCP servers.

This module handles injecting OAuth credentials into MCP server processes
as environment variables.
"""

from __future__ import annotations

from typing import Any

from bindu.mcp.server_config import get_mcp_server_config
from bindu.utils.logging import get_logger

logger = get_logger("bindu.mcp.credential_injector")


class CredentialInjector:
    """Injects OAuth credentials into MCP server environment."""

    @staticmethod
    def build_env_vars(
        provider: str, credentials: dict[str, Any], base_env: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Build environment variables for MCP server.
        
        Args:
            provider: OAuth provider name
            credentials: Credential data from CredentialManager
            base_env: Base environment variables to extend
        
        Returns:
            Environment variables dict for MCP server process
        """
        env = base_env.copy() if base_env else {}
        
        # Get MCP server config for provider
        mcp_config = get_mcp_server_config(provider)
        if not mcp_config:
            logger.warning(f"No MCP config found for provider: {provider}")
            return env
        
        # Map credential fields to environment variables
        env_var_mapping = mcp_config.get("env_vars", {})
        
        for env_var_name, credential_field in env_var_mapping.items():
            # Get credential value
            credential_value = credentials.get(credential_field)
            
            if credential_value:
                env[env_var_name] = str(credential_value)
                logger.debug(f"Mapped {credential_field} -> {env_var_name}")
            else:
                logger.warning(
                    f"Missing credential field '{credential_field}' for {provider}"
                )
        
        return env

    @staticmethod
    def inject_all_credentials(
        credentials: dict[str, dict[str, Any]], base_env: dict[str, str] | None = None
    ) -> dict[str, dict[str, str]]:
        """Build environment variables for all providers.
        
        Args:
            credentials: Dict mapping provider names to credential data
            base_env: Base environment variables
        
        Returns:
            Dict mapping provider names to their environment variables
        """
        provider_envs = {}
        
        for provider, creds in credentials.items():
            env = CredentialInjector.build_env_vars(provider, creds, base_env)
            provider_envs[provider] = env
            
            logger.debug(f"Built environment for {provider}: {len(env)} vars")
        
        return provider_envs

    @staticmethod
    def get_server_params(provider: str, credentials: dict[str, Any]) -> dict[str, Any]:
        """Get MCP server parameters with injected credentials.
        
        Args:
            provider: OAuth provider name
            credentials: Credential data
        
        Returns:
            Server parameters dict with command, args, and env
        """
        mcp_config = get_mcp_server_config(provider)
        if not mcp_config:
            raise ValueError(f"No MCP server config for provider: {provider}")
        
        # Build environment variables
        env = CredentialInjector.build_env_vars(provider, credentials)
        
        # Return server parameters
        return {
            "command": mcp_config["command"],
            "args": mcp_config["args"],
            "env": env,
        }
