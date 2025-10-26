"""Endpoint utilities for common HTTP patterns."""

from functools import wraps
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import InternalError
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error

logger = get_logger("bindu.utils.endpoint_utils")


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
