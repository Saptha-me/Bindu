"""Ory Hydra client for OAuth2 operations.

This module provides a client for interacting with Ory Hydra's admin API
for token introspection, refresh, revocation, and OAuth2 client management.
"""

from __future__ import annotations

import httpx
from typing import Any

from bindu.utils.logging import get_logger

logger = get_logger("bindu.auth.hydra_client")


class HydraClient:
    """Client for Ory Hydra OAuth2 server operations.
    
    Handles token introspection, refresh, revocation, and OAuth2 client
    management via Hydra's admin API.
    """

    def __init__(self, admin_url: str, timeout: int = 10):
        """Initialize Hydra client.
        
        Args:
            admin_url: Hydra admin API URL (e.g., http://localhost:4445)
            timeout: Request timeout in seconds
        """
        self.admin_url = admin_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        logger.info(f"Hydra client initialized with admin URL: {admin_url}")

    async def introspect_token(self, token: str, scope: str | None = None) -> dict[str, Any]:
        """Introspect an OAuth2 access token.
        
        Validates the token and returns its metadata including expiration,
        subject, scopes, and client information.
        
        Args:
            token: OAuth2 access token to introspect
            scope: Optional scope to check (e.g., "agent:read")
            
        Returns:
            Token introspection response with fields:
            - active: bool - Whether token is active
            - sub: str - Subject (user ID)
            - client_id: str - OAuth2 client ID
            - scope: str - Space-separated scopes
            - exp: int - Expiration timestamp
            - iat: int - Issued at timestamp
            
        Raises:
            httpx.HTTPError: If introspection request fails
        """
        url = f"{self.admin_url}/admin/oauth2/introspect"
        data = {"token": token}
        if scope:
            data["scope"] = scope

        try:
            response = await self.client.post(url, data=data)
            response.raise_for_status()
            result = response.json()
            
            logger.debug(
                f"Token introspection: active={result.get('active')}, "
                f"sub={result.get('sub')}, client={result.get('client_id')}"
            )
            
            return result
        except httpx.HTTPError as e:
            logger.error(f"Token introspection failed: {e}")
            raise

    async def refresh_token(
        self, refresh_token: str, client_id: str, client_secret: str
    ) -> dict[str, Any]:
        """Refresh an OAuth2 access token.
        
        Exchanges a refresh token for a new access token.
        
        Args:
            refresh_token: OAuth2 refresh token
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            
        Returns:
            Token response with fields:
            - access_token: str - New access token
            - refresh_token: str - New refresh token (if rotated)
            - token_type: str - Token type (usually "bearer")
            - expires_in: int - Seconds until expiration
            
        Raises:
            httpx.HTTPError: If token refresh fails
        """
        url = f"{self.admin_url.replace('/admin', '')}/oauth2/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            response = await self.client.post(url, data=data)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Token refreshed for client: {client_id}")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Token refresh failed: {e}")
            raise

    async def revoke_token(
        self, token: str, client_id: str, client_secret: str
    ) -> bool:
        """Revoke an OAuth2 token.
        
        Invalidates an access or refresh token.
        
        Args:
            token: Token to revoke (access or refresh)
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            
        Returns:
            True if revocation succeeded
            
        Raises:
            httpx.HTTPError: If revocation request fails
        """
        url = f"{self.admin_url}/admin/oauth2/revoke"
        data = {
            "token": token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        try:
            response = await self.client.post(url, data=data)
            response.raise_for_status()
            
            logger.info(f"Token revoked for client: {client_id}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Token revocation failed: {e}")
            raise

    async def create_oauth_client(
        self,
        client_id: str,
        client_name: str,
        redirect_uris: list[str],
        grant_types: list[str] | None = None,
        response_types: list[str] | None = None,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """Create a new OAuth2 client.
        
        Registers a new OAuth2 client in Hydra.
        
        Args:
            client_id: Unique client identifier
            client_name: Human-readable client name
            redirect_uris: List of allowed redirect URIs
            grant_types: OAuth2 grant types (default: ["authorization_code", "refresh_token"])
            response_types: OAuth2 response types (default: ["code"])
            scope: Space-separated scopes (default: "openid offline_access")
            
        Returns:
            Created client information including client_secret
            
        Raises:
            httpx.HTTPError: If client creation fails
        """
        url = f"{self.admin_url}/admin/clients"
        
        if grant_types is None:
            grant_types = ["authorization_code", "refresh_token"]
        if response_types is None:
            response_types = ["code"]
        if scope is None:
            scope = "openid offline_access"

        data = {
            "client_id": client_id,
            "client_name": client_name,
            "redirect_uris": redirect_uris,
            "grant_types": grant_types,
            "response_types": response_types,
            "scope": scope,
            "token_endpoint_auth_method": "client_secret_post",
        }

        try:
            response = await self.client.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"OAuth2 client created: {client_id}")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Client creation failed: {e}")
            raise

    async def get_oauth_client(self, client_id: str) -> dict[str, Any]:
        """Get OAuth2 client information.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Client information
            
        Raises:
            httpx.HTTPError: If client not found
        """
        url = f"{self.admin_url}/admin/clients/{client_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get client {client_id}: {e}")
            raise

    async def delete_oauth_client(self, client_id: str) -> bool:
        """Delete an OAuth2 client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if deletion succeeded
            
        Raises:
            httpx.HTTPError: If deletion fails
        """
        url = f"{self.admin_url}/admin/clients/{client_id}"

        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            
            logger.info(f"OAuth2 client deleted: {client_id}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Client deletion failed: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
