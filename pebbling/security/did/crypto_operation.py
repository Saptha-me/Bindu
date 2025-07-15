import orjson
import base64
from typing import Any, Union, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519

# Import didkit if available for future use
try:
    import didkit
    DIDKIT_AVAILABLE = True
except ImportError:
    DIDKIT_AVAILABLE = False
    print("didkit module not available, using built-in cryptography instead")

async def sign_message(private_key: Any, message: Union[str, dict]) -> str:
    """Sign a message using a private key.
    
    Args:
        private_key: The private key object to use for signing
        message: The message to sign (string or dict)
        
    Returns:
        Base64-encoded signature
    """
    # Convert message to string if it's a dict
    if isinstance(message, dict):
        message = orjson.dumps(message)
    
    try:
        message_bytes = message.encode('utf-8')
        
        if isinstance(private_key, rsa.RSAPrivateKey):
            # RSA signing
            signature = private_key.sign(
                message_bytes,
                padding=serialization.padding.PKCS1v15(),
                algorithm=hashes.SHA256()
            )
        elif isinstance(private_key, ed25519.Ed25519PrivateKey):
            # Ed25519 signing
            signature = private_key.sign(message_bytes)
        else:
            raise ValueError("Unsupported private key type")
            
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"Error signing message: {e}")
        return ""

async def verify_message(message: Union[str, dict], signature: str, 
                        verification_method: dict) -> bool:
    """Verify a message signature using a verification method from a DID document.
    
    Args:
        message: The message that was signed (string or dict)
        signature: The base64-encoded signature
        verification_method: The verification method from a DID document
            
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # Convert message to string if it's a dict
        if isinstance(message, dict):
            message = orjson.dumps(message)
        
        # Decode the signature from base64
        signature_bytes = base64.b64decode(signature)
        message_bytes = message.encode('utf-8')
        
        # Extract public key from verification method
        if not verification_method or "publicKeyPem" not in verification_method:
            raise ValueError("Invalid verification method: missing public key")
        
        # Load the public key
        public_key_pem = verification_method["publicKeyPem"]
        
        # Check the key type based on the verification method type
        key_type = verification_method.get("type", "")
        
        if "Rsa" in key_type:
            # Handle RSA key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8')
            )
            
            # Verify the signature
            try:
                public_key.verify(
                    signature_bytes,
                    message_bytes,
                    padding=serialization.padding.PKCS1v15(),
                    algorithm=hashes.SHA256()
                )
                return True
            except Exception:
                return False
                
        elif "Ed25519" in key_type:
            # Handle Ed25519 key
            # Would need implementation specific to Ed25519
            return False
        else:
            # Unsupported key type
            raise ValueError(f"Unsupported verification method type: {key_type}")
            
    except Exception as e:
        print(f"Error verifying message: {e}")
        return False
