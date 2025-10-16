"""x402 extension constants and metadata keys for Bindu.

This module defines the x402 A2A extension URI and the metadata keys
used to record payment flow state on Tasks and Messages.
"""

from __future__ import annotations


# Extension URI (activation and declaration)
X402_EXTENSION_URI = "https://github.com/google-a2a/a2a-x402/v0.1"


class X402Metadata:
    """Metadata key constants for x402 payment flow."""

    STATUS_KEY = "x402.payment.status"
    REQUIRED_KEY = "x402.payment.required"  # Contains x402PaymentRequiredResponse
    PAYLOAD_KEY = "x402.payment.payload"  # Contains PaymentPayload
    RECEIPTS_KEY = "x402.payment.receipts"  # Array of settlement receipts
    ERROR_KEY = "x402.payment.error"  # Error code/message when failed


class X402Status:
    """String values for x402 payment statuses."""

    PAYMENT_REQUIRED = "payment-required"
    PAYMENT_SUBMITTED = "payment-submitted"
    PAYMENT_VERIFIED = "payment-verified"
    PAYMENT_COMPLETED = "payment-completed"
    PAYMENT_FAILED = "payment-failed"
