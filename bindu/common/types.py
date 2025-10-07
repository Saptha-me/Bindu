# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Common type definitions for the Bindu agent framework.

This module contains shared type definitions that are used across multiple modules
to avoid circular imports.
"""

from typing import NamedTuple


class KeyPaths(NamedTuple):
    """Cryptographic key file paths for agent identity.
    
    These paths point to the agent's digital fingerprint - the keys that prove
    who they are in the decentralized constellation.
    """
    
    private_key_path: str
    public_key_path: str
