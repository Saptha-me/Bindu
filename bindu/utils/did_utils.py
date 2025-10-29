"""DID utilities for DID extension management and validation."""

from __future__ import annotations

from typing import Any


def validate_did_extension(
    did_extension: Any | None, required_attr: str
) -> tuple[bool, str | None]:
    """Validate DID extension has required attribute.

    Args:
        did_extension: DID extension object to validate
        required_attr: Required attribute name (e.g., 'did', 'get_agent_info')

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not did_extension:
        return False, "DID extension not configured"

    if not hasattr(did_extension, required_attr):
        return False, f"DID extension missing '{required_attr}' attribute"

    return True, None


def check_did_match(did_extension: Any, requested_did: str) -> bool:
    """Check if requested DID matches the extension's DID.

    Args:
        did_extension: DID extension object (must have 'did' attribute)
        requested_did: DID string to match

    Returns:
        True if DIDs match, False otherwise

    Note:
        Assumes did_extension has been validated with validate_did_extension() first
    """
    return did_extension.did == requested_did
