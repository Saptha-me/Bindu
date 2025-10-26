"""Utilities for managing agent capabilities and extensions."""

from typing import Any, Dict

from bindu.common.protocol.types import AgentCapabilities, AgentExtension


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