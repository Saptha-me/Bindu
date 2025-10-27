"""Coinbase CDP API utilities for JWT authentication."""

import os
from typing import Optional

from coinbase import jwt_generator


def generate_coinbase_jwt(
    request_method: Optional[str] = None,
    request_host: Optional[str] = None,
    request_path: Optional[str] = None,
) -> str:
    """Generate JWT token for Coinbase CDP API authentication.
    
    Args:
        request_method: HTTP method (e.g., "GET", "POST")
        request_host: API host (e.g., "api.cdp.coinbase.com")
        request_path: API path (e.g., "/platform/v2/evm/token-balances/...")
        
    Returns:
        JWT token string
        
    Raises:
        ValueError: If required credentials or request details are missing
        
    Example:
        >>> token = generate_coinbase_jwt(
        ...     request_method="GET",
        ...     request_host="api.cdp.coinbase.com",
        ...     request_path="/platform/v2/evm/token-balances/base-sepolia/0x..."
        ... )
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
    
    # Format the JWT URI for REST API
    jwt_uri = jwt_generator.format_jwt_uri(request_method, request_path)
    
    # Build the JWT token
    jwt_token = jwt_generator.build_rest_jwt(jwt_uri, key_name, key_secret)
    
    return jwt_token