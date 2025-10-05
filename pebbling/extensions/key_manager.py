"""Key management utilities for DID system."""

import os
from pathlib import Path
from typing import Optional, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class KeyManager:
    """Handles key generation, storage, and retrieval for DID system."""
    
    def __init__(
        self,
        private_key_path: str,
        public_key_path: str,
        key_password: Optional[bytes] = None,
    ):
        self.private_key_path = private_key_path
        self.public_key_path = public_key_path
        self.key_password = key_password
    
    def key_files_exist(self) -> bool:
        """Check if both key files exist."""
        return os.path.exists(self.private_key_path) and os.path.exists(self.public_key_path)
    
    def generate_key_pair(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Generate a new Ed25519 key pair."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key
    
    def get_encryption_algorithm(self):
        """Get the appropriate encryption algorithm based on password presence."""
        if self.key_password:
            return serialization.BestAvailableEncryption(self.key_password)
        return serialization.NoEncryption()
    
    def serialize_private_key(self, private_key: ed25519.Ed25519PrivateKey) -> bytes:
        """Serialize private key to PEM format."""
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=self.get_encryption_algorithm(),
        )
    
    def serialize_public_key(self, public_key: ed25519.Ed25519PublicKey) -> bytes:
        """Serialize public key to PEM format."""
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def save_keys(self, private_pem: bytes, public_pem: bytes) -> None:
        """Save key files with appropriate permissions."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.private_key_path), exist_ok=True)
        
        # Write keys
        with open(self.private_key_path, "wb") as f:
            f.write(private_pem)
        
        with open(self.public_key_path, "wb") as f:
            f.write(public_pem)
        
        # Set appropriate file permissions
        os.chmod(self.private_key_path, 0o600)  # Owner read/write only
        os.chmod(self.public_key_path, 0o644)   # Owner read/write, others read
    
    def generate_and_save_keys(self, recreate: bool = False) -> Tuple[str, str]:
        """Generate and save key pair if needed.
        
        Args:
            recreate: Force recreation of keys even if they exist
            
        Returns:
            Tuple of (private_key_path, public_key_path)
        """
        if self.key_files_exist() and not recreate:
            return self.private_key_path, self.public_key_path
        
        private_key, public_key = self.generate_key_pair()
        private_pem = self.serialize_private_key(private_key)
        public_pem = self.serialize_public_key(public_key)
        self.save_keys(private_pem, public_pem)
        
        return self.private_key_path, self.public_key_path
    
    def load_private_key(self) -> ed25519.Ed25519PrivateKey:
        """Load private key from file."""
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
                )
            raise
        
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Private key is not an Ed25519 key")
        
        return private_key
    
    def load_public_key(self) -> ed25519.Ed25519PublicKey:
        """Load public key from file."""
        if not os.path.exists(self.public_key_path):
            raise FileNotFoundError(f"Public key file not found: {self.public_key_path}")
        
        with open(self.public_key_path, "rb") as f:
            public_key_pem = f.read()
        
        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key is not an Ed25519 key")
        
        return public_key
