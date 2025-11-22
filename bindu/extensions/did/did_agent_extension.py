# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
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
from typing import Any, Dict, Optional

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.did_extension")


class DIDAgentExtension:
    """DID extension for agent identity management.

    This class manages the complete lifecycle of an agent's decentralized identity,
    including cryptographic key generation, DID creation, and digital signatures.
    Each agent gets a unique, self-sovereign identity that can be verified without
    relying on centralized authorities.
    """

    def __init__(
        self,
        recreate_keys: bool,
        key_dir: Path,
        author: Optional[str] = None,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        key_password: Optional[str] = None,
    ):
        """Initialize the DID extension with cryptographic identity.

        Args:
            recreate_keys: If True, regenerate keys even if they already exist.
                          Useful for key rotation or testing. Use with caution in production.
            key_dir: Directory path where the Ed25519 key pair will be stored.
                    Private key saved as 'private.pem', public key as 'public.pem'.
            author: The creator/owner of the agent (e.g., email or identifier).
                   Used to construct human-readable DIDs: did:bindu:{author}:{agent_name}:{agent_id}
            agent_name: The name of the agent. Combined with author to create the DID.
            agent_id: The unique identifier of the agent. Appended at the end of the DID.
            key_password: Optional password to encrypt the private key at rest.
                         Can be a direct password, environment variable reference (env:VAR_NAME),
                         or 'prompt' for interactive entry. None means unencrypted.

        Attributes:
            private_key_path (str): Full path to the private key PEM file
            public_key_path (str): Full path to the public key PEM file
            did (str): The agent's Decentralized Identifier (computed from public key)
            metadata (dict): Additional metadata included in the DID document
        """
        # Store key directory and paths
        self._key_dir = key_dir
        self.private_key_path = key_dir / app_settings.did.private_key_filename
        self.public_key_path = key_dir / app_settings.did.public_key_filename
        self.recreate_keys = recreate_keys
        self.author = author  # The author/owner of the agent
        self.agent_name = agent_name
        self.agent_id = agent_id  # The unique agent identifier
        self.key_password = key_password.encode() if key_password else None
        self._created_at = datetime.now(
            timezone.utc
        ).isoformat()  # Cache creation timestamp

        # Store additional metadata that will be included in DID document
        self.metadata: Dict[str, Any] = {}

    def __repr__(self) -> str:
        """Return string representation of the extension."""
        did_preview = self.did[:20] + "..." if len(self.did) > 20 else self.did
        return (
            f"DIDAgentExtension(did={did_preview}, "
            f"author={self.author}, agent_name={self.agent_name})"
        )

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
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    def _get_key_paths(self) -> dict[str, str]:
        """Get KeyPaths object from current paths."""
        return {
            "private_key_path": str(self.private_key_path),
            "public_key_path": str(self.public_key_path),
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
        if (
            not self.recreate_keys
            and self.private_key_path.exists()
            and self.public_key_path.exists()
        ):
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
            raise FileNotFoundError(
                f"{key_type.capitalize()} key file not found: {key_path}"
            )
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
                private_key_pem, password=self.key_password
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
        return text.encode(app_settings.did.text_encoding)

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
        return base58.b58encode(signature).decode(app_settings.did.base58_encoding)

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
            component.lower().replace(" ", "_").replace("@", "_at_").replace(".", "_")
        )

    @cached_property
    def did(self) -> str:
        """Create custom bindu DID format.

        Returns:
            DID string in format did:bindu:{author}:{agent_name}:{agent_id}
            Falls back to did:key format if author or agent_name not provided
        """
        # Use custom bindu format if author, agent_name, and agent_id provided
        if self.author and self.agent_name and self.agent_id:
            sanitized_author = self._sanitize_did_component(self.author)
            sanitized_agent_name = self._sanitize_did_component(self.agent_name)
            return f"did:{app_settings.did.method_bindu}:{sanitized_author}:{sanitized_agent_name}:{self.agent_id}"

        # Fallback to did:key format with multibase encoding
        public_key_bytes = self._get_public_key_raw_bytes()
        encoded = base58.b58encode(public_key_bytes).decode(
            app_settings.did.base58_encoding
        )
        multibase_encoded = app_settings.did.multibase_prefix + encoded
        return f"did:{app_settings.did.method_key}:{multibase_encoded}"

    def _get_public_key_raw_bytes(self) -> bytes:
        """Get raw bytes of public key."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )

    @cached_property
    def public_key_base58(self) -> str:
        """Get base58-encoded public key (cached)."""
        return base58.b58encode(self._get_public_key_raw_bytes()).decode(
            app_settings.did.base58_encoding
        )

    def get_did_document(self) -> Dict[str, Any]:
        """Generate a complete DID document with all agent information.

        Returns:
            Dictionary containing the full DID document with agent metadata
        """
        did_doc = {
            "@context": [app_settings.did.w3c_context, app_settings.did.bindu_context],
            "id": self.did,
            "created": self._created_at,
            # Authentication method
            "authentication": [
                {
                    "id": f"{self.did}#{app_settings.did.key_fragment}",
                    "type": app_settings.did.verification_key_type,
                    "controller": self.did,
                    "publicKeyBase58": self.public_key_base58,
                }
            ],
        }
        return did_doc
