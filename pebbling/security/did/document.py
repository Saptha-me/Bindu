#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""DID (Decentralized Identifier) document handling for Pebbling.

This module provides classes and functions for creating, managing, and
validating DID documents used for agent identity verification in the
Pebbling framework.
"""

from typing import Any, Dict

import orjson


def create_did_document(
    did: str,
    public_key_pem: str,
) -> Dict[str, Any]:
    """Create a DID document from a public key.

    Args:
        did: The DID to use
        public_key_pem: Public key in PEM format

    Returns:
        DID document as dictionary
    """
    did_document = {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "verificationMethod": [
            {"id": f"{did}#keys-1", "type": "RsaVerificationKey2018", "controller": did, "publicKeyPem": public_key_pem}
        ],
        "authentication": [f"{did}#keys-1"],
        "service": [{"id": f"{did}#agent", "type": "PebbleAgentCard", "serviceEndpoint": "http://localhost:8000"}],
    }

    return did_document


def update_service_endpoint(did_document: Dict[str, Any], endpoint: str) -> Dict[str, Any]:
    """Update the service endpoint in a DID document.

    Args:
        did_document: The DID document to update
        endpoint: The new service endpoint

    Returns:
        Updated DID document
    """
    for service in did_document.get("service", []):
        if service["type"] == "PebbleAgentCard":
            service["serviceEndpoint"] = endpoint

    return did_document


def validate_did_document(did_document: Dict[str, Any]) -> bool:
    """Validate a DID document.

    Args:
        did_document: The DID document to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["@context", "id", "verificationMethod"]
    for field in required_fields:
        if field not in did_document:
            return False

    return True


def import_did_document(did_document_data, validate=True):
    """Import a DID document, optionally validating its structure.

    Args:
        did_document_data: DID document as string or dictionary
        validate: Whether to validate the document structure

    Returns:
        DID document as dictionary

    Raises:
        ValueError: If the document is invalid and validate=True
    """
    if isinstance(did_document_data, str):
        did_document = orjson.loads(did_document_data)
    else:
        did_document = did_document_data

    if validate and not validate_did_document(did_document):
        raise ValueError("Invalid DID document: missing required fields")

    return did_document


def export_did_document(did_document: Dict[str, Any], file_path=None) -> str:
    """Export a DID document to a file or as a string.

    Args:
        did_document: The DID document to export
        file_path: Optional path to save the document to

    Returns:
        DID document as JSON string
    """
    did_doc_str = orjson.dumps(did_document, indent=2)
    if file_path:
        with open(file_path, "w") as file:
            file.write(did_doc_str)

    return did_doc_str
