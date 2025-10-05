"""Cryptographic operations for DID system."""

import base58
from cryptography.hazmat.primitives.asymmetric import ed25519


class CryptoOperations:
    """Handles signing and verification operations."""
    
    @staticmethod
    def sign_text(private_key: ed25519.Ed25519PrivateKey, text: str) -> str:
        """Sign text using private key.
        
        Args:
            private_key: Ed25519 private key
            text: Text to sign
            
        Returns:
            Base58-encoded signature
        """
        signature = private_key.sign(text.encode("utf-8"))
        return base58.b58encode(signature).decode("ascii")
    
    @staticmethod
    def verify_text(public_key: ed25519.Ed25519PublicKey, text: str, signature: str) -> bool:
        """Verify signature using public key.
        
        Args:
            public_key: Ed25519 public key
            text: Original text that was signed
            signature: Base58-encoded signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            signature_bytes = base58.b58decode(signature)
            public_key.verify(signature_bytes, text.encode("utf-8"))
            return True
        except Exception:
            return False
    
    @staticmethod
    def encode_public_key_base58(public_key: ed25519.Ed25519PublicKey) -> str:
        """Encode public key in base58 format.
        
        Args:
            public_key: Ed25519 public key
            
        Returns:
            Base58-encoded public key
        """
        from cryptography.hazmat.primitives import serialization
        
        raw_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base58.b58encode(raw_bytes).decode("ascii")
