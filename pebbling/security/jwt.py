"""JWT Token Verification using PyJWT for Pebbling Authentication.

This module provides JWT token verification capabilities with support
for multiple identity providers through JWKS (JSON Web Key Set) integration.
"""

from typing import Any, Dict, Optional
import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
)

from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.security.jwt")


class JWTVerifier:
    """JWT token verification with JWKS support using PyJWT."""

    def __init__(
        self,
        jwks_url: Optional[str] = None,
        jwks_cache_ttl: int = 3600,
        jwks_max_cached_keys: int = 16,
    ):
        """Initialize JWT verifier.

        Args:
            jwks_url: JWKS URL for fetching public keys (for RS*/ES* algorithms)
            jwks_cache_ttl: JWKS cache time-to-live in seconds (default: 1 hour)
            jwks_max_cached_keys: Maximum number of keys to cache (default: 16)
        """
        self.jwks_url = jwks_url
        self.jwks_client = None

        if jwks_url:
            self.jwks_client = PyJWKClient(
                jwks_url,
                cache_keys=True,
                max_cached_keys=jwks_max_cached_keys,
                cache_jwk_set_ttl=jwks_cache_ttl,
            )
            logger.info(f"Initialized JWKS client for {jwks_url}")

    def verify_token(
        self,
        token: str,
        secret: Optional[str] = None,
        algorithms: Optional[list[str]] = None,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        verify_signature: bool = True,
        verify_exp: bool = True,
        leeway: int = 60,
    ) -> Dict[str, Any]:
        """Verify JWT token and return payload.

        Args:
            token: JWT token string
            secret: Shared secret for HMAC algorithms (HS256, HS384, HS512)
            algorithms: Allowed algorithms (default: ["RS256", "ES256", "HS256"])
            issuer: Expected issuer (validates 'iss' claim if provided)
            audience: Expected audience (validates 'aud' claim if provided)
            verify_signature: Whether to verify signature
            verify_exp: Whether to verify expiration
            leeway: Leeway in seconds for time-based claims

        Returns:
            Verified JWT payload

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token is expired
            InvalidAudienceError: If audience doesn't match
            InvalidIssuerError: If issuer doesn't match
            InvalidSignatureError: If signature verification fails
        """
        if algorithms is None:
            algorithms = ["RS256", "ES256", "HS256"]

        # Determine verification key
        key = None
        if any(alg.startswith(("RS", "ES")) for alg in algorithms):
            # Public key algorithms - use JWKS
            if not self.jwks_client:
                raise ValueError("JWKS URL not configured for public key algorithms")

            # Get signing key from JWKS
            try:
                signing_key = self.jwks_client.get_signing_key_from_jwt(token)
                key = signing_key.key
            except Exception as e:
                logger.error(f"Failed to get signing key from JWKS: {e}")
                raise InvalidTokenError(f"Failed to get signing key: {e}")

        elif any(alg.startswith("HS") for alg in algorithms):
            # HMAC algorithms - use shared secret
            if not secret:
                raise ValueError("Shared secret required for HMAC algorithms")
            key = secret

        else:
            raise ValueError(f"No supported algorithms specified: {algorithms}")

        # Build verification options
        options = {
            "verify_signature": verify_signature,
            "verify_exp": verify_exp,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_aud": audience is not None,
            "require_exp": False,  # Don't require exp claim
            "require_iat": False,  # Don't require iat claim
            "require_nbf": False,  # Don't require nbf claim
        }

        # Decode and verify token
        try:
            payload = jwt.decode(
                token,
                key=key,
                algorithms=algorithms,
                issuer=issuer,
                audience=audience,
                options=options,
                leeway=leeway,
            )

            logger.info(f"Successfully verified JWT token for subject: {payload.get('sub', 'unknown')}")
            return payload

        except ExpiredSignatureError as e:
            logger.warning(f"Token expired: {e}")
            raise
        except InvalidAudienceError as e:
            logger.warning(f"Invalid audience: {e}")
            raise
        except InvalidIssuerError as e:
            logger.warning(f"Invalid issuer: {e}")
            raise
        except InvalidSignatureError as e:
            logger.warning(f"Invalid signature: {e}")
            raise
        except DecodeError as e:
            logger.error(f"Failed to decode token: {e}")
            raise InvalidTokenError(f"Failed to decode token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            raise InvalidTokenError(f"Unexpected error: {e}")

    def decode_token_unverified(self, token: str) -> Dict[str, Any]:
        """Decode JWT token without verification (for inspection only).

        Args:
            token: JWT token string

        Returns:
            JWT payload (unverified)

        Raises:
            InvalidTokenError: If token cannot be decoded
        """
        try:
            # Decode without verification
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"Failed to decode token: {e}")
            raise InvalidTokenError(f"Failed to decode token: {e}")

    def get_token_header(self, token: str) -> Dict[str, Any]:
        """Extract JWT header without verification.

        Args:
            token: JWT token string

        Returns:
            JWT header

        Raises:
            InvalidTokenError: If token cannot be decoded
        """
        try:
            header = jwt.get_unverified_header(token)
            return header
        except Exception as e:
            logger.error(f"Failed to get token header: {e}")
            raise InvalidTokenError(f"Failed to get token header: {e}")


def create_jwt_verifier(
    jwks_url: Optional[str] = None,
    jwks_cache_ttl: int = 3600,
) -> JWTVerifier:
    """Factory function to create JWT verifier.

    Args:
        jwks_url: JWKS URL for fetching public keys
        jwks_cache_ttl: JWKS cache time-to-live in seconds

    Returns:
        JWTVerifier instance
    """
    return JWTVerifier(jwks_url=jwks_url, jwks_cache_ttl=jwks_cache_ttl)
