"""Common request utilities for endpoint handlers."""

from __future__ import annotations

from starlette.requests import Request
from typing import Any, Tuple, get_args


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.
    
    Args:
        request: Starlette request object
        
    Returns:
        Client IP address or "unknown" if not available
    """
    return request.client.host if request.client else "unknown"


def extract_error_fields(err_alias: Any) -> Tuple[int, str]:
    """
    Given a JSONRPCError[Literal[code], Literal[message]] typing alias,
    return (code, message) as runtime values.
    """
    code_lit, msg_lit = get_args(err_alias)           
    (code,) = get_args(code_lit)                      
    (message,) = get_args(msg_lit)                    
    return int(code), str(message)
