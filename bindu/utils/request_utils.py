"""Common request utilities for endpoint handlers."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Tuple, Type, get_args

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import InternalError
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.request_utils")


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
    request_id: Any = None,
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
            "id": str(request_id) if request_id is not None else None,
        },
        status_code=status,
    )


def handle_endpoint_errors(endpoint_name: str) -> Callable:
    """Decorate endpoint to handle common errors.

    Args:
        endpoint_name: Name of the endpoint for logging (e.g., "agent card", "skills list")

    Returns:
        Decorated endpoint function with error handling

    Example:
        @handle_endpoint_errors("agent card")
        async def agent_card_endpoint(app, request):
            # Your endpoint logic here
            return response
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Response:
            # Extract request from args/kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]

            client_ip = get_client_ip(request) if request else "unknown"

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error serving {endpoint_name} to {client_ip}: {e}", exc_info=True
                )
                code, message = extract_error_fields(InternalError)
                return jsonrpc_error(code, message, str(e), status=500)

        return wrapper

    return decorator
