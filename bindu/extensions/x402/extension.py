"""Bindu x402 extension helpers.

Provides:
- AgentExtension declaration for agent card capabilities
- HTTP activation header utilities per A2A extensions mechanism
"""

from __future__ import annotations

from typing import Optional

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import AgentExtension

from .constants import X402_EXTENSION_URI


def get_agent_extension(required: bool = False, description: Optional[str] = None) -> AgentExtension:
    """Create an AgentExtension declaration for x402.

    Args:
        required: Whether clients must support the extension
        description: Optional description override

    Returns:
        AgentExtension dict for capabilities.extensions
    """
    return AgentExtension(
        uri=X402_EXTENSION_URI,
        description=description or "Supports x402 A2A agent payments",
        required=required,
        params={},
    )


def is_activation_requested(request: Request) -> bool:
    """Check if the client requested x402 extension activation via header."""
    exts = request.headers.get("X-A2A-Extensions", "")
    return X402_EXTENSION_URI in exts


def add_activation_header(response: Response) -> Response:
    """Echo the x402 extension URI in response header to confirm activation."""
    response.headers["X-A2A-Extensions"] = X402_EXTENSION_URI
    return response
