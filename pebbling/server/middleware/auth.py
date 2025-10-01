"""Authentication Middleware for Pebbling Server.

This middleware handles JWT token verification for incoming requests,
supporting multiple identity providers through JWKS integration.
"""

from typing import Optional, Set
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from pebbling.security.jwt import JWTVerifier
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.server.middleware.auth")


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Starlette middleware for JWT authentication.

    This middleware:
    1. Extracts JWT tokens from Authorization header (Bearer tokens)
    2. Verifies token signature and claims
    3. Attaches verified token payload to request.state
    4. Returns 401 Unauthorized for invalid tokens
    5. Allows anonymous access to specified public paths
    """

    def __init__(
        self,
        app: ASGIApp,
        jwt_verifier: JWTVerifier,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        algorithms: Optional[list[str]] = None,
        secret: Optional[str] = None,
        verify_signature: bool = True,
        allow_anonymous: bool = False,
        public_paths: Optional[Set[str]] = None,
    ):
        """Initialize authentication middleware.

        Args:
            app: ASGI application
            jwt_verifier: JWT verifier instance
            issuer: Expected token issuer
            audience: Expected token audience
            algorithms: Allowed algorithms (default: ["RS256", "ES256", "HS256"])
            secret: Shared secret for HMAC algorithms
            verify_signature: Whether to verify token signature
            allow_anonymous: Allow requests without tokens
            public_paths: Set of paths that don't require authentication
        """
        super().__init__(app)
        self.jwt_verifier = jwt_verifier
        self.issuer = issuer
        self.audience = audience
        self.algorithms = algorithms or ["RS256", "ES256", "HS256"]
        self.secret = secret
        self.verify_signature = verify_signature
        self.allow_anonymous = allow_anonymous

        # Default public paths
        self.public_paths = public_paths or {
            "/.well-known/agent.json",
            "/docs",
            "/docs.html",
            "/agent.html",
            "/chat.html",
            "/storage.html",
            "/common.js",
            "/common.css",
            "/components/layout.js",
            "/components/header.html",
            "/components/footer.html",
        }

        logger.info(
            f"Authentication middleware initialized (anonymous_allowed={allow_anonymous}, "
            f"public_paths={len(self.public_paths)})"
        )

    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from Authorization header.

        Args:
            request: Starlette request

        Returns:
            Token string if found, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        # Check for Bearer token
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (doesn't require authentication).

        Args:
            path: Request path

        Returns:
            True if path is public
        """
        return path in self.public_paths

    def _create_error_response(self, message: str, status_code: int = 401) -> JSONResponse:
        """Create JSON error response.

        Args:
            message: Error message
            status_code: HTTP status code

        Returns:
            JSON response
        """
        return JSONResponse(
            status_code=status_code,
            content={
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": message},
                "id": None,
            },
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through authentication middleware.

        Args:
            request: Starlette request
            call_next: Next middleware/endpoint

        Returns:
            Response from next middleware or error response
        """
        # Check if path is public
        if self._is_public_path(request.url.path):
            logger.debug(f"Public path accessed: {request.url.path}")
            return await call_next(request)

        # Extract token
        token = self._extract_token(request)

        if not token:
            if self.allow_anonymous:
                logger.debug("No token provided, allowing anonymous access")
                request.state.authenticated = False
                request.state.token_payload = None
                return await call_next(request)
            else:
                logger.warning(f"No token provided for protected path: {request.url.path}")
                return self._create_error_response(
                    "Authentication required: Missing or invalid Authorization header"
                )

        # Verify token
        try:
            payload = self.jwt_verifier.verify_token(
                token=token,
                secret=self.secret,
                algorithms=self.algorithms,
                issuer=self.issuer,
                audience=self.audience,
                verify_signature=self.verify_signature,
            )

            # Attach verified payload to request state
            request.state.authenticated = True
            request.state.token_payload = payload

            logger.debug(f"Authenticated request for subject: {payload.get('sub', 'unknown')}")

            # Proceed to next middleware/endpoint
            return await call_next(request)

        except ExpiredSignatureError:
            logger.warning("Token expired")
            return self._create_error_response("Authentication failed: Token expired", status_code=401)

        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return self._create_error_response(f"Authentication failed: {str(e)}", status_code=401)

        except Exception as e:
            logger.error(f"Unexpected error during authentication: {e}")
            return self._create_error_response(
                "Authentication failed: Internal error", status_code=500
            )
