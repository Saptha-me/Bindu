"""
DID Manager Package for Pebbling.

This package provides DID (Decentralized Identifier) management functionality
for Pebbling agents, including key generation, DID document management,
and cryptographic operations.
"""

# Import main manager class
# Import document operations
from pebbling.security.did.document import (
    create_did_document,
    export_did_document,
    import_did_document,
    update_service_endpoint,
    validate_did_document,
)
from pebbling.security.did.manager import DIDManager

# Define public API
__all__ = [
    # Main class
    "DIDManager",
    # Document operations
    "create_did_document",
    "update_service_endpoint",
    "import_did_document",
    "export_did_document",
    "validate_did_document",
]
