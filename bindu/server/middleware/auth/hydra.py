"""Ory Hydra authentication middleware for Bindu server.

This middleware validates OAuth2 access tokens from Ory Hydra for user authentication.
It inherits from AuthMiddleware and implements Hydra-specific token validation via
token introspection.
"""

from __future__ import annotations

from typing import Any

from bindu.auth.hydra_client import HydraClient
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .base import AuthMiddleware

logger = get_logger("bindu.server.middleware.hydra")


class HydraMiddleware(AuthMiddleware):
    """Ory Hydra OAuth2 authentication middleware.
    
    This middleware implements Hydra token validation using token introspection.
    It validates:
    - Token is active (not expired or revoked)
    - Token has required scopes (if configured)
    - Extracts user/client information from token
    
    Supports both user authentication and machine-to-machine (M2M) flows.
    """

    def _initialize_provider(self) -> None:
        """Initialize Hydra-specific components.
        
        Sets up:
        - HydraClient for token introspection
        - Hydra admin URL configuration
        """
        hydra_admin_url = getattr(
            self.config, "admin_url", "http://localhost:4445"
        )
        
        # Create async Hydra client (will be used in async context)
        self.hydra_admin_url = hydra_admin_url
        
        logger.info(
            f"Hydra middleware initialized. Admin URL: {hydra_admin_url}"
        )

    def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate Hydra OAuth2 access token.
        
        Uses Hydra's token introspection endpoint to validate the token.
        This is a synchronous wrapper that will be called from async context.
        
        Args:
            token: OAuth2 access token from Hydra
            
        Returns:
            Token introspection response
            
        Raises:
            Exception: If token is invalid, expired, or introspection fails
        """
        # Note: This will be called from async dispatch method
        # We'll need to handle the async call there
        # For now, store token for async validation
        self._current_token = token
        return {"token": token}

    async def _validate_token_async(self, token: str) -> dict[str, Any]:
        """Async token validation using Hydra introspection.
        
        Args:
            token: OAuth2 access token
            
        Returns:
            Token introspection response
            
        Raises:
            Exception: If token is invalid or introspection fails
        """
        async with HydraClient(self.hydra_admin_url) as hydra_client:
            introspection = await hydra_client.introspect_token(token)
            
            # Check if token is active
            if not introspection.get("active", False):
                raise ValueError("Token is not active (expired or revoked)")
            
            # Check required scopes if configured
            required_scopes = getattr(self.config, "required_scopes", None)
            if required_scopes:
                token_scopes = introspection.get("scope", "").split()
                missing_scopes = set(required_scopes) - set(token_scopes)
                if missing_scopes:
                    raise ValueError(
                        f"Token missing required scopes: {missing_scopes}"
                    )
            
            return introspection

    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Extract user/client information from Hydra token introspection.
        
        Args:
            token_payload: Token introspection response from Hydra
            
        Returns:
            Dictionary with standardized user information:
            - sub: Subject (user ID or client ID)
            - is_m2m: Whether this is a machine-to-machine token
            - client_id: OAuth2 client ID
            - scope: Space-separated scopes
            - permissions: List of permissions (derived from scopes)
        """
        sub = token_payload.get("sub", "")
        client_id = token_payload.get("client_id", "")
        scope = token_payload.get("scope", "")
        scopes = scope.split() if scope else []
        
        # Determine if this is M2M (client credentials flow)
        # M2M tokens typically have client_id as subject
        is_m2m = sub == client_id
        
        user_info = {
            "sub": sub,
            "is_m2m": is_m2m,
            "client_id": client_id,
            "scope": scope,
            "permissions": scopes,  # Scopes can be used as permissions
        }
        
        # Add optional fields if present
        if "exp" in token_payload:
            user_info["exp"] = token_payload["exp"]
        if "iat" in token_payload:
            user_info["iat"] = token_payload["iat"]
        
        logger.debug(
            f"Extracted user info: sub={sub}, m2m={is_m2m}, "
            f"client={client_id}, scopes={len(scopes)}"
        )
        
        return user_info

    async def dispatch(self, request, call_next):
        """Override dispatch to handle async token validation.
        
        This is necessary because Hydra token introspection is async.
        """
        from starlette.responses import Response
        
        path = request.url.path

        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint: {path}")
            return await call_next(request)

        # Extract token
        token = self._extract_token(request)
        if not token:
            logger.warning(f"No token provided for {path}")
            return await self._auth_required_error(request)

        # Validate token (async)
        try:
            token_payload = await self._validate_token_async(token)
        except Exception as e:
            logger.warning(f"Token validation failed for {path}: {e}")
            return self._handle_validation_error(e, path)

        # Extract user info
        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            from bindu.common.protocol.types import InvalidTokenError
            from bindu.utils.request_utils import extract_error_fields, jsonrpc_error
            
            code, message = extract_error_fields(InvalidTokenError)
            return jsonrpc_error(code=code, message=message, status=401)

        # Attach context to request state
        self._attach_user_context(request, user_info, token_payload)

        logger.debug(
            f"Authenticated {path} - sub={user_info.get('sub')}, "
            f"m2m={user_info.get('is_m2m', False)}"
        )

        return await call_next(request)
