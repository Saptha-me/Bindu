"""Common request utilities for endpoint handlers."""

from __future__ import annotations

from typing import Any, Tuple, Type, get_args

from starlette.requests import Request
from starlette.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.

    Args:
        request: Starlette request object

    Returns:
        Client IP address or "unknown" if not available
    """
    return request.client.host if request.client else "unknown"


def extract_error_fields(err_alias: Type[Any]) -> Tuple[int, str]:
    """Extract error code and message from JSONRPCError type alias.

    Given a JSONRPCError[Literal[code], Literal[message]] typing alias,
    return (code, message) as runtime values.
    """
    code_lit, msg_lit = get_args(err_alias)
    (code,) = get_args(code_lit)
    (msg,) = get_args(msg_lit)
    return int(code), str(msg)


def jsonrpc_error(
    code: int,
    message: str,
    data: str | None = None,
    request_id: str | None = None,
    status: int = 400,
) -> JSONResponse:
    """Create a JSON-RPC error response.

    Args:
        code: JSON-RPC error code
        message: Error message
        data: Optional additional error data
        request_id: Optional JSON-RPC request ID
        status: HTTP status code (default: 400)

    Returns:
        JSONResponse with JSON-RPC error format
    """
    error_dict: dict[str, Any] = {"code": code, "message": message}
    if data:
        error_dict["data"] = data

    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "error": error_dict,
            "id": request_id,
        },
        status_code=status,
    )
