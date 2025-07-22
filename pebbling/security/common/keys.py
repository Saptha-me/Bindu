# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""Cryptographic key management utilities for Pebbling security.

This module provides functionality for generating, storing, loading, and
managing cryptographic keys used in the Pebbling security framework.
"""

import os
from typing import Literal, Tuple, Union

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

# Constants
PRIVATE_KEY_FILENAME = "private_key.pem"
PUBLIC_KEY_FILENAME = "public_key.pem"
RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537

KeyType = Literal["rsa", "ed25519"]
PrivateKeyTypes = Union[rsa.RSAPrivateKey, ed25519.Ed25519PrivateKey]
PublicKeyTypes = Union[rsa.RSAPublicKey, ed25519.Ed25519PublicKey]

def _load_key_file(file_path: str, private: bool = True) -> Tuple[Union[PrivateKeyTypes, PublicKeyTypes], str]:
    """Load a key from a file path."""
    with open(file_path, "rb") as f:
        key_pem = f.read().decode('utf-8')
    
    loader = load_pem_private_key if private else load_pem_public_key
    key_obj = loader(key_pem.encode('utf-8'), password=None if private else None)
    return key_obj, key_pem

def generate_key_pair(
        keys_dir: str,
        key_type: KeyType = "rsa", 
        recreate: bool = False
    ) -> Tuple[PrivateKeyTypes, str, str]:
    """Generate a cryptographic key pair or load existing keys."""
    # Create directory if needed
    os.makedirs(keys_dir, exist_ok=True)
    
    private_key_file = os.path.join(keys_dir, PRIVATE_KEY_FILENAME)
    public_key_file = os.path.join(keys_dir, PUBLIC_KEY_FILENAME)
    
    # Try to load existing keys if not recreating
    if os.path.exists(private_key_file) and not recreate:
        try:
            private_key_obj, private_key_pem = _load_key_file(private_key_file, private=True)
            with open(public_key_file, "rb") as f:
                public_key_pem = f.read().decode('utf-8')
            return private_key_obj, private_key_pem, public_key_pem
        except Exception:
            # Fall through to create new keys
            pass
    
    # Remove existing files if recreating
    if recreate:
        for file_path in [private_key_file, public_key_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    # Generate new key pair based on type
    private_key_obj = (
        rsa.generate_private_key(public_exponent=RSA_PUBLIC_EXPONENT, key_size=RSA_KEY_SIZE)
        if key_type == "rsa" else ed25519.Ed25519PrivateKey.generate()
    )
    
    # Convert to PEM format
    private_key_pem = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_key_obj = private_key_obj.public_key()
    public_key_pem = public_key_obj.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Save keys
    with open(private_key_file, "wb") as f:
        f.write(private_key_pem.encode('utf-8'))
    with open(public_key_file, "wb") as f:
        f.write(public_key_pem.encode('utf-8'))
    
    return private_key_obj, private_key_pem, public_key_pem

def generate_csr(
    keys_dir: str,
    agent_id: str
) -> str:
    """Generate a minimal Certificate Signing Request (CSR) using existing keys.
    
    Args:
        keys_dir: Directory containing the key files
        agent_name: Common Name (CN) for the certificate (typically agent ID or DID)
        output_file: Optional file path to save the CSR
        
    Returns:
        The CSR in PEM format
    """
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    
    # Load private key
    private_key, _ = load_private_key(keys_dir)
    
    # Build subject name
    subject_name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, agent_name),
    ])
    
    # Create CSR builder with minimal settings
    builder = x509.CertificateSigningRequestBuilder().subject_name(subject_name)
    
    # Sign the CSR with the private key
    csr = builder.sign(
        private_key=private_key,
        algorithm=hashes.SHA256()
    )
    
    # Get PEM format
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    
    # Save to file if output_file is provided
    if output_file:
        with open(output_file, "wb") as f:
            f.write(csr_pem.encode('utf-8'))
    
    return csr_pem

def load_private_key(keys_dir: str) -> Tuple[PrivateKeyTypes, str]:
    """Load the private key from the keys directory."""
    private_key_file = os.path.join(keys_dir, PRIVATE_KEY_FILENAME)
    
    if not os.path.exists(private_key_file):
        raise FileNotFoundError(f"Private key file not found at {private_key_file}")
    
    return _load_key_file(private_key_file, private=True)

def load_public_key(keys_dir: str) -> str:
    """Load the public key from the keys directory as a string."""
    public_key_file = os.path.join(keys_dir, PUBLIC_KEY_FILENAME)
    
    if not os.path.exists(public_key_file):
        raise FileNotFoundError(f"Public key file not found at {public_key_file}")
    
    with open(public_key_file, "rb") as f:
        return f.read().decode('utf-8')

# Aliases for backward compatibility
def generate_rsa_key_pair(key_path: str, recreate: bool = False) -> Tuple[PrivateKeyTypes, str, str]:
    """Generate an RSA key pair (for backward compatibility)."""
    return generate_key_pair(key_path, "rsa", recreate)

def generate_ed25519_key_pair(key_path: str, recreate: bool = False) -> Tuple[PrivateKeyTypes, str, str]:
    """Generate an Ed25519 key pair (for backward compatibility)."""
    return generate_key_pair(key_path, "ed25519", recreate)
