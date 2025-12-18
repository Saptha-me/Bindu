"""Credential manager for OAuth token management and injection.

This module provides credential management for agents requiring external
service access (Notion, Google Maps, etc.). It checks requirements, fetches
credentials from Kratos, and injects them into agent context.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bindu.auth.kratos_client import KratosClient
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.penguin.credential_manager")


class CredentialManager:
    """Manages OAuth credentials for agent execution.
    
    Handles credential requirement checking, retrieval from Kratos,
    token refresh, and injection into agent context.
    """

    def __init__(self, kratos_admin_url: str | None = None):
        """Initialize credential manager.
        
        Args:
            kratos_admin_url: Kratos admin API URL (defaults to settings)
        """
        self.kratos_admin_url = kratos_admin_url or getattr(
            app_settings, "kratos_admin_url", "http://localhost:4434"
        )

    async def check_requirements(
        self, user_id: str, credential_requirements: dict[str, Any]
    ) -> dict[str, Any]:
        """Check if user has all required credentials.
        
        Args:
            user_id: User's Kratos identity ID
            credential_requirements: Dict of provider requirements from agent config
                Example:
                {
                    "notion": {
                        "type": "oauth2",
                        "provider": "notion",
                        "scopes": ["read_content"],
                        "required": True
                    }
                }
        
        Returns:
            Check result:
            {
                "satisfied": bool,
                "missing": list[str],  # Missing provider names
                "auth_urls": dict[str, str]  # Authorization URLs for missing providers
            }
        """
        missing_providers = []
        auth_urls = {}
        
        async with KratosClient(self.kratos_admin_url) as kratos_client:
            for provider, config in credential_requirements.items():
                # Skip if not required
                if not config.get("required", True):
                    continue
                
                # Check if user has this provider connected
                token_data = await kratos_client.get_oauth_token(user_id, provider)
                
                if not token_data:
                    missing_providers.append(provider)
                    # Generate authorization URL
                    auth_url = f"{app_settings.network.default_url}/oauth/authorize/{provider}"
                    auth_urls[provider] = auth_url
                    logger.debug(f"Missing required credential: {provider}")
                else:
                    # Check if token is expired
                    expires_at_str = token_data.get("expires_at")
                    if expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str)
                        if datetime.utcnow() >= expires_at:
                            logger.warning(f"Credential expired for {provider}")
                            missing_providers.append(provider)
                            auth_urls[provider] = f"{app_settings.network.default_url}/oauth/authorize/{provider}"
        
        satisfied = len(missing_providers) == 0
        
        logger.info(
            f"Credential check for user {user_id}: "
            f"satisfied={satisfied}, missing={len(missing_providers)}"
        )
        
        return {
            "satisfied": satisfied,
            "missing": missing_providers,
            "auth_urls": auth_urls,
        }

    async def get_credentials(
        self, user_id: str, providers: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Get OAuth credentials for specified providers.
        
        Args:
            user_id: User's Kratos identity ID
            providers: List of provider names to fetch
        
        Returns:
            Dict mapping provider names to credential data:
            {
                "notion": {
                    "access_token": "...",
                    "token_type": "Bearer",
                    "workspace_id": "...",
                    ...
                }
            }
        """
        credentials = {}
        
        async with KratosClient(self.kratos_admin_url) as kratos_client:
            for provider in providers:
                token_data = await kratos_client.get_oauth_token(user_id, provider)
                
                if token_data:
                    # Remove sensitive refresh token from context
                    # (keep only access token for agent use)
                    safe_credentials = {
                        "access_token": token_data.get("access_token"),
                        "token_type": token_data.get("token_type", "Bearer"),
                    }
                    
                    # Add provider-specific metadata
                    for key, value in token_data.items():
                        if key not in ["access_token", "refresh_token", "connected", "expires_at"]:
                            safe_credentials[key] = value
                    
                    credentials[provider] = safe_credentials
                    logger.debug(f"Retrieved credentials for {provider}")
                else:
                    logger.warning(f"No credentials found for {provider}")
        
        return credentials

    def inject_into_context(
        self, context: dict[str, Any], credentials: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Inject credentials into agent execution context.
        
        Args:
            context: Agent execution context
            credentials: Credentials dict from get_credentials()
        
        Returns:
            Updated context with credentials
        """
        context["credentials"] = credentials
        
        logger.debug(f"Injected {len(credentials)} credentials into context")
        
        return context

    async def refresh_if_needed(
        self, user_id: str, provider: str
    ) -> dict[str, Any] | None:
        """Check if token needs refresh and return current token data.
        
        Note: Actual token refresh should be implemented by calling the
        provider's token refresh endpoint and storing the new tokens.
        
        Args:
            user_id: User's Kratos identity ID
            provider: Provider name
        
        Returns:
            Current token data or None if not connected
        """
        async with KratosClient(self.kratos_admin_url) as kratos_client:
            token_data = await kratos_client.refresh_oauth_token(user_id, provider)
            
            if not token_data:
                return None
            
            # Check if expired
            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.utcnow() >= expires_at:
                    logger.warning(
                        f"Token expired for {provider}, user {user_id}. "
                        "Refresh implementation needed."
                    )
                    # TODO: Implement actual token refresh using provider's API
                    # For now, return None to indicate refresh needed
                    return None
            
            return token_data
