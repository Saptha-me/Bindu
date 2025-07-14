import asyncio
import json
import os
import uuid
import base64
from typing import Dict, Any, Tuple, Optional, Union

import base64
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

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
    def get_or_create_did(key_path: str) -> Tuple[str, str, Dict[str, Any]]:
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
            private_key = key_data["privateKeyPem"]
            did = key_data["did"]
            did_document = key_data["didDocument"]
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            
            # Generate an RSA key pair (works for both DID and TLS)
            private_key_obj = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Get the private key in PEM format
            private_key_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
            
            # Get the public key in PEM format
            public_key_obj = private_key_obj.public_key()
            public_key_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode('utf-8')
            
            # Create a DID
            did_uuid = str(uuid.uuid4())
            did = f"did:pebble:{did_uuid}"
            
            # Create a DID document
            did_document = {
                "@context": ["https://www.w3.org/ns/did/v1"],
                "id": did,
                "verificationMethod": [{
                    "id": f"{did}#keys-1",
                    "type": "RsaVerificationKey2018",
                    "controller": did,
                    "publicKeyPem": public_key_pem
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
                    "privateKeyPem": private_key_pem,
                    "did": did,
                    "didDocument": did_document
                }, f, indent=2)
    
        return did, did_document

    def __init__(self, key_path="pebble_private_key.json", endpoint=None):
        self.key_path = key_path
        self.did, self.did_document = self.get_or_create_did(key_path)
        # Update service endpoint if provided
        if endpoint:
            self.update_service_endpoint(endpoint)
        
        # Load the private key data from file
        try:
            with open(key_path, "r") as f:
                key_data = json.load(f)
                self.private_key_pem = key_data.get("privateKeyPem")
            
            # Load the private key into a cryptography object
            self.private_key_obj = load_pem_private_key(
                self.private_key_pem.encode('utf-8'),
                password=None
            )
        except Exception as e:
            print(f"Error loading private key: {e}")
            # Generate a new key if we can't load the existing one
            self.private_key_obj = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.private_key_pem = self.private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode('utf-8')
        
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

    def get_private_key(self) -> str:
        """Get the private key of the agent as a PEM string.
        
        Returns:
            Private key in PEM format
        """
        return self.private_key_pem
    
    def get_private_key_object(self):
        """Get the private key object of the agent."""
        return self.private_key_obj

    async def sign_message(self, message):
        """Sign a message using the agent's private key."""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        try:
            message_bytes = message.encode('utf-8')
            signature = self.private_key_obj.sign(
                message_bytes,
                padding=serialization.padding.PKCS1v15(),
                algorithm=hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            print(f"Error signing message: {e}")
            return ""

    async def verify_message(self, message, signature, verification_method):
        """Verify a message signature using a verification method from a DID document.
        
        Args:
            message: The message that was signed (string or dict)
            signature: The base64-encoded signature
            verification_method: The verification method from a DID document
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Convert message to string if it's a dict
            if isinstance(message, dict):
                message = json.dumps(message)
            
            # Decode the signature from base64
            signature_bytes = base64.b64decode(signature)
            message_bytes = message.encode('utf-8')
            
            # Extract public key from verification method
            if not verification_method or "publicKeyPem" not in verification_method:
                raise ValueError("Invalid verification method: missing public key")
            
            # Load the public key
            public_key_pem = verification_method["publicKeyPem"]
            
            # Check the key type based on the verification method type
            key_type = verification_method.get("type", "")
            
            if "Rsa" in key_type:
                # Handle RSA key
                public_key = serialization.load_pem_public_key(
                    public_key_pem.encode('utf-8')
                )
                
                # Verify the signature
                try:
                    public_key.verify(
                        signature_bytes,
                        message_bytes,
                        padding=serialization.padding.PKCS1v15(),
                        algorithm=hashes.SHA256()
                    )
                    return True
                except Exception:
                    return False
                    
            elif "Ed25519" in key_type:
                # Handle Ed25519 key
                # Would need implementation specific to Ed25519
                return False
            else:
                # Unsupported key type
                raise ValueError(f"Unsupported verification method type: {key_type}")
                
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
