"""
Authentication utilities for the Pebble framework.

This module provides utilities for API authentication and authorization.
"""

from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from pebble.security.keys import validate_api_key

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_token(
    api_key: str = Security(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> str:
    """Extract and validate the authentication token from various sources.
    
    Args:
        api_key: API key from the X-API-Key header
        credentials: Bearer token credentials
        
    Returns:
        str: The validated token
        
    Raises:
        HTTPException: If the token is invalid or missing
    """
    if api_key:
        token = api_key
    elif credentials:
        token = credentials.credentials
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not validate_api_key(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return token
