# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""MIDDLEWARE MODULE EXPORTS.

This module provides middleware layers for the bindu framework including
authentication and payment protocol enforcement.

MIDDLEWARE TYPES:

1. AUTHENTICATION MIDDLEWARE:
   - AuthMiddleware: Abstract base class for authentication
   - Auth0Middleware: Auth0 JWT validation (production-ready)
   - CognitoMiddleware: AWS Cognito JWT validation (template)

2. PAYMENT MIDDLEWARE:
   - X402Middleware: x402 payment protocol enforcement
     Automatically handles payment verification and settlement for agents
     with execution_cost configured.

USAGE PATTERNS:
   - Import the base AuthMiddleware class for type hints and interfaces
   - Import specific implementations based on your auth provider
   - Import X402Middleware for payment-gated agents
   - All implementations are interchangeable through their base interfaces
"""

from __future__ import annotations as _annotations

# Export authentication implementations
from .auth0 import Auth0Middleware
from .base import AuthMiddleware

# Export payment middleware
from .x402_middleware import X402Middleware

# from .cognito import CognitoMiddleware # TODO: Implement Cognito authentication

__all__ = [
    # Base interface
    "AuthMiddleware",
    # Authentication implementations
    "Auth0Middleware",
    # "CognitoMiddleware",
    # Payment middleware
    "X402Middleware",
]
