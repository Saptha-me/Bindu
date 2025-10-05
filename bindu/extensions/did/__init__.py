"""
DID (Decentralized Identifier) Extension for Pebbling Agents.

This module provides DID-based identity management for agents, including:
- Key generation and management (Ed25519)
- DID creation and resolution
- Digital signatures and verification
- W3C-compliant DID documents
- Validation utilities
"""

from __future__ import annotations

from pebbling.extensions.did.did_agent_extension import (
    DIDAgentExtension,
    DIDAgentExtensionMetadata,
)
from pebbling.extensions.did.validation import DIDValidation

__all__ = [
    "DIDAgentExtension",
    "DIDAgentExtensionMetadata",
    "DIDValidation",
]

__version__ = "1.0.0"
