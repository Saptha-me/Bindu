"""Authentication utilities for JWT validation and Auth0 integration.

This module provides utilities for validating JWT tokens from Auth0,
including JWKS fetching, token signature verification, and claims validation.
"""

import time
from typing import Any, Optional

import jwt
from jwt import PyJWKClient

from bindu.settings import AuthSettings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.auth_utils")


class JWKSCache:
    """Simple in-memory cache for JWKS to reduce Auth0 API calls."""

    def __init__(self, ttl: int = 3600):
        """Initialize JWKS cache.

        Args:
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        self.ttl = ttl
        self._cache: dict[str, Any] = {}
        self._cache_time: float = 0

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if time.time() - self._cache_time > self.ttl:
            self._cache.clear()
            return None
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set cached value with current timestamp."""
        self._cache[key] = value
        self._cache_time = time.time()


class JWTValidator:
    """JWT token validation for Auth0 M2M authentication."""

    def __init__(self, auth_config: AuthSettings):
        """Initialize JWT validator with Auth0 configuration.

        Args:
            auth_config: Authentication settings from configuration
        """
        self.config = auth_config
        self.jwks_cache = JWKSCache(ttl=auth_config.jwks_cache_ttl)

        # Build JWKS URI if not provided
        if not self.config.jwks_uri and self.config.domain:
            self.config.jwks_uri = f"https://{self.config.domain}/.well-known/jwks.json"

        # Build issuer if not provided
        if not self.config.issuer and self.config.domain:
            self.config.issuer = f"https://{self.config.domain}/"

        # Initialize PyJWKClient for fetching signing keys
        self._jwks_client: Optional[PyJWKClient] = None
        if self.config.jwks_uri:
            self._jwks_client = PyJWKClient(
                self.config.jwks_uri, cache_keys=True, max_cached_keys=16
            )

    def validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token and return decoded payload.

        Args:
            token: JWT access token from Authorization header

        Returns:
            Decoded token payload with claims

        Raises:
            jwt.InvalidTokenError: If token is invalid, expired, or signature fails
            ValueError: If configuration is invalid
        """
        if not self._jwks_client:
            raise ValueError("JWKS client not initialized. Check auth configuration.")

        try:
            # Get signing key from JWKS
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=self.config.algorithms,
                audience=self.config.audience,
                issuer=self.config.issuer,
                leeway=self.config.leeway,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            logger.debug(
                f"Token validated successfully for subject: {payload.get('sub')}"
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: Token has expired")
            raise
        except jwt.InvalidAudienceError:
            logger.warning(
                f"Token validation failed: Invalid audience (expected: {self.config.audience})"
            )
            raise
        except jwt.InvalidIssuerError:
            logger.warning(
                f"Token validation failed: Invalid issuer (expected: {self.config.issuer})"
            )
            raise
        except jwt.InvalidSignatureError:
            logger.warning("Token validation failed: Invalid signature")
            raise
        except jwt.DecodeError as e:
            logger.warning(f"Token validation failed: Decode error - {e}")
            raise
        except Exception as e:
            logger.error(f"Token validation failed: Unexpected error - {e}")
            raise

    def check_permissions(
        self, payload: dict[str, Any], required_permissions: list[str]
    ) -> bool:
        """Check if token has required permissions.

        Args:
            payload: Decoded JWT payload
            required_permissions: List of required permission strings

        Returns:
            True if token has all required permissions, False otherwise
        """
        if not required_permissions:
            return True

        # Auth0 M2M tokens store permissions in 'permissions' or 'scope' claim
        token_permissions = payload.get("permissions", [])

        # Also check 'scope' claim (space-separated string)
        if not token_permissions and "scope" in payload:
            token_permissions = payload["scope"].split()

        # Check if all required permissions are present
        has_permissions = all(
            perm in token_permissions for perm in required_permissions
        )

        if not has_permissions:
            logger.warning(
                f"Permission check failed. Required: {required_permissions}, Token has: {token_permissions}"
            )

        return has_permissions

    def extract_user_info(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Extract user/service information from token payload.

        Args:
            payload: Decoded JWT payload

        Returns:
            Dictionary with user/service information
        """
        # M2M tokens have format: client_id@clients
        # User tokens have format: auth0|user_id or google-oauth2|user_id
        sub = payload.get("sub", "")

        is_m2m = sub.endswith("@clients")

        user_info = {
            "sub": sub,
            "is_m2m": is_m2m,
            "permissions": payload.get("permissions", []),
            "scope": payload.get("scope", ""),
            "azp": payload.get("azp"),  # Authorized party (client_id)
            "gty": payload.get("gty"),  # Grant type
        }

        # Add user-specific fields if present
        if not is_m2m:
            user_info.update(
                {
                    "email": payload.get("email"),
                    "email_verified": payload.get("email_verified"),
                    "name": payload.get("name"),
                    "nickname": payload.get("nickname"),
                    "picture": payload.get("picture"),
                }
            )
        else:
            # For M2M, extract client_id
            user_info["client_id"] = sub.replace("@clients", "")

        return user_info


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """Extract JWT token from Authorization header.

    Args:
        authorization_header: Authorization header value (e.g., "Bearer eyJ...")

    Returns:
        JWT token string or None if header is invalid
    """
    if not authorization_header:
        return None

    parts = authorization_header.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
