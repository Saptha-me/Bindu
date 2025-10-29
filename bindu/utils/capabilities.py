"""Utilities for managing agent capabilities and extensions."""

from typing import Any, Dict, Optional

from bindu.common.protocol.types import AgentCapabilities


def add_extension_to_capabilities(
    capabilities: AgentCapabilities | Dict[str, Any] | None,
    extension: Any,
) -> AgentCapabilities:
    """Add an extension to agent capabilities.

    Args:
        capabilities: Existing capabilities (dict, AgentCapabilities object, or None)
        extension: Extension instance (X402AgentExtension or DIDAgentExtension)

    Returns:
        AgentCapabilities object with extension included

    """
    if capabilities is None:
        capabilities = {}

    extensions = capabilities.get("extensions", [])
    extensions.append(extension)
    return AgentCapabilities(extensions=extensions)


def get_x402_extension_from_capabilities(manifest: Any) -> Optional[Any]:
    """Extract X402 extension from manifest capabilities.

    Args:
        capabilities: Agent capabilities object with extensions

    Returns:
        X402AgentExtension instance if configured and required, None otherwise
    """
    from bindu.extensions.x402 import X402AgentExtension

    for ext in manifest.capabilities.get("extensions", []):
        # Check if it's already an X402AgentExtension instance
        if isinstance(ext, X402AgentExtension):
            return ext

    return None
