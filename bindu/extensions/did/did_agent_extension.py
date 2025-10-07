# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DID (Decentralized Identifier) Extension for Bindu Agents.

Why is DID an Extension?
------------------------
According to the A2A Protocol specification, extensions provide a standardized way to add
optional capabilities to agents without modifying the core protocol. Extensions are declared
in the agent's capabilities and can be discovered by clients.

By implementing DID as an extension (https://a2a-protocol.org/v0.3.0/topics/extensions/):
- **Modularity**: Agents can choose whether to support DID-based identity
- **Discoverability**: Clients can detect DID support through the agent card
- **Interoperability**: Standard extension format ensures cross-agent compatibility
- **Flexibility**: Different identity mechanisms can coexist as separate extensions

This extension provides cryptographic identity management using Ed25519 keys and W3C-compliant
DID documents, enabling agents to establish trust in a decentralized network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from bindu.common.protocol.types import AgentExtension
from bindu.utils.constants import (
    BASE58_ENCODING,
    DID_BINDU_CONTEXT,
    DID_EXTENSION_DESCRIPTION,
    DID_EXTENSION_URI,
    DID_INFO_ENDPOINT,
    DID_KEY_FRAGMENT,
    DID_METHOD_BINDU,
    DID_METHOD_KEY,
    DID_MULTIBASE_PREFIX,
    DID_PRIVATE_KEY_FILENAME,
    DID_PUBLIC_KEY_FILENAME,
    DID_RESOLVER_ENDPOINT,
    DID_SERVICE_FRAGMENT,
    DID_SERVICE_TYPE,
    DID_VERIFICATION_KEY_TYPE,
    DID_W3C_CONTEXT,
    TEXT_ENCODING,
)
from bindu.utils.logging import get_logger

logger = get_logger("bindu.did_extension")


class DIDAgentExtension:
    """DID extension for agent identity management.
    
    This class manages the complete lifecycle of an agent's decentralized identity,
    including cryptographic key generation, DID creation, and digital signatures.
    Each agent gets a unique, self-sovereign identity that can be verified without
    relying on centralized authorities.
    """

    def __init__(self, 
        recreate_keys: bool, 
        key_dir: Path,
        author: Optional[str] = None,
        agent_name: Optional[str] = None,
        key_password: Optional[str] = None,
    ):
        """Initialize the DID extension with cryptographic identity.
        
        Args:
            recreate_keys: If True, regenerate keys even if they already exist.
                          Useful for key rotation or testing. Use with caution in production.
            key_dir: Directory path where the Ed25519 key pair will be stored.
                    Private key saved as 'private.pem', public key as 'public.pem'.
            author: The creator/owner of the agent (e.g., email or identifier).
                   Used to construct human-readable DIDs: did:bindu:{author}:{agent_name}
            agent_name: The name of the agent. Combined with author to create the DID.
            key_password: Optional password to encrypt the private key at rest.
                         Can be a direct password, environment variable reference (env:VAR_NAME),
                         or 'prompt' for interactive entry. None means unencrypted.
        
        Attributes:
            private_key_path (str): Full path to the private key PEM file
            public_key_path (str): Full path to the public key PEM file
            did (str): The agent's Decentralized Identifier (computed from public key)
            metadata (dict): Additional metadata included in the DID document
        
        Example:
            >>> from pathlib import Path
            >>> did_ext = DIDAgentExtension(
            ...     recreate_keys=False,
            ...     key_dir=Path(".keys"),
            ...     author="alice@example.com",
            ...     agent_name="travel_agent",
            ...     key_password="env:AGENT_KEY_PASSWORD"
            ... )
            >>> did_ext.generate_and_save_key_pair()
            >>> print(did_ext.did)
            'did:bindu:alice_at_example_com:travel_agent'
        """
        # Store key directory and paths
        self._key_dir = key_dir
        self.private_key_path = key_dir / DID_PRIVATE_KEY_FILENAME
        self.public_key_path = key_dir / DID_PUBLIC_KEY_FILENAME
        self.recreate_keys = recreate_keys
        self.author = author  # The author/owner of the agent
        self.agent_name = agent_name
        self.key_password = key_password.encode() if key_password else None
        self._created_at = datetime.now(timezone.utc).isoformat()  # Cache creation timestamp
        
        # Store additional metadata that will be included in DID document
        self.metadata: Dict[str, Any] = {}

    def _generate_key_pair_data(self) -> tuple[bytes, bytes]:
        """Generate key pair and return PEM data.
        
        Returns:
            Tuple of (private_pem, public_pem) as bytes
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Use password protection if provided
        encryption_algorithm = (
            serialization.BestAvailableEncryption(self.key_password)
            if self.key_password
            else serialization.NoEncryption()
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_algorithm,
        )

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem

    def _get_key_paths(self) -> dict[str, str]:
        """Get KeyPaths object from current paths."""
        return {
            "private_key_path": str(self.private_key_path),
            "public_key_path": str(self.public_key_path)
        }

    def generate_and_save_key_pair(self) -> dict[str, str]:
        """Generate and save key pair to files if they don't exist.

        Returns:
            Dict containing the private and public key file paths

        Raises:
            OSError: If unable to write key files
        """
        # Ensure directory exists for the key files
        self._key_dir.mkdir(parents=True, exist_ok=True)

        # Skip generation if keys exist and we're not recreating
        if not self.recreate_keys and self.private_key_path.exists() and self.public_key_path.exists():
            return self._get_key_paths()

        private_pem, public_pem = self._generate_key_pair_data()

        # Write keys using Path methods
        self.private_key_path.write_bytes(private_pem)
        self.public_key_path.write_bytes(public_pem)

        # Set appropriate file permissions (owner read/write only for private key)
        self.private_key_path.chmod(0o600)
        self.public_key_path.chmod(0o644)
        
        return self._get_key_paths()
    

    def _load_key_from_file(self, key_path: Path, key_type: str) -> bytes:
        """Load key PEM data from file.
        
        Args:
            key_path: Path to the key file
            key_type: Type of key ('private' or 'public') for error messages
            
        Returns:
            Key PEM data as bytes
            
        Raises:
            FileNotFoundError: If key file does not exist
        """
        if not key_path.exists():
            raise FileNotFoundError(f"{key_type.capitalize()} key file not found: {key_path}")
        return key_path.read_bytes()

    @cached_property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        """Load and cache the private key from file.

        Returns:
            Ed25519 private key object

        Raises:
            FileNotFoundError: If private key file does not exist
            ValueError: If key is not Ed25519 or password issues
        """
        private_key_pem = self._load_key_from_file(self.private_key_path, "private")

        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem, 
                password=self.key_password
            )
        except TypeError as e:
            if "Password was not given but private key is encrypted" in str(e):
                raise ValueError(
                    "Private key is encrypted but no password was provided. "
                    "Please provide the key password in the configuration."
                ) from e
            raise
        
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
        public_key_pem = self._load_key_from_file(self.public_key_path, "public")
        public_key = serialization.load_pem_public_key(public_key_pem)
        
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key is not an Ed25519 key")

        return public_key

    @staticmethod
    def _encode_text(text: str) -> bytes:
        """Encode text to UTF-8 bytes."""
        return text.encode(TEXT_ENCODING)

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
        signature = self.private_key.sign(self._encode_text(text))
        return base58.b58encode(signature).decode(BASE58_ENCODING)

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
            self.public_key.verify(signature_bytes, self._encode_text(text))
            return True
        except Exception:
            return False

    @staticmethod
    def _sanitize_did_component(component: str) -> str:
        """Sanitize a component for use in DID."""
        return (
            component.lower()
            .replace(' ', '_')
            .replace('@', '_at_')
            .replace('.', '_')
        )

    @cached_property
    def did(self) -> str:
        """Create custom bindu DID format.

        Returns:
            DID string in format did:bindu:{author}:{agent_name}
            Falls back to did:key format if author or agent_name not provided
        """
        # Use custom bindu format if author and agent_name provided
        if self.author and self.agent_name:
            sanitized_author = self._sanitize_did_component(self.author)
            sanitized_agent_name = self._sanitize_did_component(self.agent_name)
            return f"did:{DID_METHOD_BINDU}:{sanitized_author}:{sanitized_agent_name}"
        
        # Fallback to did:key format with multibase encoding
        public_key_bytes = self._get_public_key_raw_bytes()
        multibase_encoded = DID_MULTIBASE_PREFIX + base58.b58encode(public_key_bytes).decode(BASE58_ENCODING)
        return f"did:{DID_METHOD_KEY}:{multibase_encoded}"

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
        # Update metadata with all non-None values
        updates = {
            "skills": skills,
            "capabilities": capabilities,
            "description": description,
            "version": version,
            "author": author,
        }
        self.metadata.update({k: v for k, v in updates.items() if v is not None})
        self.metadata.update(extra_metadata)
    
    def _get_public_key_raw_bytes(self) -> bytes:
        """Get raw bytes of public key."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

    @cached_property
    def public_key_base58(self) -> str:
        """Get base58-encoded public key (cached)."""
        return base58.b58encode(self._get_public_key_raw_bytes()).decode(BASE58_ENCODING)

    def get_did_document(self) -> Dict[str, Any]:
        """Generate a complete DID document with all agent information.
        
        Returns:
            Dictionary containing the full DID document with agent metadata
        """
        did_doc = {
            "@context": [DID_W3C_CONTEXT, DID_BINDU_CONTEXT],
            "id": self.did,
            "created": self._created_at,
            
            # Authentication method
            "authentication": [{
                "id": f"{self.did}#{DID_KEY_FRAGMENT}",
                "type": DID_VERIFICATION_KEY_TYPE,
                "controller": self.did,
                "publicKeyBase58": self.public_key_base58
            }],
            
            # bindu-specific metadata
            "bindu": {
                "agentName": self.agent_name,
                "author": self.author,
                **self.metadata  # Include all metadata
            }
        }
        
        # Add service endpoints if URL is available
        if "url" in self.metadata:
            did_doc["service"] = [{
                "id": f"{self.did}#{DID_SERVICE_FRAGMENT}",
                "type": DID_SERVICE_TYPE,
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
            "author": self.author,
            "publicKey": self.public_key_base58,
            "created": self._created_at,
        }
        
        # Add all metadata fields
        info.update(self.metadata)
        
        return info
    
    @cached_property
    def agent_extension(self) -> AgentExtension:
        return AgentExtension(
            uri=DID_EXTENSION_URI,
            description=DID_EXTENSION_DESCRIPTION,
            required=False,
            params={
                "did": self.did,
                "resolver_endpoint": DID_RESOLVER_ENDPOINT,
                "info_endpoint": DID_INFO_ENDPOINT
            },
        )
