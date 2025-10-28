# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""X402 payment middleware for Bindu.

This module provides x402 payment protocol enforcement middleware
for agents that require payment for execution.

The X402Middleware automatically handles:
- Payment requirement detection
- Payment verification with Coinbase facilitator
- Payment settlement after successful execution
- 402 Payment Required responses
"""

from __future__ import annotations as _annotations

from .x402_middleware import X402Middleware

__all__ = [
    "X402Middleware",
]
