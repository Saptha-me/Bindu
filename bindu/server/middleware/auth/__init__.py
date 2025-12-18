# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Authentication middleware for Bindu server.

Provides authentication middleware for different providers:
- Ory Hydra (HydraMiddleware) - OAuth2 authentication
- Auth0 (Auth0Middleware) - DEPRECATED, use Hydra
- AWS Cognito (CognitoMiddleware) - template only, DEPRECATED
"""

from bindu.server.middleware.auth.auth0 import Auth0Middleware
from bindu.server.middleware.auth.base import AuthMiddleware
from bindu.server.middleware.auth.cognito import CognitoMiddleware
from bindu.server.middleware.auth.hydra import HydraMiddleware

__all__ = ["AuthMiddleware", "HydraMiddleware", "Auth0Middleware", "CognitoMiddleware"]
