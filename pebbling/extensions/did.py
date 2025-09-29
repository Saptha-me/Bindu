import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from functools import cached_property
from datetime import datetime, timezone

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pebbling.common.protocol.types import AgentExtension


class DIDAgentExtensionMetadata:
    """Constants for DID-related metadata keys."""

    SIGNATURE_KEY = "did.message.signature"


    """DID extension for agent identity management."""

    def __init__(self, 
        recreate_keys: bool, 
        key_dir: Path,
        author: Optional[str] = None,
        agent_name: Optional[str] = None,
        key_password: Optional[str] = None,
    ):
        # Store key paths directly instead of key_dir
        self.private_key_path = str(key_dir / "private.pem")
        self.public_key_path = str(key_dir / "public.pem")
        self.recreate_keys = recreate_keys
        self.author = author  # The author/owner of the agent
        self.agent_name = agent_name
        self.key_password = key_password.encode() if key_password else None
        
        # Store additional metadata that will be included in DID document
        self.metadata: Dict[str, Any] = {}

    def generate_and_save_key_pair(self):
        """
        Generate and save key pair to files if they don't exist.

        Returns:
            Tuple of (private_key_path, public_key_path)

        Raises:
            OSError: If unable to write key files
        """
        # Ensure directory exists for the key files
        os.makedirs(os.path.dirname(self.private_key_path), exist_ok=True)

        # We need to create the keys in the following scenarios
        # 1. Either private or public key is missing
        # 2. We're explicitly creating new keys
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path) and not self.recreate_keys:
            return self.private_key_path, self.public_key_path

        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Currently we don't accept a password for the keys created
        # Moving forward to make the process a bit more secure, we can
        # start accepting passwords for the generated key pair as well
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        with open(self.private_key_path, "wb") as f:
            f.write(private_pem)

        with open(self.public_key_path, "wb") as f:
            f.write(public_pem)

        # Set appropriate file permissions (owner read/write only for private key)
        os.chmod(self.private_key_path, 0o600)
        os.chmod(self.public_key_path, 0o644)

    @cached_property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        """Load and cache the private key from file.

        Returns:
            Ed25519 private key object

        Raises:
            FileNotFoundError: If private key file does not exist
            ValueError: If key is not Ed25519
        """
        if not os.path.exists(self.private_key_path):
            raise FileNotFoundError(f"Private key file not found: {self.private_key_path}")

        with open(self.private_key_path, "rb") as f:
            private_key_pem = f.read()

        private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Private key is not an Ed25519 key")

        return private_key

    @cached_property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        """Load and cache the public key from file.

        Returns:
            Ed25519 public key object

        Raises:
            FileNotFoundError: If public key file does not exist
            ValueError: If key is not Ed25519
        """
        if not os.path.exists(self.public_key_path):
            raise FileNotFoundError(f"Public key file not found: {self.public_key_path}")

        with open(self.public_key_path, "rb") as f:
            public_key_pem = f.read()

        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key is not an Ed25519 key")

        return public_key

    def sign_text(self, text: str) -> str:
        """Sign the given text using the private key.

        Args:
            text: The text to sign

        Returns:
            Base58-encoded signature string

        Raises:
            FileNotFoundError: If private key file does not exist
            ValueError: If signing fails
        """
        # Sign the text (encode to bytes first)
        signature = self.private_key.sign(text.encode("utf-8"))

        # Encode signature in base58
        return base58.b58encode(signature).decode("ascii")

    def verify_text(self, text: str, signature: str) -> bool:
        """Verify the signature for the given text using the public key.

        Args:
            text: The text that was signed
            signature: Base58-encoded signature to verify

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            signature_bytes = base58.b58decode(signature)
            self.public_key.verify(signature_bytes, text.encode("utf-8"))
            return True
        except Exception:
            return False

    @cached_property
    def did(self) -> str:
        """Create custom Pebbling DID format.

        Returns:
            DID string in format did:pebbling:{author}:{agent_name}
            Falls back to did:key format if author or agent_name not provided
        """
        # Use custom Pebbling format if author and agent_name provided
        if self.author and self.agent_name:
            # Sanitize the components to ensure valid DID format
            sanitized_author = self.author.lower().replace(' ', '_').replace('@', '_at_').replace('.', '_')
            sanitized_agent_name = self.agent_name.lower().replace(' ', '_')
            return f"did:pebbling:{sanitized_author}:{sanitized_agent_name}"
        
        # Fallback to did:key format for backward compatibility
        with open(self.public_key_path, "rb") as f:
            public_key_pem = f.read()

        public_key = serialization.load_pem_public_key(public_key_pem)
        raw_bytes = public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

        # Encode in base58btc with 'z' prefix (multibase convention for ed25519)
        multibase_encoded = "z" + base58.b58encode(raw_bytes).decode("ascii")

        return f"did:key:{multibase_encoded}"

    def set_agent_metadata(self, 
                          skills: Optional[List[Any]] = None,
                          capabilities: Optional[Dict[str, Any]] = None,
                          description: Optional[str] = None,
                          version: Optional[str] = None,
                          author: Optional[str] = None,
                          **extra_metadata) -> None:
        """Set metadata that will be included in the DID document.
        
        Args:
            skills: List of agent skills
            capabilities: Agent capabilities dictionary
            description: Agent description
            version: Agent version
            author: Agent author
            **extra_metadata: Any additional metadata to include
        """
        if skills is not None:
            self.metadata["skills"] = skills
        if capabilities is not None:
            self.metadata["capabilities"] = capabilities
        if description is not None:
            self.metadata["description"] = description
        if version is not None:
            self.metadata["version"] = version
        if author is not None:
            self.metadata["author"] = author
        
        # Add any extra metadata
        self.metadata.update(extra_metadata)
    
    def get_did_document(self) -> Dict[str, Any]:
        """Generate a complete DID document with all agent information.
        
        Returns:
            Dictionary containing the full DID document with agent metadata
        """
        # Get public key for verification
        public_key_b58 = base58.b58encode(
            self.public_key.public_bytes(
                encoding=serialization.Encoding.Raw, 
                format=serialization.PublicFormat.Raw
            )
        ).decode("ascii")
        
        did_doc = {
            "@context": ["https://www.w3.org/ns/did/v1", "https://pebbling.ai/ns/v1"],
            "id": self.did,
            "created": datetime.now(timezone.utc).isoformat() + "Z",
            
            # Authentication method
            "authentication": [{
                "id": f"{self.did}#key-1",
                "type": "Ed25519VerificationKey2020",
                "controller": self.did,
                "publicKeyBase58": public_key_b58
            }],
            
            # Pebbling-specific metadata
            "pebbling": {
                "agentName": self.agent_name,
                "author": self.author,  # Using author instead of userId
                **self.metadata  # Include all metadata
            }
        }
        
        # Add service endpoints if URL is available
        if "url" in self.metadata:
            did_doc["service"] = [{
                "id": f"{self.did}#agent-service",
                "type": "PebblingAgentService",
                "serviceEndpoint": self.metadata["url"]
            }]
        
        return did_doc
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get a simplified agent info JSON (more readable than full DID document).
        
        Returns:
            Dictionary with agent information in a user-friendly format
        """
        info = {
            "did": self.did,
            "agentName": self.agent_name,
            "author": self.author,  # Using author instead of userId
            "publicKey": base58.b58encode(
                self.public_key.public_bytes(
                    encoding=serialization.Encoding.Raw, 
                    format=serialization.PublicFormat.Raw
                )
            ).decode("ascii"),
            "created": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add all metadata fields
        info.update(self.metadata)
        
        return info
    
    @cached_property
    def agent_extension(self):
        return AgentExtension(
            uri="https://github.com/Saptha-me/septha",
            description="DID-based identity management for Pebbling agents",
            required=False,
            params={
                "did": self.did,
                "resolver_endpoint": "/did/resolve",  # Endpoint to resolve DID info
                "info_endpoint": "/agent/info"  # Simplified info endpoint
            },
        )
