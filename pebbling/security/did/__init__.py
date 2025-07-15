"""
DID Manager Package for Pebbling.

This package provides DID (Decentralized Identifier) management functionality
for Pebbling agents, including key generation, DID document management,
and cryptographic operations.
"""

# Import main manager class
from pebbling.security.did.manager import DIDManager

# Import cryptographic operations
from pebbling.security.did.crypto_operation import (
    sign_message,
    verify_message
)

# Import document operations
from pebbling.security.did.document import (
    create_did_document,
    update_service_endpoint,
    import_did_document,
    export_did_document,
    validate_did_document
)

# Import key management operations
from pebbling.security.did.keys import (
    generate_rsa_key_pair,
    load_private_key
)

# Import decorators
from pebbling.security.did.decorators import (
    with_did
)

# Define public API
__all__ = [
    # Main class
    'DIDManager',
    
    # Cryptographic operations
    'sign_message',
    'verify_message',
    
    # Document operations
    'create_did_document',
    'update_service_endpoint',
    'import_did_document',
    'export_did_document',
    'validate_did_document',
    
    # Key operations
    'generate_rsa_key_pair',
    'load_private_key',
    
    # Decorators
    'with_did'
]
