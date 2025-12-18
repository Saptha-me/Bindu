"""Ory Kratos client for identity and credential management.

This module provides a client for interacting with Ory Kratos's admin API
for user identity management and OAuth credential storage/retrieval.
"""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta
from typing import Any

from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.kratos_client")


class KratosClient:
    """Client for Ory Kratos identity management operations.
    
    Handles user identity management, OAuth credential storage/retrieval,
    and token refresh for external services.
    """

    def __init__(self, admin_url: str, timeout: int = 10):
        """Initialize Kratos client.
        
        Args:
            admin_url: Kratos admin API URL (e.g., http://localhost:4434)
            timeout: Request timeout in seconds
        """
        self.admin_url = admin_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"Kratos client initialized with admin URL: {admin_url}")

    async def get_identity(self, user_id: str) -> dict[str, Any]:
        """Get user identity by ID.
        
        Args:
            user_id: Kratos identity ID
            
        Returns:
            Identity object with traits, metadata, and credentials
            
        Raises:
            httpx.HTTPError: If identity not found
        """
        url = f"{self.admin_url}/admin/identities/{user_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            identity = response.json()
            
            logger.debug(f"Retrieved identity: {user_id}")
            return identity
        except httpx.HTTPError as e:
            logger.error(f"Failed to get identity {user_id}: {e}")
            raise

    async def update_identity(
        self, user_id: str, traits: dict[str, Any]
    ) -> dict[str, Any]:
        """Update user identity traits.
        
        Args:
            user_id: Kratos identity ID
            traits: Updated traits dictionary
            
        Returns:
            Updated identity object
            
        Raises:
            httpx.HTTPError: If update fails
        """
        url = f"{self.admin_url}/admin/identities/{user_id}"
        
        # Get current identity first
        identity = await self.get_identity(user_id)
        
        # Update with new traits
        data = {
            "schema_id": identity["schema_id"],
            "traits": traits,
            "state": identity["state"],
        }

        try:
            response = await self.client.put(url, json=data)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Updated identity: {user_id}")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Failed to update identity {user_id}: {e}")
            raise

    async def get_oauth_token(
        self, user_id: str, provider: str
    ) -> dict[str, Any] | None:
        """Get OAuth token for a provider from user's identity.
        
        Args:
            user_id: Kratos identity ID
            provider: OAuth provider name (e.g., "notion", "google")
            
        Returns:
            OAuth token data or None if not connected:
            - access_token: str
            - refresh_token: str
            - token_type: str
            - expires_at: str (ISO 8601)
            - Additional provider-specific fields
            
        Raises:
            httpx.HTTPError: If identity retrieval fails
        """
        identity = await self.get_identity(user_id)
        traits = identity.get("traits", {})
        oauth_connections = traits.get("oauth_connections", {})
        provider_data = oauth_connections.get(provider, {})

        if not provider_data.get("connected", False):
            logger.debug(f"Provider {provider} not connected for user {user_id}")
            return None

        logger.debug(f"Retrieved OAuth token for {provider}, user {user_id}")
        return provider_data

    async def store_oauth_token(
        self,
        user_id: str,
        provider: str,
        tokens: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Store OAuth tokens for a provider in user's identity.
        
        Args:
            user_id: Kratos identity ID
            provider: OAuth provider name
            tokens: Token data from OAuth flow:
                - access_token: str
                - refresh_token: str (optional)
                - token_type: str
                - expires_in: int (seconds)
            metadata: Additional provider-specific metadata
            
        Returns:
            Updated identity object
            
        Raises:
            httpx.HTTPError: If storage fails
        """
        identity = await self.get_identity(user_id)
        traits = identity.get("traits", {})
        
        # Initialize oauth_connections if not exists
        if "oauth_connections" not in traits:
            traits["oauth_connections"] = {}
        
        # Calculate expiration time
        expires_in = tokens.get("expires_in", 3600)
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        # Store token data
        provider_data = {
            "connected": True,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_at": expires_at,
        }
        
        # Add provider-specific metadata
        if metadata:
            provider_data.update(metadata)
        
        traits["oauth_connections"][provider] = provider_data
        
        # Update identity
        result = await self.update_identity(user_id, traits)
        
        logger.info(f"Stored OAuth token for {provider}, user {user_id}")
        return result

    async def refresh_oauth_token(
        self, user_id: str, provider: str
    ) -> dict[str, Any] | None:
        """Refresh OAuth token for a provider.
        
        Note: This method retrieves the token but does not perform the actual
        refresh. The refresh should be done by the OAuth provider's client
        and then stored back using store_oauth_token().
        
        Args:
            user_id: Kratos identity ID
            provider: OAuth provider name
            
        Returns:
            Current token data or None if not connected
            
        Raises:
            httpx.HTTPError: If identity retrieval fails
        """
        token_data = await self.get_oauth_token(user_id, provider)
        
        if not token_data:
            return None
        
        # Check if token is expired
        expires_at_str = token_data.get("expires_at")
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() >= expires_at:
                logger.warning(
                    f"Token expired for {provider}, user {user_id}. "
                    "Refresh required."
                )
        
        return token_data

    async def revoke_oauth_connection(
        self, user_id: str, provider: str
    ) -> dict[str, Any]:
        """Revoke OAuth connection for a provider.
        
        Removes stored OAuth tokens from user's identity.
        
        Args:
            user_id: Kratos identity ID
            provider: OAuth provider name
            
        Returns:
            Updated identity object
            
        Raises:
            httpx.HTTPError: If revocation fails
        """
        identity = await self.get_identity(user_id)
        traits = identity.get("traits", {})
        oauth_connections = traits.get("oauth_connections", {})
        
        if provider in oauth_connections:
            # Mark as disconnected and clear tokens
            oauth_connections[provider] = {"connected": False}
            traits["oauth_connections"] = oauth_connections
            
            result = await self.update_identity(user_id, traits)
            
            logger.info(f"Revoked OAuth connection for {provider}, user {user_id}")
            return result
        
        logger.debug(f"No connection to revoke for {provider}, user {user_id}")
        return identity

    async def list_user_connections(self, user_id: str) -> list[dict[str, Any]]:
        """List all OAuth connections for a user.
        
        Args:
            user_id: Kratos identity ID
            
        Returns:
            List of connection objects:
            - provider: str
            - connected: bool
            - expires_at: str (if connected)
            - Additional metadata
            
        Raises:
            httpx.HTTPError: If identity retrieval fails
        """
        identity = await self.get_identity(user_id)
        traits = identity.get("traits", {})
        oauth_connections = traits.get("oauth_connections", {})
        
        connections = []
        for provider, data in oauth_connections.items():
            connection = {
                "provider": provider,
                "connected": data.get("connected", False),
            }
            
            if data.get("connected"):
                connection["expires_at"] = data.get("expires_at")
                # Add provider-specific metadata (without sensitive tokens)
                for key, value in data.items():
                    if key not in ["access_token", "refresh_token", "connected"]:
                        connection[key] = value
            
            connections.append(connection)
        
        logger.debug(f"Listed {len(connections)} connections for user {user_id}")
        return connections

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
