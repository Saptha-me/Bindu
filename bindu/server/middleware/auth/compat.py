"""Compatibility middleware for dual Auth0/Hydra authentication.

This middleware supports both Auth0 and Hydra authentication during the
migration period, allowing gradual transition from Auth0 to Hydra.
"""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from bindu.server.middleware.auth.auth0 import Auth0Middleware
from bindu.server.middleware.auth.hydra import HydraMiddleware
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.auth.compat")


class CompatAuthMiddleware(BaseHTTPMiddleware):
    """Compatibility middleware supporting both Auth0 and Hydra authentication.
    
    During the migration period, this middleware tries Hydra authentication first,
    and falls back to Auth0 if Hydra validation fails. This allows:
    - New users to use Hydra authentication
    - Existing users to continue using Auth0
    - Gradual migration without service disruption
    
    Usage:
        Set USE_HYDRA_AUTH=true to enable Hydra as primary
        Set USE_HYDRA_AUTH=false to use Auth0 only (legacy mode)
    """

    def __init__(self, app: Callable, auth_config: any, hydra_config: any):
        """Initialize compatibility middleware.
        
        Args:
            app: ASGI application
            auth_config: Auth0 configuration
            hydra_config: Hydra configuration
        """
        super().__init__(app)
        self.use_hydra = app_settings.use_hydra_auth
        
        # Initialize both middleware instances
        self.auth0_middleware = Auth0Middleware(app, auth_config)
        self.hydra_middleware = HydraMiddleware(app, hydra_config)
        
        logger.info(
            f"Compatibility middleware initialized. "
            f"Primary: {'Hydra' if self.use_hydra else 'Auth0'}"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through compatibility layer.
        
        Flow:
        1. If USE_HYDRA_AUTH=true:
           - Try Hydra first
           - Fall back to Auth0 if Hydra fails
        2. If USE_HYDRA_AUTH=false:
           - Use Auth0 only (legacy mode)
        
        Args:
            request: HTTP request
            call_next: Next middleware/endpoint
            
        Returns:
            Response from endpoint or error response
        """
        path = request.url.path
        
        # Check if endpoint is public (skip auth)
        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint: {path}")
            return await call_next(request)
        
        # Extract token once
        token = self._extract_token(request)
        if not token:
            logger.warning(f"No token provided for {path}")
            return await self._auth_required_error(request)
        
        if self.use_hydra:
            # Try Hydra first (primary)
            try:
                response = await self.hydra_middleware.dispatch(request, call_next)
                if response.status_code != 401:
                    logger.debug(f"Authenticated via Hydra: {path}")
                    return response
                logger.debug(f"Hydra auth failed, trying Auth0 fallback: {path}")
            except Exception as e:
                logger.debug(f"Hydra error, trying Auth0 fallback: {e}")
            
            # Fall back to Auth0
            try:
                response = await self.auth0_middleware.dispatch(request, call_next)
                if response.status_code != 401:
                    logger.info(f"Authenticated via Auth0 (fallback): {path}")
                    # Mark user for migration
                    if hasattr(request.state, "user"):
                        request.state.user["_needs_migration"] = True
                return response
            except Exception as e:
                logger.error(f"Both Hydra and Auth0 failed: {e}")
                return await self._auth_required_error(request)
        else:
            # Legacy mode: Auth0 only
            logger.debug(f"Using Auth0 only (legacy mode): {path}")
            return await self.auth0_middleware.dispatch(request, call_next)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public."""
        # Use Auth0 middleware's public endpoint check
        return self.auth0_middleware._is_public_endpoint(path)

    def _extract_token(self, request: Request) -> str | None:
        """Extract Bearer token from Authorization header."""
        return self.auth0_middleware._extract_token(request)

    async def _auth_required_error(self, request: Request):
        """Return authentication required error."""
        return await self.auth0_middleware._auth_required_error(request)
