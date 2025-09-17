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
from typing import Tuple, Union

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.x509.oid import NameOID

from pebbling.common.models import KeyPaths

# Import constants from central location
from pebbling.utils.constants import (
    CSR_FILENAME,
    DEFAULT_KEY_ALGORITHM,
    PRIVATE_KEY_FILENAME,
    PUBLIC_KEY_FILENAME,
    RSA_KEY_SIZE,
    RSA_PUBLIC_EXPONENT,
    KeyType,
    PrivateKeyTypes,
    PublicKeyTypes,
)
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.security.common.keys")


def _load_key_file(file_path: str, private: bool = True) -> Tuple[Union[PrivateKeyTypes, PublicKeyTypes], str]:
    """Load a key from a file path."""
    with open(file_path, "rb") as f:
        key_pem = f.read().decode("utf-8")

    loader = load_pem_private_key if private else load_pem_public_key
    key_obj = loader(key_pem.encode("utf-8"), password=None if private else None)
    return key_obj, key_pem


def generate_key_pair(pki_dir: str, key_type: KeyType = "rsa", recreate: bool = False) -> KeyPaths:
    """Generate a cryptographic key pair or load existing keys.

    Args:
        pki_dir: Directory to store key files
        key_type: Type of key to generate ('rsa' or 'ed25519')
        recreate: Whether to force recreation of keys

    Returns:
        KeyPaths containing:
        - Private key file path
        - Public key file path
    """
    # Create directory if needed
    os.makedirs(pki_dir, exist_ok=True)

    private_key_file = os.path.join(pki_dir, PRIVATE_KEY_FILENAME)
    public_key_file = os.path.join(pki_dir, PUBLIC_KEY_FILENAME)

    # Remove existing files if recreating
    if recreate:
        for file_path in [private_key_file, public_key_file]:
            if os.path.exists(file_path):
                os.remove(file_path)

    # Generate keys if they don't exist or if recreating
    if not os.path.exists(private_key_file) or not os.path.exists(public_key_file) or recreate:
        try:
            # Generate new key pair based on type
            private_key_obj = (
                rsa.generate_private_key(public_exponent=RSA_PUBLIC_EXPONENT, key_size=RSA_KEY_SIZE)
                if key_type == "rsa"
                else ed25519.Ed25519PrivateKey.generate()
            )

            # Convert to PEM format
            private_key_pem = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            ).decode("utf-8")

            public_key_obj = private_key_obj.public_key()
            public_key_pem = public_key_obj.public_bytes(
                encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode("utf-8")

            # Save keys
            with open(private_key_file, "wb") as f:
                f.write(private_key_pem.encode("utf-8"))
            with open(public_key_file, "wb") as f:
                f.write(public_key_pem.encode("utf-8"))

        except Exception as e:
            logger.error(f"Failed to generate key pair: {e}")
            return None

    return KeyPaths(private_key_path=private_key_file, public_key_path=public_key_file)


def generate_csr(pki_dir: str, agent_id: str) -> str:
    """Generate a minimal Certificate Signing Request (CSR) using existing keys.

    Args:
        pki_dir: Directory containing the key files
        agent_id: Common Name (CN) for the certificate (typically agent ID or DID)

    Returns:
        The CSR file path if successful, None if failed
    """
    try:
        private_key, _ = load_private_key(pki_dir)

        # Build subject name
        subject_name = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, agent_id),
            ]
        )

        # Create CSR builder with minimal settings
        builder = x509.CertificateSigningRequestBuilder().subject_name(subject_name)

        # Determine the signing algorithm based on key type
        if isinstance(private_key, ed25519.Ed25519PrivateKey):
            # Ed25519 keys use None as algorithm (built-in hash)
            algorithm = None
        elif isinstance(private_key, rsa.RSAPrivateKey):
            # RSA keys use SHA256
            algorithm = hashes.SHA256()
        else:
            # Default to None for other key types
            algorithm = None

        # Sign the CSR with the appropriate algorithm
        csr = builder.sign(private_key=private_key, algorithm=algorithm)

        # Get PEM format
        csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

        # Save to file and return path
        csr_file_path = os.path.join(pki_dir, CSR_FILENAME)
        with open(csr_file_path, "wb") as f:
            f.write(csr_pem.encode("utf-8"))

        return csr_file_path

    except Exception as e:
        logger.error(f"Failed to generate CSR: {e}")
        return None


def load_private_key(pki_dir: str) -> Tuple[PrivateKeyTypes, str]:
    """Load the private key from the keys directory."""
    private_key_file = os.path.join(pki_dir, PRIVATE_KEY_FILENAME)

    if not os.path.exists(private_key_file):
        raise FileNotFoundError(f"Private key file not found at {private_key_file}")

    return _load_key_file(private_key_file, private=True)


def load_public_key(pki_dir: str) -> str:
    """Load the public key from the keys directory as a string."""
    public_key_file = os.path.join(pki_dir, PUBLIC_KEY_FILENAME)

    if not os.path.exists(public_key_file):
        raise FileNotFoundError(f"Public key file not found at {public_key_file}")

    with open(public_key_file, "rb") as f:
        return f.read().decode("utf-8")


# Aliases for backward compatibility
def generate_rsa_key_pair(key_path: str, recreate: bool = False) -> Tuple[PrivateKeyTypes, str, str, bool]:
    """Generate an RSA key pair (for backward compatibility)."""
    return generate_key_pair(key_path, "rsa", recreate)


def generate_ed25519_key_pair(key_path: str, recreate: bool = False) -> Tuple[PrivateKeyTypes, str, str, bool]:
    """Generate an Ed25519 key pair (for backward compatibility)."""
    return generate_key_pair(key_path, "ed25519", recreate)
