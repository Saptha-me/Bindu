import os
import orjson
import uuid
from typing import Dict, Any, Tuple, Optional

from pebbling.security.did.keys import generate_rsa_key_pair, load_private_key
from pebbling.security.did.document import (
    create_did_document, 
    update_service_endpoint,
    import_did_document,
    export_did_document
)
from pebbling.security.did.crypto_operation import sign_message, verify_message

class DIDManager:
    """DID manager for pebbling agents."""

    @staticmethod
    def get_or_create_did(key_path: str) -> Tuple[str, Dict[str, Any]]:
        """Get or create a DID for the agent.
        
        Args:
            key_path: Path to the private key file
            
        Returns:
            Tuple of (did, did_document)
        """
        # Check if the key file already exists
        if os.path.exists(key_path):
            key_data = orjson.loads(open(key_path, "rb").read())
            did = key_data["did"]
            did_document = key_data["didDocument"]
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            
            # Generate a new key pair
            _, private_key_pem, public_key_pem = generate_rsa_key_pair()
            
            # Create a DID
            did_uuid = str(uuid.uuid4())
            did = f"did:pebble:{did_uuid}"
            
            # Create a DID document
            did_document = create_did_document(did, public_key_pem)
            
            # Save the key pair and DID information
            with open(key_path, "wb") as f:
                f.write(orjson.dumps({
                    "privateKeyPem": private_key_pem,
                    "did": did,
                    "didDocument": did_document
                }))
    
        return did, did_document

    def __init__(self, key_path="pebble_private_key.json", endpoint=None):
        """Initialize the DID manager.
        
        Args:
            key_path: Path to the private key file
            endpoint: Optional service endpoint to update in the DID document
        """
        self.key_path = key_path
        self.did, self.did_document = self.get_or_create_did(key_path)
        
        # Update service endpoint if provided
        if endpoint:
            self.update_service_endpoint(endpoint)
        
        # Load the private key
        self.private_key_obj, self.private_key_pem = load_private_key(key_path)
        
        # If loading failed, generate a new key pair
        if self.private_key_obj is None:
            self.private_key_obj, self.private_key_pem, _ = generate_rsa_key_pair()
        
    def update_service_endpoint(self, endpoint):
        """Update the service endpoint in the DID document.
        
        Args:
            endpoint: The new service endpoint
        """
        self.did_document = update_service_endpoint(self.did_document, endpoint)

    def get_did(self) -> str:
        """Get the DID of the agent.
        
        Returns:
            The DID as a string
        """
        return self.did

    def get_did_document(self) -> Dict[str, Any]:
        """Get the DID document of the agent.
        
        Returns:
            The DID document as a dictionary
        """
        return self.did_document

    def get_private_key(self) -> str:
        """Get the private key of the agent as a PEM string.
        
        Returns:
            Private key in PEM format
        """
        return self.private_key_pem
    
    def get_private_key_object(self):
        """Get the private key object of the agent.
        
        Returns:
            The private key object
        """
        return self.private_key_obj

    async def sign_message(self, message):
        """Sign a message using the agent's private key.
        
        Args:
            message: The message to sign (string or dict)
            
        Returns:
            Base64-encoded signature
        """
        return await sign_message(self.private_key_obj, message)

    async def verify_message(self, message, signature, verification_method):
        """Verify a message signature using a verification method from a DID document.
        
        Args:
            message: The message that was signed (string or dict)
            signature: The base64-encoded signature
            verification_method: The verification method from a DID document
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        return await verify_message(message, signature, verification_method)

    def export_did_document(self, file_path=None):
        """Export the DID document to a file or return as string.
        
        Args:
            file_path: Optional path to save the document to
            
        Returns:
            DID document as JSON string
        """
        return export_did_document(self.did_document, file_path)

    def import_did_document(self, did_document, validate=True):
        """Import a DID document, optionally validating its structure.
        
        Args:
            did_document: DID document as string or dictionary
            validate: Whether to validate the document structure
            
        Returns:
            DID document as dictionary
        """
        return import_did_document(did_document, validate)