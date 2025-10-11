"""Security utilities for Bindu agents.

This module provides utilities for secure password handling and key management.
"""


def validate_password_strength(password: str, min_length: int = 8) -> bool:
    """Validate password strength.

    Args:
        password: Password to validate
        min_length: Minimum required length (default: 8)

    Returns:
        True if password meets requirements

    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters long")

    # Check for at least one number or special character
    has_number = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    if not (has_number or has_special):
        raise ValueError(
            "Password must contain at least one number or special character"
        )

    return True
