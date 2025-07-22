import os
from typing import Tuple, Optional, Union, Literal

from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# Constants
PRIVATE_KEY_FILENAME = "private_key.pem"
PUBLIC_KEY_FILENAME = "public_key.pem"
RSA_KEY_SIZE = 4096
RSA_PUBLIC_EXPONENT = 65537

KeyType = Literal["rsa", "ed25519"]
PrivateKeyTypes = Union[rsa.RSAPrivateKey, ed25519.Ed25519PrivateKey]
PublicKeyTypes = Union[rsa.RSAPublicKey, ed25519.Ed25519PublicKey]

def generate_key_pair(
        keys_dir: str,
        key_type: KeyType = "rsa", 
        recreate: bool = False
    ) -> Tuple[PrivateKeyTypes, str, str]:
    """Generate a cryptographic key pair or load existing keys.
    
    Args:
        keys_dir: Path to the directory to store keys
        key_type: Type of key to generate ("rsa" or "ed25519")
        recreate: Whether to recreate the key files if they exist
    
    Returns:
        Tuple of (private_key_obj, private_key_pem, public_key_pem)
    """
    # Create directory if needed
    os.makedirs(keys_dir, exist_ok=True)
    
    private_key_file = os.path.join(keys_dir, PRIVATE_KEY_FILENAME)
    public_key_file = os.path.join(keys_dir, PUBLIC_KEY_FILENAME)
    
    # Try to load existing keys if not recreating
    if os.path.exists(private_key_file) and not recreate:
        try:
            private_key_obj, private_key_pem = _load_private_key_file(private_key_file)
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
    if key_type == "rsa":
        private_key_obj = rsa.generate_private_key(
            public_exponent=RSA_PUBLIC_EXPONENT,
            key_size=RSA_KEY_SIZE
        )
    else:  # ed25519
        private_key_obj = ed25519.Ed25519PrivateKey.generate()
    
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

def _load_key_file(file_path: str, private: bool = True) -> Tuple[PrivateKeyTypes, str]:
    """Helper to load a key from a file path."""
    with open(file_path, "rb") as f:
        key_pem = f.read().decode('utf-8')
    
    if private:
        key_obj = load_pem_private_key(
            key_pem.encode('utf-8'),
            password=None
        )
    else:
        key_obj = load_pem_public_key(
            key_pem.encode('utf-8')
        )
    return key_obj

def load_private_key(keys_dir: str) -> Tuple[PrivateKeyTypes, str]:
    """Load the private key from the keys directory."""
    private_key_file = os.path.join(keys_dir, "private_key.pem")
    
    if not os.path.exists(private_key_file):
        raise FileNotFoundError(f"Private key file not found at {private_key_file}")
    
    return _load_key_file(private_key_file, private=True)

def load_public_key(keys_dir: str) -> str:
    """Load the public key from the keys directory as a string."""
    public_key_file = os.path.join(keys_dir, "public_key.pem")
    
    if not os.path.exists(public_key_file):
        raise FileNotFoundError(f"Public key file not found at {public_key_file}")
    
    # Read the file directly as string instead of using _load_key_file to avoid encoding issues
    with open(public_key_file, "rb") as f:
        public_key_pem = f.read().decode('utf-8')
    
    return public_key_pem

# Aliases for backward compatibility
generate_rsa_key_pair = lambda key_path, recreate=False: generate_key_pair(key_path, "rsa", recreate)
generate_ed25519_key_pair = lambda key_path, recreate=False: generate_key_pair(key_path, "ed25519", recreate)
