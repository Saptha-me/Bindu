"""Utilities for managing agent capabilities and extensions."""

from typing import Any, Dict, Optional

from bindu.common.protocol.types import AgentCapabilities, AgentExtension
from bindu.settings import app_settings


def add_extension_to_capabilities(
    capabilities: AgentCapabilities | Dict[str, Any] | None,
    extension: AgentExtension,
) -> AgentCapabilities:
    """Add an extension to agent capabilities.

    Args:
        capabilities: Existing capabilities (dict, AgentCapabilities object, or None)
        extension: AgentExtension dict to add

    Returns:
        AgentCapabilities object with extension included

    Example:
        >>> from bindu.extensions.did import DIDAgentExtension
        >>> did_ext = DIDAgentExtension(...)
        >>> capabilities = add_extension_to_capabilities(
        ...     capabilities=None,
        ...     extension=did_ext.agent_extension
        ... )
    """
    # Convert to dict if needed
    if capabilities is None:
        caps_dict: Dict[str, Any] = {}
    elif isinstance(capabilities, dict):
        caps_dict = capabilities.copy()
    else:
        # Convert AgentCapabilities to dict
        caps_dict = dict(capabilities)

    # Update extensions list
    extensions = caps_dict.get("extensions", [])
    caps_dict["extensions"] = [*extensions, extension]

    return AgentCapabilities(**caps_dict)


def get_x402_extension_from_capabilities(manifest: Any) -> Optional[Any]:
    """Extract X402 extension from manifest capabilities.

    Args:
        manifest: Agent manifest object with capabilities

    Returns:
        X402AgentExtension instance if configured and required, None otherwise

    Example:
        >>> x402_ext = get_x402_extension_from_capabilities(manifest)
        >>> if x402_ext:
        ...     payment_req = x402_ext.create_payment_requirements(...)
    """
    if not manifest or not hasattr(manifest, "capabilities"):
        return None

    capabilities = manifest.capabilities
    if not capabilities or "extensions" not in capabilities:
        return None

    for ext in capabilities.get("extensions", []):
        if ext.get("uri") == app_settings.x402.extension_uri and ext.get("required"):
            # Reconstruct X402AgentExtension from params
            from bindu.extensions.x402 import X402AgentExtension

            params = ext.get("params", {})
            return X402AgentExtension(
                amount=params.get("amount"),
                token=params.get("token", "USDC"),
                network=params.get("network", "base-sepolia"),
                pay_to_address=params.get("pay_to_address"),
                required=ext.get("required", True),
            )

    return None
