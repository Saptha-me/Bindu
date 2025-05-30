import asyncio
import json
import os
import uuid
from typing import Any, Dict, Optional, Tuple

import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Import didkit if available for future use
try:
    import didkit
    DIDKIT_AVAILABLE = True
except ImportError:
    DIDKIT_AVAILABLE = False
    print("didkit module not available, using built-in cryptography instead")

class DIDManager:
    """DID manager for pebbling agents."""

    @staticmethod
    async def get_or_create_did(key_path: str) -> Tuple[str, str, Dict[str, Any]]:
        """Get or create a DID for the agent.
        
        Args:
            key_path: Path to the private key file
            
        Returns:
            Tuple of (private_key, did, did_document)
        """
        # Check if the key file already exists
        if os.path.exists(key_path):
            with open(key_path, "r") as f:
                key_data = json.load(f)
            private_key = key_data["privateKeyBase58"]
            did = key_data["did"]
            did_document = key_data["didDocument"]
        else:
            # Generate a new key pair
            private_key_obj = ed25519.Ed25519PrivateKey.generate()
            
            # Get the private key in base58 format
            private_bytes = private_key_obj.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            private_key = base64.b64encode(private_bytes).decode('utf-8')
            
            # Get the public key in base58 format
            public_key_obj = private_key_obj.public_key()
            public_bytes = public_key_obj.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            public_key_base58 = base64.b64encode(public_bytes).decode('utf-8')
            
            # Create a DID
            did_uuid = str(uuid.uuid4())
            did = f"did:pebble:{did_uuid}"
            
            # Create a DID document
            did_document = {
                "@context": ["https://www.w3.org/ns/did/v1"],
                "id": did,
                "verificationMethod": [{
                    "id": f"{did}#keys-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": did,
                    "publicKeyBase58": public_key_base58
                }],
                "authentication": [f"{did}#keys-1"],
                "service": [{
                    "id": f"{did}#agent",
                    "type": "PebbleAgentCard",
                    "serviceEndpoint": "http://localhost:8000"
                }]
            }
            
            # Save the key pair
            with open(key_path, "w") as f:
                json.dump({
                    "privateKeyBase58": private_key,
                    "did": did,
                    "didDocument": did_document
                }, f, indent=2)
    
        return private_key, did, did_document

    def __init__(self, key_path="pebble_private_key.json", endpoint=None):
        self.key_path = key_path
        self.private_key, self.did, self.did_document = asyncio.run(self.get_or_create_did(key_path))
        # Update service endpoint if provided
        if endpoint:
            self.update_service_endpoint(endpoint)
        
        # Load the private key into a cryptography object
        try:
            raw_private_key = base64.b64decode(self.private_key)
            self.private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(raw_private_key)
        except Exception as e:
            print(f"Error loading private key: {e}")
            # Generate a new key if we can't load the existing one
            self.private_key_obj = ed25519.Ed25519PrivateKey.generate()

    def update_service_endpoint(self, endpoint):
        """Update the service endpoint in the DID document."""
        for service in self.did_document["service"]:
            if service["type"] == "PebbleAgentCard":
                service["serviceEndpoint"] = endpoint

    def get_did(self):
        """Get the DID of the agent."""
        return self.did

    def get_did_document(self):
        """Get the DID document of the agent."""
        return self.did_document

    def get_private_key(self):
        """Get the private key of the agent."""
        return self.private_key

    async def sign_message(self, message):
        """Sign a message using the agent's private key."""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        try:
            message_bytes = message.encode('utf-8')
            signature_bytes = self.private_key_obj.sign(message_bytes)
            signature = base64.b64encode(signature_bytes).decode('utf-8')
            return signature
        except Exception as e:
            print(f"Error signing message: {e}")
            return ""

    async def verify_message(self, message, signature, verification_method):
        """Verify a message signature using a verification method from a DID document."""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        try:
            # Extract the public key from the verification method
            # In a real implementation, you would look up the verification method in a DID document
            # For now, we'll just extract the public key from our own DID document
            verification_id = verification_method.split('#')[1]
            public_key_base58 = None
            
            for method in self.did_document["verificationMethod"]:
                if method["id"].endswith(verification_id):
                    public_key_base58 = method["publicKeyBase58"]
                    break
            
            if not public_key_base58:
                print(f"Could not find verification method: {verification_method}")
                return False
            
            # Load the public key
            public_key_bytes = base64.b64decode(public_key_base58)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify the signature
            message_bytes = message.encode('utf-8')
            signature_bytes = base64.b64decode(signature)
            
            public_key.verify(signature_bytes, message_bytes)
            return True
        except Exception as e:
            print(f"Error verifying message: {e}")
            return False

    def export_did_document(self, file_path=None):
        """Export the DID document to a file or return as string."""
        did_doc_str = json.dumps(self.did_document, indent=2)
        if file_path:
            with open(file_path, "w") as file:
                file.write(did_doc_str)
        return did_doc_str

    def import_did_document(self, did_document, validate=True):
        """Import a DID document, optionally validating its structure."""
        if isinstance(did_document, str):
            did_document = json.loads(did_document)
        
        if validate:
            # Basic validation
            required_fields = ["@context", "id", "verificationMethod"]
            for field in required_fields:
                if field not in did_document:
                    raise ValueError(f"Invalid DID document: missing '{field}' field")
        
        return did_document
