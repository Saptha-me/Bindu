import os
from pathlib import Path
from typing import Optional, Tuple
from functools import cached_property

import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pebbling.common.protocol.types import AgentExtension


class DIDAgentExtension:
    """DID extension for agent identity management."""

    def __init__(self, recerate_keys: bool, key_dir: Path):
        # Store key paths directly instead of key_dir
        self.private_key_path = str(key_dir / "private.pem")
        self.public_key_path = str(key_dir / "public.pem")
        self.recreate_keys = recerate_keys
        self.extension = AgentExtension(
            uri="https://github.com/Saptha-me/septha",
            # TODO: add a better description
            description="Manage did's for your agent",
            required=False,
        )

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
    def did(self) -> str:
        """Create did:key format DID based on the public key.

        Returns:
            DID string in format did:key:{multibase_encoded_public_key}
        """
        with open(self.public_key_path, "rb") as f:
            public_key_pem = f.read()

        public_key = serialization.load_pem_public_key(public_key_pem)
        raw_bytes = public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

        # Encode in base58btc with 'z' prefix (multibase convention for ed25519)
        multibase_encoded = "z" + base58.b58encode(raw_bytes).decode("ascii")

        return f"did:key:{multibase_encoded}"