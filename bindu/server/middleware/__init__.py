# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""MIDDLEWARE MODULE EXPORTS.

This module provides the authentication middleware layer for the bindu framework.
It exposes different authentication provider implementations.

AUTHENTICATION PROVIDERS:

Think of this as the restaurant's security checkpoint catalog:

1. AUTHENTICATION INTERFACE (AuthMiddleware):
   - Abstract base class defining the authentication contract
   - All provider implementations must follow this interface
   - Ensures consistent API across different auth providers

2. AUTHENTICATION IMPLEMENTATIONS:
   - Auth0Middleware: Auth0 JWT validation (production-ready)
   - CognitoMiddleware: AWS Cognito JWT validation (template)

3. USAGE PATTERNS:
   - Import the base AuthMiddleware class for type hints and interfaces
   - Import specific implementations based on your auth provider
   - All implementations are interchangeable through the AuthMiddleware interface

AVAILABLE AUTHENTICATION OPTIONS:
- Auth0Middleware: Production-ready Auth0 integration
- CognitoMiddleware: AWS Cognito integration (template for future implementation)
"""

from __future__ import annotations as _annotations

# Export all authentication implementations
from .auth0 import Auth0Middleware

# Export the base authentication interface
from .base import AuthMiddleware

# from .cognito import CognitoMiddleware # TODO: Implement Cognito authentication

__all__ = [
    # Base interface
    "AuthMiddleware",
    # Authentication implementations
    "Auth0Middleware",
    # "CognitoMiddleware",
]
