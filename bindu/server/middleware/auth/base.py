"""Base authentication middleware interface for Bindu server.

Provides an abstract base class for authentication middleware supporting
multiple providers (Auth0, AWS Cognito, Azure AD, etc.).
"""

from __future__ import annotations as _annotations

import fnmatch
import json
from abc import ABC, abstractmethod
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import (
    AuthenticationRequiredError,
    InvalidTokenError,
    InvalidTokenSignatureError,
    TokenExpiredError,
)
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, jsonrpc_error

logger = get_logger("bindu.server.middleware.auth.base")


class AuthMiddleware(BaseHTTPMiddleware, ABC):
    """Abstract authentication middleware for Bindu server.

    Handles token extraction, validation, and user context attachment.
    Subclasses implement provider-specific validation logic.

    Supported providers:
    - Auth0 (Auth0Middleware)
    - AWS Cognito, Azure AD, Custom JWT (future)
    """

    def __init__(self, app: Callable, auth_config: Any) -> None:
        """Initialize authentication middleware.

        Args:
            app: ASGI application
            auth_config: Provider-specific authentication configuration
        """
        super().__init__(app)
        self.config = auth_config
        self._initialize_provider()

    # Abstract methods - Provider-specific implementation required

    @abstractmethod
    def _initialize_provider(self) -> None:
        """Initialize provider-specific components (JWKS client, validators, etc.)."""

    @abstractmethod
    def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate authentication token.

        Args:
            token: Authentication token (JWT, opaque token, etc.)

        Returns:
            Decoded token payload

        Raises:
            Exception: If token is invalid, expired, or verification fails
        """

    @abstractmethod
    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Extract standardized user information from token payload.

        Args:
            token_payload: Decoded and validated token payload

        Returns:
            User info dict with keys: sub, is_m2m, permissions, email, name
        """

    # Token extraction and validation helpers

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if request path is a public endpoint.

        Args:
            path: Request path (e.g., "/agent.html")

        Returns:
            True if endpoint is public, False otherwise
        """
        public_endpoints = getattr(self.config, "public_endpoints", [])
        return any(fnmatch.fnmatch(path, pattern) for pattern in public_endpoints)

    def _extract_token(self, request: Request) -> str | None:
        """Extract Bearer token from Authorization header.

        Args:
            request: HTTP request

        Returns:
            Token string or None if not found
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]

        return None

    # Main middleware dispatch

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware.

        Flow:
        1. Check if endpoint is public
        2. Extract and validate token
        3. Extract user info and attach to request state
        4. Continue to next middleware/endpoint

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            Response from endpoint or error response
        """
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

        # Validate token
        try:
            token_payload = self._validate_token(token)
        except Exception as e:
            logger.warning(f"Token validation failed for {path}: {e}")
            return self._handle_validation_error(e, path)

        # Extract user info
        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            code, message = extract_error_fields(InvalidTokenError)
            return jsonrpc_error(code=code, message=message, status=401)

        # Attach context to request state
        self._attach_user_context(request, user_info, token_payload)

        logger.debug(
            f"Authenticated {path} - sub={user_info.get('sub')}, m2m={user_info.get('is_m2m', False)}"
        )

        return await call_next(request)

    # Error handling and utilities

    async def _auth_required_error(self, request: Request) -> JSONResponse:
        """Return authentication required error response.

        Args:
            request: HTTP request

        Returns:
            JSON-RPC error response
        """
        request_id = await self._extract_request_id(request)
        code, message = extract_error_fields(AuthenticationRequiredError)
        return jsonrpc_error(
            code=code, message=message, request_id=request_id, status=401
        )

    async def _extract_request_id(self, request: Request) -> Any:
        """Extract request ID from JSON-RPC request body.

        Args:
            request: HTTP request

        Returns:
            Request ID or None if not found
        """
        try:
            body = await request.body()
            if body:
                data = json.loads(body)
                return data.get("id")
        except Exception:
            return None

    def _attach_user_context(
        self, request: Request, user_info: dict[str, Any], token_payload: dict[str, Any]
    ) -> None:
        """Attach user context to request state.

        Args:
            request: HTTP request
            user_info: Extracted user information
            token_payload: Decoded token payload
        """
        request.state.user = user_info
        request.state.authenticated = True
        request.state.token_payload = token_payload

    def _handle_validation_error(self, error: Exception, path: str) -> JSONResponse:
        """Handle token validation errors with appropriate error responses.

        Args:
            error: Validation exception
            path: Request path

        Returns:
            JSON-RPC error response
        """
        error_str = str(error).lower()

        # Map error patterns to error types
        if "expired" in error_str:
            error_type = TokenExpiredError
        elif "signature" in error_str:
            error_type = InvalidTokenSignatureError
        else:
            error_type = InvalidTokenError

        code, message = extract_error_fields(error_type)

        # Include details for non-expired errors
        data = None if "expired" in error_str else f"Token validation failed: {error}"

        return jsonrpc_error(code=code, message=message, data=data, status=401)
