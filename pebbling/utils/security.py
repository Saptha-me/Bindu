"""
Security utilities for Pebbling framework.

This module provides security-related utilities such as secure password input
and key management helpers.
"""

import getpass
import os
from typing import Optional


def get_key_password(config: dict) -> Optional[str]:
    """Get key password from config or prompt user.
    
    Args:
        config: Agent configuration dictionary
        
    Returns:
        Password string or None if no password protection desired
        
    The password can be obtained in the following ways:
    1. Direct string in config["key_password"] (not recommended for production)
    2. Environment variable reference: "env:VARIABLE_NAME"  
    3. Interactive prompt: "prompt"
    4. None/empty for no password protection
    """
    password_config = config.get("key_password")
    
    if not password_config:
        return None
        
    # Environment variable reference
    if password_config.startswith("env:"):
        env_var = password_config[4:]
        password = os.environ.get(env_var)
        if not password:
            print(f"Warning: Environment variable '{env_var}' not set.")
            return None
        return password
    
    # Interactive prompt
    elif password_config == "prompt":
        try:
            password = getpass.getpass("Enter key password (leave empty for no encryption): ")
            if password:
                # Confirm password for new keys
                confirm = getpass.getpass("Confirm key password: ")
                if password != confirm:
                    raise ValueError("Passwords do not match")
            return password if password else None
        except KeyboardInterrupt:
            print("\nPassword entry cancelled.")
            return None
    
    # Direct password (not recommended)
    else:
        print("Warning: Using password from config file. Consider using 'env:VARIABLE_NAME' or 'prompt' instead.")
        return password_config


def validate_password_strength(password: str, min_length: int = 8) -> tuple[bool, str]:
    """Validate password strength.
    
    Args:
        password: Password to validate
        min_length: Minimum required length (default: 8)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"
        
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    if not (has_upper and has_lower and has_digit):
        return False, "Password must contain uppercase, lowercase, and numeric characters"
    
    return True, ""
