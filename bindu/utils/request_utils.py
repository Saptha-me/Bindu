"""Common request utilities for endpoint handlers."""

from __future__ import annotations

from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.
    
    Args:
        request: Starlette request object
        
    Returns:
        Client IP address or "unknown" if not available
    """
    return request.client.host if request.client else "unknown"
