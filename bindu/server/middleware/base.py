"""Base authentication middleware interface for Bindu server.

This module provides an abstract base class for authentication middleware,
allowing support for multiple authentication providers (Auth0, AWS Cognito, Azure AD, etc.).
"""

from __future__ import annotations as _annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import (
    AuthenticationRequiredError,
    InvalidTokenError,
    InvalidTokenSignatureError,
    TokenExpiredError,
)
from bindu.utils.request_utils import extract_error_fields
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.base")


class AuthMiddleware(BaseHTTPMiddleware, ABC):
    """Abstract authentication middleware interface.
    
    Responsibilities:
    - Token Extraction: Extract authentication tokens from requests
    - Token Validation: Validate tokens using provider-specific logic
    - User Context: Extract and attach user/service information to requests
    - Error Handling: Return standardized JSON-RPC error responses
    
    This class defines the interface that all authentication providers must implement.
    Subclasses should implement token validation logic specific to their provider.
    
    Supported providers:
    - Auth0 (Auth0Middleware)
    - AWS Cognito (CognitoMiddleware) - Future
    - Azure AD (AzureADMiddleware) - Future
    - Custom JWT (CustomJWTMiddleware) - Future
    """

    def __init__(self, app: Callable, auth_config: Any):
        """Initialize authentication middleware.
        
        Args:
            app: ASGI application
            auth_config: Provider-specific authentication configuration
        """
        super().__init__(app)
        self.config = auth_config
        self._initialize_provider()
    
    # -------------------------------------------------------------------------
    # Provider Initialization
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def _initialize_provider(self) -> None:
        """Initialize provider-specific components.
        
        This method should set up any provider-specific clients, validators,
        or configuration needed for token validation.
        
        Example:
            - Auth0: Initialize JWKS client
            - AWS Cognito: Initialize Cognito client
            - Azure AD: Initialize MSAL client
        """
    
    # -------------------------------------------------------------------------
    # Token Validation (Provider-Specific)
    # -------------------------------------------------------------------------
    
    @abstractmethod
    def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate authentication token.
        
        Args:
            token: Authentication token (JWT, opaque token, etc.)
            
        Returns:
            Decoded token payload with user/service information
            
        Raises:
            Exception: If token is invalid, expired, or verification fails
            
        Note:
            Implementation should validate:
            - Token signature
            - Token expiration
            - Token issuer
            - Token audience
            - Any provider-specific claims
        """
    
    @abstractmethod
    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Extract user/service information from validated token.
        
        Args:
            token_payload: Decoded and validated token payload
            
        Returns:
            Dictionary with standardized user information:
            {
                "sub": "user_id or service_id",
                "is_m2m": bool,  # True for service accounts
                "permissions": [...],
                "email": "...",  # Optional, for user tokens
                "name": "...",   # Optional
                ... provider-specific fields
            }
        """
    
    # -------------------------------------------------------------------------
    # Token Extraction (Common Logic)
    # -------------------------------------------------------------------------
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the request path is a public endpoint.
        
        Args:
            path: Request path (e.g., "/agent.html")
            
        Returns:
            True if endpoint is public, False if authentication required
            
        Note:
            Default implementation checks against config.public_endpoints.
            Override if provider needs custom logic.
        """
        import fnmatch
        
        public_endpoints = getattr(self.config, 'public_endpoints', [])
        for pattern in public_endpoints:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract authentication token from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Token string or None if not found
            
        Note:
            Default implementation extracts from Authorization header.
            Override if provider uses different token location (cookie, query param, etc.).
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        
        return parts[1]

    
    # -------------------------------------------------------------------------
    # Main Middleware Dispatch
    # -------------------------------------------------------------------------
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware.
        
        This is the main middleware entry point. It orchestrates the authentication flow:
        1. Check if endpoint is public
        2. Extract token from request
        3. Validate token (provider-specific)
        4. Extract user info (provider-specific)
        5. Attach user context to request
        6. Continue to next middleware/endpoint
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response from endpoint or error response
        """
        path = request.url.path
        
        # Skip authentication for public endpoints
        if self._is_public_endpoint(path):
            logger.debug(f"Public endpoint accessed: {path}")
            return await call_next(request)
        
        # Extract token from request
        token = self._extract_token(request)
        
        if not token:
            logger.warning(f"Authentication required for {path} - No token provided")
            # Extract request ID for proper JSON-RPC error response
            request_id = await self._extract_request_id(request)
            AUTH_REQUIRED_CODE, AUTH_REQUIRED_MSG = extract_error_fields(AuthenticationRequiredError)
            return self._create_error_response(
                code=AUTH_REQUIRED_CODE,
                message=AUTH_REQUIRED_MSG,
                request_id=request_id
            )
        
        # Validate token (provider-specific implementation)
        try:
            token_payload = self._validate_token(token)
        except Exception as e:
            # Provider-specific exceptions will be caught here
            logger.warning(f"Authentication failed for {path}: {e}")
            return self._handle_validation_error(e, path)
        
        # Extract user/service information (provider-specific)
        try:
            user_info = self._extract_user_info(token_payload)
        except Exception as e:
            logger.error(f"Failed to extract user info for {path}: {e}")
            code, message = extract_error_fields(InvalidTokenError)
            return self._create_error_response(code=code, message=message)
        
        # Attach user info to request state
        request.state.user = user_info
        request.state.authenticated = True
        request.state.token_payload = token_payload
        
        logger.debug(
            f"Request authenticated: {path} - "
            f"Subject: {user_info.get('sub')}, M2M: {user_info.get('is_m2m', False)}"
        )
        
        # Continue to next middleware/endpoint
        return await call_next(request)
    
    # -------------------------------------------------------------------------
    # Error Handling (Provider-Specific)
    # -------------------------------------------------------------------------
    
    async def _extract_request_id(self, request: Request) -> Any:
        """Extract request ID from JSON-RPC request body.
        
        Args:
            request: HTTP request
            
        Returns:
            Request ID or None if not found/parseable
        """
        try:
            body = await request.body()
            if body:
                import json
                data = json.loads(body)
                return data.get("id")
        except Exception:
            pass
        return None
    
    def _create_error_response(
        self, code: int, message: str, data: str | None = None, status: int = 401, request_id: Any = None
    ) -> JSONResponse:
        """Create a JSON-RPC error response.
        
        Args:
            code: JSON-RPC error code (from protocol specification)
            message: Error message (from protocol specification)
            data: Optional additional error data
            status: HTTP status code (default: 401)
            request_id: Optional JSON-RPC request ID
            
        Returns:
            JSONResponse with JSON-RPC error format
        """
        error_dict: dict[str, Any] = {"code": code, "message": message}
        if data:
            error_dict["data"] = data
        
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "error": error_dict,
                "id": request_id,
            },
            status_code=status,
        )
    
    def _handle_validation_error(self, error: Exception, path: str) -> JSONResponse:
        """Handle token validation errors.
        
        Args:
            error: Validation exception
            path: Request path
            
        Returns:
            Appropriate error response
            
        Note:
            Override this method if provider has specific error types.
        """
        # Default error handling
        error_str = str(error)
        
        # Common error patterns
        if "expired" in error_str.lower():
            code, message = extract_error_fields(TokenExpiredError)
            return self._create_error_response(code=code, message=message)
        elif "signature" in error_str.lower():
            code, message = extract_error_fields(InvalidTokenSignatureError)
            return self._create_error_response(code=code, message=message)
        elif "audience" in error_str.lower() or "issuer" in error_str.lower():
            code, message = extract_error_fields(InvalidTokenError)
            return self._create_error_response(
                code=code,
                message=message,
                data=f"Token validation failed: {error_str}"
            )
        else:
            code, message = extract_error_fields(InvalidTokenError)
            return self._create_error_response(
                code=code,
                message=message,
                data=f"Token validation failed: {error_str}"
            )
