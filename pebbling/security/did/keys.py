import orjson
from typing import Tuple, Optional

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key

def generate_rsa_key_pair() -> Tuple[rsa.RSAPrivateKey, str, str]:
    """Generate an RSA key pair.
    
    Returns:
        Tuple of (private_key_obj, private_key_pem, public_key_pem)
    """
    # Generate an RSA key pair (works for both DID and TLS)
    private_key_obj = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    
    # Get the private key in PEM format
    private_key_pem = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get the public key in PEM format
    public_key_obj = private_key_obj.public_key()
    public_key_pem = public_key_obj.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_key_obj, private_key_pem, public_key_pem

def load_private_key(key_path: str) -> Tuple[Optional[object], Optional[str]]:
    """Load private key from a JSON file.
    
    Args:
        key_path: Path to the private key file
        
    Returns:
        Tuple of (private_key_obj, private_key_pem)
    """
    try:
        with open(key_path, "rb") as f:
            key_data = orjson.loads(f.read())
            private_key_pem = key_data.get("privateKeyPem")
        
        # Load the private key into a cryptography object
        private_key_obj = load_pem_private_key(
            private_key_pem.encode('utf-8'),
            password=None
        )
        return private_key_obj, private_key_pem
    except Exception as e:
        print(f"Error loading private key: {e}")
        return None, None
