"""Auth0 authentication middleware for Bindu server.

This middleware validates JWT tokens from Auth0 for M2M and user authentication.
It intercepts all requests, validates tokens, and attaches user context to requests.
"""

import fnmatch
from typing import Callable

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.settings import AuthSettings
from bindu.utils.auth_utils import JWTValidator, extract_bearer_token
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.auth")


class Auth0Middleware(BaseHTTPMiddleware):
    """Middleware for Auth0 JWT token validation.
    
    This middleware:
    1. Checks if the endpoint is public (no auth required)
    2. Extracts JWT token from Authorization header
    3. Validates token signature and claims using Auth0 JWKS
    4. Checks permissions if required
    5. Attaches user/service info to request.state
    6. Returns 401/403 errors for invalid/unauthorized requests
    """

    def __init__(self, app: Callable, auth_config: AuthSettings):
        """Initialize Auth0 middleware.
        
        Args:
            app: ASGI application
            auth_config: Authentication configuration settings
        """
        super().__init__(app)
        self.config = auth_config
        self.validator = JWTValidator(auth_config)
        
        logger.info(
            f"Auth0 middleware initialized. Domain: {auth_config.domain}, "
            f"Audience: {auth_config.audience}"
        )

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if the request path is a public endpoint.
        
        Args:
            path: Request path (e.g., "/agent.html")
            
        Returns:
            True if endpoint is public, False if authentication required
        """
        for pattern in self.config.public_endpoints:
            if fnmatch.fnmatch(path, pattern):
                return True
        return False

    def _create_error_response(
        self,
        code: int,
        message: str,
        data: dict | None = None,
        status_code: int = 401
    ) -> JSONResponse:
        """Create JSON-RPC error response.
        
        Args:
            code: JSON-RPC error code
            message: Error message
            data: Additional error data
            status_code: HTTP status code
            
        Returns:
            JSONResponse with error details
        """
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message,
            },
            "id": None,
        }
        
        if data:
            error_response["error"]["data"] = data
        
        return JSONResponse(content=error_response, status_code=status_code)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware.
        
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
        
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        token = extract_bearer_token(auth_header)
        
        if not token:
            logger.warning(f"Authentication required for {path} - No token provided")
            return self._create_error_response(
                code=-32001,
                message="Authentication required",
                data={
                    "reason": "Missing Authorization header",
                    "expected_format": "Authorization: Bearer <token>",
                },
                status_code=401
            )
        
        # Validate JWT token
        try:
            payload = self.validator.validate_token(token)
        except jwt.ExpiredSignatureError:
            logger.warning(f"Authentication failed for {path} - Token expired")
            return self._create_error_response(
                code=-32004,
                message="Token has expired",
                data={"reason": "Token expiration time (exp) has passed"},
                status_code=401
            )
        except jwt.InvalidAudienceError:
            logger.warning(f"Authentication failed for {path} - Invalid audience")
            return self._create_error_response(
                code=-32002,
                message="Invalid token",
                data={
                    "reason": f"Token audience does not match (expected: {self.config.audience})"
                },
                status_code=401
            )
        except jwt.InvalidIssuerError:
            logger.warning(f"Authentication failed for {path} - Invalid issuer")
            return self._create_error_response(
                code=-32002,
                message="Invalid token",
                data={
                    "reason": f"Token issuer does not match (expected: {self.config.issuer})"
                },
                status_code=401
            )
        except jwt.InvalidSignatureError:
            logger.warning(f"Authentication failed for {path} - Invalid signature")
            return self._create_error_response(
                code=-32002,
                message="Invalid token signature",
                data={"reason": "Token signature verification failed"},
                status_code=401
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Authentication failed for {path} - Invalid token: {e}")
            return self._create_error_response(
                code=-32002,
                message="Invalid token",
                data={"reason": str(e)},
                status_code=401
            )
        except Exception as e:
            logger.error(f"Authentication error for {path}: {e}", exc_info=True)
            return self._create_error_response(
                code=-32603,
                message="Internal authentication error",
                data={"reason": str(e)},
                status_code=500
            )
        
        # Extract user/service information
        user_info = self.validator.extract_user_info(payload)
        
        # Check permissions if required (for JSON-RPC methods)
        if self.config.require_permissions and path == "/":
            # We'll check permissions in the endpoint based on the method
            # Store payload for later permission checking
            request.state.token_payload = payload
        
        # Attach user info to request state
        request.state.user = user_info
        request.state.authenticated = True
        
        logger.debug(
            f"Request authenticated: {path} - "
            f"Subject: {user_info['sub']}, M2M: {user_info['is_m2m']}"
        )
        
        # Continue to next middleware/endpoint
        return await call_next(request)
