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

The payment_endpoints module provides REST API endpoints for
session-based payment flow:
- POST /api/start-payment-session: Start a new payment session
- GET /payment-capture: Browser page to capture payment
- GET /api/payment-status/{session_id}: Get payment status and token
"""

from __future__ import annotations as _annotations

from .x402_middleware import X402Middleware
from .payment_session_manager import PaymentSessionManager, PaymentSession
from .payment_endpoints import create_payment_router

__all__ = [
    "X402Middleware",
    "PaymentSessionManager",
    "PaymentSession",
    "create_payment_router",
]
