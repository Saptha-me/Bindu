"""Auth0 authentication middleware for Bindu server.

This middleware validates JWT tokens from Auth0 for M2M and user authentication.
It inherits from AuthMiddleware and implements Auth0-specific token validation.
"""

from __future__ import annotations as _annotations

from typing import Any

from bindu.utils.auth_utils import JWTValidator
from bindu.utils.logging import get_logger

from .base import AuthMiddleware

logger = get_logger("bindu.server.middleware.auth0")


class Auth0Middleware(AuthMiddleware):
    """Auth0-specific authentication middleware.

    This middleware implements Auth0 JWT token validation using JWKS.
    It validates:
    - Token signature using Auth0 public keys
    - Token expiration (exp claim)
    - Token issuer (iss claim)
    - Token audience (aud claim)
    - Optional: Permissions/scopes

    Supports both M2M (client credentials) and user authentication flows.
    """

    def _initialize_provider(self) -> None:
        """Initialize Auth0-specific components.

        Sets up:
        - JWTValidator with JWKS client for signature verification
        - Auth0 domain and audience configuration
        """
        self.validator = JWTValidator(self.config)

        logger.info(
            f"Auth0 middleware initialized. Domain: {self.config.domain}, Audience: {self.config.audience}"
        )

    def _validate_token(self, token: str) -> dict[str, Any]:
        """Validate Auth0 JWT token.

        Args:
            token: JWT access token from Auth0

        Returns:
            Decoded token payload with claims
        """
        return self.validator.validate_token(token)

    def _extract_user_info(self, token_payload: dict[str, Any]) -> dict[str, Any]:
        """Extract user/service information from Auth0 token.

        Args:
            token_payload: Decoded and validated JWT payload

        Returns:
            Dictionary with standardized user information
        """
        return self.validator.extract_user_info(token_payload)
