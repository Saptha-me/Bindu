from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from bindu.common.protocol.types import AgentExtension

logger = logging.getLogger(__name__)

# Optional async file I/O support
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    logger.warning("aiofiles not installed. Async file operations will fall back to sync.")


class DIDAgentExtensionMetadata:
    """Constants for DID-related metadata keys."""

    SIGNATURE_KEY = "did.message.signature"



class DIDAgentExtension:
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
        self._key_dir = os.path.dirname(self.private_key_path)  # Cache directory path
        self.recreate_keys = recreate_keys
        self.author = author  # The author/owner of the agent
        self.agent_name = agent_name
        self.key_password = key_password.encode() if key_password else None
        self._created_at = datetime.now(timezone.utc).isoformat()  # Cache creation timestamp
        
        # Store additional metadata that will be included in DID document
        self.metadata: Dict[str, Any] = {}

    def _generate_key_pair_data(self) -> Tuple[bytes, bytes]:
        """Generate key pair and return PEM data.
        
        Returns:
            Tuple of (private_pem, public_pem)
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

    def generate_and_save_key_pair(self) -> Tuple[str, str]:
        """
        Generate and save key pair to files if they don't exist.

        Returns:
            Tuple of (private_key_path, public_key_path)

        Raises:
            OSError: If unable to write key files
        """
        # Ensure directory exists for the key files
        os.makedirs(self._key_dir, exist_ok=True)

        # We need to create the keys in the following scenarios
        # 1. Either private or public key is missing
        # 2. We're explicitly creating new keys
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path) and not self.recreate_keys:
            return self.private_key_path, self.public_key_path

        private_pem, public_pem = self._generate_key_pair_data()

        with open(self.private_key_path, "wb") as f:
            f.write(private_pem)

        with open(self.public_key_path, "wb") as f:
            f.write(public_pem)

        # Set appropriate file permissions (owner read/write only for private key)
        os.chmod(self.private_key_path, 0o600)
        os.chmod(self.public_key_path, 0o644)
        
        return self.private_key_path, self.public_key_path
    
    async def generate_and_save_key_pair_async(self) -> Tuple[str, str]:
        """
        Async version - Generate and save key pair to files if they don't exist.

        Returns:
            Tuple of (private_key_path, public_key_path)

        Raises:
            OSError: If unable to write key files
        """
        # Check if async file I/O is available
        if not AIOFILES_AVAILABLE:
            logger.debug("Falling back to sync key generation (aiofiles not available)")
            return await asyncio.get_event_loop().run_in_executor(
                None, self.generate_and_save_key_pair
            )
        
        # Ensure directory exists for the key files
        os.makedirs(self._key_dir, exist_ok=True)

        # We need to create the keys in the following scenarios
        # 1. Either private or public key is missing
        # 2. We're explicitly creating new keys
        if os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path) and not self.recreate_keys:
            return self.private_key_path, self.public_key_path

        # Key generation is CPU-bound, so run in executor
        private_pem, public_pem = await asyncio.get_event_loop().run_in_executor(
            None, self._generate_key_pair_data
        )

        # Async file write
        async with aiofiles.open(self.private_key_path, "wb") as f:
            await f.write(private_pem)

        async with aiofiles.open(self.public_key_path, "wb") as f:
            await f.write(public_pem)

        # Set appropriate file permissions
        await asyncio.get_event_loop().run_in_executor(
            None, os.chmod, self.private_key_path, 0o600
        )
        await asyncio.get_event_loop().run_in_executor(
            None, os.chmod, self.public_key_path, 0o644
        )
        
        return self.private_key_path, self.public_key_path

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

    @staticmethod
    def _sanitize_did_component(component: str) -> str:
        """Sanitize a component for use in DID."""
        # Use regex for efficient multi-character replacement
        return re.sub(r'[@.]', lambda m: '_at_' if m.group() == '@' else '_', 
                     component.lower().replace(' ', '_'))

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
            return f"did:bindu:{sanitized_author}:{sanitized_agent_name}"
        
        # Fallback to did:key format - use cached public_key property
        raw_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )

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
    
    @cached_property
    def public_key_base58(self) -> str:
        """Get base58-encoded public key (cached)."""
        return base58.b58encode(
            self.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        ).decode("ascii")

    def get_did_document(self) -> Dict[str, Any]:
        """Generate a complete DID document with all agent information.
        
        Returns:
            Dictionary containing the full DID document with agent metadata
        """
        did_doc = {
            "@context": ["https://www.w3.org/ns/did/v1", "https://bindu.ai/ns/v1"],
            "id": self.did,
            "created": self._created_at,
            
            # Authentication method
            "authentication": [{
                "id": f"{self.did}#key-1",
                "type": "Ed25519VerificationKey2020",
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
                "id": f"{self.did}#agent-service",
                "type": "binduAgentService",
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
    def agent_extension(self):
        return AgentExtension(
            uri="https://github.com/Saptha-me/septha",
            description="DID-based identity management for bindu agents",
            required=False,
            params={
                "did": self.did,
                "resolver_endpoint": "/did/resolve",  # Endpoint to resolve DID info
                "info_endpoint": "/agent/info"  # Simplified info endpoint
            },
        )
