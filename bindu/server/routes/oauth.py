"""OAuth flow endpoints for external service authorization.

This module provides endpoints for initiating OAuth flows, handling callbacks,
and managing OAuth connections for external services (Notion, Google, etc.).
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from bindu.auth.kratos_client import KratosClient
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.routes.oauth")

# OAuth provider configurations
OAUTH_PROVIDERS = {
    "notion": {
        "authorize_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "scopes": ["read_content"],
    },
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"],
    },
    "slack": {
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "scopes": ["channels:read", "chat:write"],
    },
}

# In-memory state storage (should be Redis in production)
_oauth_states: dict[str, dict[str, Any]] = {}


async def oauth_authorize(request: Request) -> JSONResponse | RedirectResponse:
    """Initiate OAuth authorization flow for a provider.
    
    GET /oauth/authorize/{provider}
    
    Args:
        request: HTTP request with provider in path
        
    Returns:
        Redirect to provider's authorization URL or JSON error
    """
    provider = request.path_params.get("provider")
    
    if provider not in OAUTH_PROVIDERS:
        return JSONResponse(
            {"error": "invalid_provider", "message": f"Provider '{provider}' not supported"},
            status_code=400,
        )
    
    # Check if user is authenticated
    if not hasattr(request.state, "user"):
        return JSONResponse(
            {"error": "unauthorized", "message": "Authentication required"},
            status_code=401,
        )
    
    user_id = request.state.user.get("sub")
    
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    
    # Store state with user_id and provider
    _oauth_states[state] = {
        "user_id": user_id,
        "provider": provider,
    }
    
    # Build authorization URL
    provider_config = OAUTH_PROVIDERS[provider]
    redirect_uri = f"{app_settings.network.default_url}/oauth/callback/{provider}"
    
    # Get client ID from environment (should be configured)
    client_id = _get_client_id(provider)
    if not client_id:
        return JSONResponse(
            {"error": "configuration_error", "message": f"OAuth client not configured for {provider}"},
            status_code=500,
        )
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": " ".join(provider_config["scopes"]),
    }
    
    # Provider-specific parameters
    if provider == "google":
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    
    auth_url = f"{provider_config['authorize_url']}?{urlencode(params)}"
    
    logger.info(f"Initiating OAuth flow for {provider}, user {user_id}")
    
    # Return authorization URL (client will redirect)
    return JSONResponse({
        "authorization_url": auth_url,
        "state": state,
    })


async def oauth_callback(request: Request) -> RedirectResponse | JSONResponse:
    """Handle OAuth callback from provider.
    
    GET /oauth/callback/{provider}?code=...&state=...
    
    Args:
        request: HTTP request with authorization code and state
        
    Returns:
        Redirect to success page or JSON error
    """
    provider = request.path_params.get("provider")
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    
    # Check for OAuth error
    if error:
        logger.error(f"OAuth error from {provider}: {error}")
        return RedirectResponse(
            f"{app_settings.network.default_url}/oauth/error?error={error}"
        )
    
    # Validate state (CSRF protection)
    if not state or state not in _oauth_states:
        logger.error(f"Invalid OAuth state: {state}")
        return JSONResponse(
            {"error": "invalid_state", "message": "Invalid or expired state token"},
            status_code=400,
        )
    
    state_data = _oauth_states.pop(state)
    user_id = state_data["user_id"]
    expected_provider = state_data["provider"]
    
    if provider != expected_provider:
        logger.error(f"Provider mismatch: expected {expected_provider}, got {provider}")
        return JSONResponse(
            {"error": "provider_mismatch"},
            status_code=400,
        )
    
    # Exchange authorization code for tokens
    try:
        tokens = await _exchange_code_for_tokens(provider, code)
    except Exception as e:
        logger.error(f"Token exchange failed for {provider}: {e}")
        return JSONResponse(
            {"error": "token_exchange_failed", "message": str(e)},
            status_code=500,
        )
    
    # Store tokens in Kratos
    try:
        kratos_admin_url = getattr(
            app_settings, "kratos_admin_url", "http://localhost:4434"
        )
        async with KratosClient(kratos_admin_url) as kratos_client:
            # Get provider-specific metadata
            metadata = await _get_provider_metadata(provider, tokens)
            
            await kratos_client.store_oauth_token(
                user_id, provider, tokens, metadata
            )
        
        logger.info(f"OAuth tokens stored for {provider}, user {user_id}")
    except Exception as e:
        logger.error(f"Failed to store tokens for {provider}: {e}")
        return JSONResponse(
            {"error": "storage_failed", "message": str(e)},
            status_code=500,
        )
    
    # Redirect to success page
    return RedirectResponse(
        f"{app_settings.network.default_url}/oauth/success?provider={provider}"
    )


async def list_connections(request: Request) -> JSONResponse:
    """List user's OAuth connections.
    
    GET /oauth/connections
    
    Args:
        request: HTTP request
        
    Returns:
        JSON list of connections
    """
    # Check if user is authenticated
    if not hasattr(request.state, "user"):
        return JSONResponse(
            {"error": "unauthorized", "message": "Authentication required"},
            status_code=401,
        )
    
    user_id = request.state.user.get("sub")
    
    try:
        kratos_admin_url = getattr(
            app_settings, "kratos_admin_url", "http://localhost:4434"
        )
        async with KratosClient(kratos_admin_url) as kratos_client:
            connections = await kratos_client.list_user_connections(user_id)
        
        return JSONResponse({"connections": connections})
    except Exception as e:
        logger.error(f"Failed to list connections for user {user_id}: {e}")
        return JSONResponse(
            {"error": "list_failed", "message": str(e)},
            status_code=500,
        )


async def revoke_connection(request: Request) -> JSONResponse:
    """Revoke OAuth connection for a provider.
    
    DELETE /oauth/connections/{provider}
    
    Args:
        request: HTTP request with provider in path
        
    Returns:
        JSON success response
    """
    provider = request.path_params.get("provider")
    
    # Check if user is authenticated
    if not hasattr(request.state, "user"):
        return JSONResponse(
            {"error": "unauthorized", "message": "Authentication required"},
            status_code=401,
        )
    
    user_id = request.state.user.get("sub")
    
    try:
        kratos_admin_url = getattr(
            app_settings, "kratos_admin_url", "http://localhost:4434"
        )
        async with KratosClient(kratos_admin_url) as kratos_client:
            await kratos_client.revoke_oauth_connection(user_id, provider)
        
        logger.info(f"OAuth connection revoked for {provider}, user {user_id}")
        return JSONResponse({"success": True, "provider": provider})
    except Exception as e:
        logger.error(f"Failed to revoke connection for {provider}: {e}")
        return JSONResponse(
            {"error": "revoke_failed", "message": str(e)},
            status_code=500,
        )


# Helper functions

def _get_client_id(provider: str) -> str | None:
    """Get OAuth client ID for provider from environment."""
    import os
    
    env_var = f"{provider.upper()}_CLIENT_ID"
    return os.getenv(env_var)


def _get_client_secret(provider: str) -> str | None:
    """Get OAuth client secret for provider from environment."""
    import os
    
    env_var = f"{provider.upper()}_CLIENT_SECRET"
    return os.getenv(env_var)


async def _exchange_code_for_tokens(provider: str, code: str) -> dict[str, Any]:
    """Exchange authorization code for access/refresh tokens.
    
    Args:
        provider: OAuth provider name
        code: Authorization code
        
    Returns:
        Token response from provider
        
    Raises:
        Exception: If token exchange fails
    """
    import httpx
    
    provider_config = OAUTH_PROVIDERS[provider]
    redirect_uri = f"{app_settings.network.default_url}/oauth/callback/{provider}"
    
    client_id = _get_client_id(provider)
    client_secret = _get_client_secret(provider)
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(provider_config["token_url"], data=data)
        response.raise_for_status()
        return response.json()


async def _get_provider_metadata(provider: str, tokens: dict[str, Any]) -> dict[str, Any]:
    """Get provider-specific metadata (workspace info, etc.).
    
    Args:
        provider: OAuth provider name
        tokens: OAuth tokens
        
    Returns:
        Provider-specific metadata
    """
    import httpx
    
    metadata = {}
    
    if provider == "notion":
        # Get workspace info from Notion API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.notion.com/v1/users/me",
                    headers={
                        "Authorization": f"Bearer {tokens['access_token']}",
                        "Notion-Version": "2022-06-28",
                    },
                )
                response.raise_for_status()
                user_info = response.json()
                
                metadata["workspace_id"] = user_info.get("workspace_id")
                metadata["workspace_name"] = user_info.get("workspace_name")
        except Exception as e:
            logger.warning(f"Failed to get Notion workspace info: {e}")
    
    return metadata


# Route definitions
oauth_routes = [
    Route("/oauth/authorize/{provider}", oauth_authorize, methods=["GET"]),
    Route("/oauth/callback/{provider}", oauth_callback, methods=["GET"]),
    Route("/oauth/connections", list_connections, methods=["GET"]),
    Route("/oauth/connections/{provider}", revoke_connection, methods=["DELETE"]),
]
