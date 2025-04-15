"""
Security utilities for the Pebble framework.

This module provides utilities for API key generation and validation.
"""

import base64
import datetime
import hmac
import json
import os
import secrets
from typing import Dict, Optional, Tuple

from pebble.utils.config import ensure_env_file, load_env_vars


def get_secret_key() -> str:
    """Get the secret key from the .env file.
    
    Returns:
        str: The secret key
    """
    # Load environment variables
    env_vars = load_env_vars()
    
    # Get the secret key
    secret_key = env_vars.get("SECRET_KEY")
    if not secret_key:
        # If not found, ensure the .env file and try again
        ensure_env_file()
        env_vars = load_env_vars()
        secret_key = env_vars.get("SECRET_KEY")
    
    return secret_key


def rotate_secret_key() -> str:
    """Rotate the secret key in the .env file.
    
    Returns:
        str: The new secret key
    """
    # Import here to avoid circular imports
    import pathlib
    from pebble.utils.config import get_env_file_path, ensure_env_file
    
    env_file = get_env_file_path()
    
    if not env_file.exists():
        ensure_env_file()
    
    # Generate a new random key
    new_key = base64.b64encode(os.urandom(42)).decode()
    
    try:
        # Use direct file operations for simplicity and cross-platform support
        with open(env_file, "r") as f:
            lines = f.readlines()
        
        with open(env_file, "w") as f:
            key_found = False
            for line in lines:
                if line.startswith("SECRET_KEY="):
                    f.write(f"SECRET_KEY={new_key}\n")
                    key_found = True
                else:
                    f.write(line)
            
            if not key_found:
                f.write(f"SECRET_KEY={new_key}\n")
    except Exception as e:
        raise RuntimeError(f"Failed to rotate secret key: {e}")
    
    return new_key


def create_api_key(expire_days: int = 365) -> str:
    """Create a new API key with expiration.
    
    Args:
        expire_days: Number of days before the key expires
        
    Returns:
        str: The generated API key
    """
    # Get the secret key from the .env file
    secret_key = get_secret_key()
    
    # Create the payload with expiration
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=expire_days)
    payload = {
        "exp": expiration.timestamp(),
        "jti": secrets.token_hex(8)  # JWT ID
    }
    
    # Convert payload to JSON and encode
    payload_json = json.dumps(payload)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
    
    # Create signature
    signature = hmac.new(
        secret_key.encode(),
        payload_b64.encode(),
        "sha256"
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    # Combine to create the key
    api_key = f"pbl_{payload_b64}.{signature_b64}"
    
    return api_key


def validate_api_key(api_key: str) -> bool:
    """Validate an API key.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        bool: True if the key is valid, False otherwise
    """
    # Get the secret key from the .env file
    secret_key = get_secret_key()
    if not secret_key:
        return False
    
    # Split the key into parts
    try:
        if not api_key.startswith("pbl_"):
            return False
        
        # Remove prefix and split
        parts = api_key[4:].split(".")
        if len(parts) != 2:
            return False
        
        payload_b64, signature_b64 = parts
        
        # Verify signature
        expected_signature = hmac.new(
            secret_key.encode(),
            payload_b64.encode(),
            "sha256"
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip("=")
        
        if signature_b64 != expected_signature_b64:
            return False
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        payload = json.loads(payload_json)
        
        # Check expiration
        expiration = payload.get("exp", 0)
        if expiration < datetime.datetime.utcnow().timestamp():
            return False
        
        return True
    
    except Exception:
        return False