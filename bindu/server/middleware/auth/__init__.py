# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Authentication middleware for Bindu.

This module provides authentication middleware implementations for
securing Bindu agents with various authentication providers.

Available Providers:
- Auth0Middleware: Auth0 JWT validation (production-ready)
- CognitoMiddleware: AWS Cognito JWT validation (template)
"""

from __future__ import annotations as _annotations

from .auth0 import Auth0Middleware
from .base import AuthMiddleware
from .cognito import CognitoMiddleware

__all__ = [
    "AuthMiddleware",
    "Auth0Middleware",
    "CognitoMiddleware",
]
