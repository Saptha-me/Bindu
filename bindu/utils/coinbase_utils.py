"""Coinbase CDP API utilities for JWT authentication."""

import base64
import os
import time
import secrets
from typing import Optional, Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend
from x402.facilitator import FacilitatorClient


def generate_coinbase_jwt(
    request_method: Optional[str] = None,
    request_host: Optional[str] = None,
    request_path: Optional[str] = None,
) -> str:
    """Generate JWT token for Coinbase CDP API authentication.
    
    Matches the official Coinbase TypeScript SDK implementation.
    Supports Ed25519 (EdDSA) keys in base64 format (64 bytes: 32 seed + 32 public key).
    
    Args:
        request_method: HTTP method (e.g., "GET", "POST")
        request_host: API host (e.g., "api.cdp.coinbase.com")
        request_path: API path (e.g., "/platform/v2/x402/verify")
        
    Returns:
        JWT token string
        
    Raises:
        ValueError: If required credentials or request details are missing
        
    Environment Variables:
        KEY_NAME: Coinbase CDP API key name
        KEY_SECRET: Coinbase CDP API key secret (base64-encoded Ed25519 key, 64 bytes)
    """
    # Get credentials from environment variables
    key_name = os.getenv("KEY_NAME")
    key_secret = os.getenv("KEY_SECRET")
    
    if not key_name:
        raise ValueError(
            "API key name required. Set KEY_NAME environment variable. "
            "See: https://docs.cdp.coinbase.com/api-reference/v2/authentication"
        )
    
    if not key_secret:
        raise ValueError(
            "API key secret required. Set KEY_SECRET environment variable. "
            "See: https://docs.cdp.coinbase.com/api-reference/v2/authentication"
        )
    
    if not request_method or not request_host or not request_path:
        raise ValueError(
            "Request details required: request_method, request_host, and request_path must be provided"
        )
    
    # Decode the base64 Ed25519 key (64 bytes: 32 seed + 32 public key)
    decoded = base64.b64decode(key_secret)
    if len(decoded) != 64:
        raise ValueError(f"Invalid Ed25519 key length: expected 64 bytes, got {len(decoded)}")
    
    # Extract seed (first 32 bytes) to create Ed25519 private key
    seed = decoded[:32]
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    
    # Build the URI for the uris claim (note: array format)
    uri = f"{request_method} {request_host}{request_path}"
    
    # Get current timestamp
    now = int(time.time())
    
    # Build JWT payload matching TypeScript implementation
    jwt_payload = {
        'sub': key_name,
        'iss': "cdp",
        'nbf': now,
        'exp': now + 120,
        'iat': now,
        'aud': ["cdp_service"],
        'uris': [uri],  # Note: array format, not single string
    }
    
    # Generate random nonce (16 bytes = 32 hex chars)
    nonce = secrets.token_hex(16)
    
    # Encode JWT with EdDSA algorithm
    jwt_token = jwt.encode(
        jwt_payload,
        private_key,
        algorithm='EdDSA',
        headers={'kid': key_name, 'typ': 'JWT', 'nonce': nonce},
    )
    
    return jwt_token


class CoinbaseFacilitatorClient(FacilitatorClient):
    """Custom FacilitatorClient with Coinbase Bearer token authentication.
    
    This class extends the x402 FacilitatorClient to add Bearer token
    authentication required by Coinbase CDP API.
    """
    
    def __init__(self, manifest_coinbase_config: Optional[dict[str, Any]] = None):
        """Initialize CoinbaseFacilitatorClient.
        
        Args:
            manifest_coinbase_config: Dict with optional "host" key for API host.
                                     Defaults to "api.cdp.coinbase.com" if not provided.
                                     Example: {"host": "api.cdp.coinbase.com"}
        """
        self.manifest_coinbase_config = manifest_coinbase_config
        
        # Initialize parent with custom create_headers callback
        super().__init__(config={
            "url": "https://api.cdp.coinbase.com/platform/v2/x402",
            "create_headers": self._create_headers,
        })
    
    async def _create_headers(self) -> dict[str, dict[str, str]]:
        """Create authentication headers for verify and settle endpoints.
        
        Returns:
            Dictionary with keys "verify" and "settle", each containing headers
        """
        verify_headers = self._generate_auth_headers("/platform/v2/x402/verify")
        settle_headers = self._generate_auth_headers("/platform/v2/x402/settle")
        
        return {
            "verify": verify_headers,
            "settle": settle_headers,
        }
    
    def _generate_auth_headers(self, endpoint: str) -> dict[str, str]:
        """Generate authentication headers with JWT Bearer token.
        
        Args:
            endpoint: API endpoint (e.g., "/platform/v2/x402/verify" or "/platform/v2/x402/settle")
            
        Returns:
            Dictionary of headers including Authorization
        """
        # x402 verify and settle endpoints always use POST method
        request_method = "POST"
        
        if self.manifest_coinbase_config:
            # Config uses "host" key for the API host
            request_host = self.manifest_coinbase_config.get("host", "api.cdp.coinbase.com")
        else:
            # Fallback: use default Coinbase API host
            request_host = "api.cdp.coinbase.com"
        
        token = generate_coinbase_jwt(
            request_method=request_method,
            request_host=request_host,
            request_path=endpoint,
        )
        
        return {
            "Authorization": f"Bearer {token}",
        }