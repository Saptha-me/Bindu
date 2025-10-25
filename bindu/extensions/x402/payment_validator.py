"""X402 Payment Validation - Reusable payment verification logic.

This module provides a centralized payment validator that can be used
by both TaskManager (early validation) and ManifestWorker (fallback validation).

Following DRY principles, all payment verification logic is consolidated here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from x402.facilitator import FacilitatorClient
from x402.types import PaymentPayload, PaymentRequirements

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.extensions.x402.payment_validator")


@dataclass
class PaymentValidationResult:
    """Result of payment validation."""

    is_valid: bool
    error_reason: str | None = None
    payment_payload: PaymentPayload | None = None
    payment_requirements: PaymentRequirements | None = None


class PaymentValidator:
    """Validates x402 payment submissions against requirements.
    
    This class provides reusable payment verification logic that can be
    called from different parts of the application (TaskManager, ManifestWorker).
    """

    @staticmethod
    def parse_payment_payload(data: Any) -> PaymentPayload | None:
        """Parse payment payload from raw data.
        
        Args:
            data: Raw payment payload data (dict or PaymentPayload)
            
        Returns:
            PaymentPayload object or None if parsing fails
        """
        if data is None:
            return None
        try:
            if hasattr(PaymentPayload, "model_validate"):
                return PaymentPayload.model_validate(data)  # type: ignore
            return PaymentPayload(**data)
        except Exception as e:
            logger.warning("Failed to parse PaymentPayload", error=str(e))
            return None

    @staticmethod
    def parse_payment_requirements(data: Any) -> PaymentRequirements | None:
        """Parse payment requirements from raw data.
        
        Args:
            data: Raw payment requirements data (dict or PaymentRequirements)
            
        Returns:
            PaymentRequirements object or None if parsing fails
        """
        if data is None:
            return None
        try:
            if hasattr(PaymentRequirements, "model_validate"):
                return PaymentRequirements.model_validate(data)  # type: ignore
            return PaymentRequirements(**data)
        except Exception as e:
            logger.warning("Failed to parse PaymentRequirements", error=str(e), data=data)
            return None

    @staticmethod
    def select_requirement_from_required(
        required: Any, payload: PaymentPayload | None
    ) -> PaymentRequirements | None:
        """Select and validate payment requirement matching the payload.

        Performs comprehensive validation:
        1. Scheme and network match
        2. Amount validation (authorization.value >= maxAmountRequired)
        3. Pay-to address validation (payment goes to merchant)

        Args:
            required: Payment requirements from agent (accepts array)
            payload: Payment payload from client

        Returns:
            Validated PaymentRequirements or None if no valid match
        """
        if not required:
            logger.warning("x402_validation_failed", reason="no_requirements_provided")
            return None

        accepts = required.get("accepts") if isinstance(required, dict) else None
        if not accepts:
            logger.warning("x402_validation_failed", reason="no_accepts_array")
            return None

        if payload is None:
            # No payload to validate against, return first requirement
            return PaymentValidator.parse_payment_requirements(accepts[0])

        # Extract payload details for validation
        payload_scheme = getattr(payload, "scheme", None)
        payload_network = getattr(payload, "network", None)
        payload_data = getattr(payload, "payload", {})

        # Extract authorization details (EIP-3009 format)
        authorization = (
            payload_data.get("authorization", {})
            if isinstance(payload_data, dict)
            else {}
        )
        auth_value = authorization.get("value")
        auth_to = authorization.get("to")

        logger.info(
            "x402_payment_validation_started",
            scheme=payload_scheme,
            network=payload_network,
            auth_value=auth_value,
            auth_to=auth_to,
        )

        # Find matching requirement with full validation
        for req in accepts:
            if not isinstance(req, dict):
                continue

            # Step 1: Match scheme and network
            if (
                req.get("scheme") != payload_scheme
                or req.get("network") != payload_network
            ):
                continue

            # Parse requirement for detailed validation
            requirement = PaymentValidator.parse_payment_requirements(req)
            if not requirement:
                continue

            # Step 2: Validate amount (authorization.value >= maxAmountRequired)
            if auth_value is not None:
                try:
                    auth_value_int = int(auth_value)
                    max_amount_int = int(requirement.max_amount_required)

                    if auth_value_int < max_amount_int:
                        logger.warning(
                            "x402_validation_failed",
                            reason="insufficient_amount",
                            auth_value=auth_value_int,
                            required_amount=max_amount_int,
                        )
                        continue
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "x402_validation_failed",
                        reason="invalid_amount_format",
                        error=str(e),
                    )
                    continue

            # Step 3: Validate pay-to address matches merchant address
            if auth_to and requirement.pay_to:
                # Normalize addresses (case-insensitive comparison for Ethereum addresses)
                auth_to_normalized = (
                    auth_to.lower() if isinstance(auth_to, str) else auth_to
                )
                pay_to_normalized = (
                    requirement.pay_to.lower()
                    if isinstance(requirement.pay_to, str)
                    else requirement.pay_to
                )

                if auth_to_normalized != pay_to_normalized:
                    logger.warning(
                        "x402_validation_failed",
                        reason="pay_to_address_mismatch",
                        auth_to=auth_to,
                        expected_pay_to=requirement.pay_to,
                    )
                    continue

            # All validations passed
            logger.info(
                "x402_payment_validation_success",
                scheme=payload_scheme,
                network=payload_network,
            )
            return requirement

        # No matching requirement found
        logger.warning("x402_validation_failed", reason="no_matching_requirement")
        return None

    @staticmethod
    def validate_timeout(
        required_timestamp: float | None, max_timeout_seconds: int = 600
    ) -> tuple[bool, str | None]:
        """Validate payment submission timeout.
        
        Args:
            required_timestamp: Unix timestamp when payment was required
            max_timeout_seconds: Maximum allowed timeout (default: 600s)
            
        Returns:
            Tuple of (is_valid, error_reason)
        """
        if required_timestamp is None:
            return True, None

        current_time = time.time()
        elapsed_time = current_time - required_timestamp

        if elapsed_time > max_timeout_seconds:
            error = f"Payment timeout exceeded: {elapsed_time:.0f}s > {max_timeout_seconds}s"
            logger.warning(
                "x402_payment_timeout_exceeded",
                elapsed_time=elapsed_time,
                max_timeout=max_timeout_seconds,
                required_timestamp=required_timestamp,
            )
            return False, error

        return True, None

    @staticmethod
    async def verify_payment(
        message_metadata: dict[str, Any],
        task_metadata: dict[str, Any],
    ) -> PaymentValidationResult:
        """Verify x402 payment submission.
        
        This is the main entry point for payment validation. It:
        1. Checks if payment was submitted
        2. Parses payload and requirements
        3. Validates timeout
        4. Calls facilitator for verification
        
        Args:
            message_metadata: Metadata from the incoming message
            task_metadata: Metadata from the previous task (contains requirements)
            
        Returns:
            PaymentValidationResult with validation status and details
        """
        # Check if payment was submitted
        payment_status = message_metadata.get(app_settings.x402.meta_status_key)
        if payment_status != app_settings.x402.status_submitted:
            return PaymentValidationResult(
                is_valid=False,
                error_reason="Payment not submitted",
            )

        # Parse payment payload
        payload_data = message_metadata.get(app_settings.x402.meta_payload_key)
        if not payload_data:
            return PaymentValidationResult(
                is_valid=False,
                error_reason="Payment payload missing",
            )

        payment_payload = PaymentValidator.parse_payment_payload(payload_data)
        if not payment_payload:
            return PaymentValidationResult(
                is_valid=False,
                error_reason="Invalid payment payload format",
            )

        # Get payment requirements
        required_data = task_metadata.get(
            app_settings.x402.meta_required_key
        ) or message_metadata.get(app_settings.x402.meta_required_key)

        if not required_data:
            return PaymentValidationResult(
                is_valid=False,
                error_reason="Payment requirements not found",
            )

        payment_requirements = PaymentValidator.select_requirement_from_required(
            required_data, payment_payload
        )

        if not payment_requirements:
            return PaymentValidationResult(
                is_valid=False,
                error_reason="No matching payment requirement found",
                payment_payload=payment_payload,
            )

        # Validate timeout
        required_timestamp = task_metadata.get("x402.payment.required_timestamp")
        max_timeout = getattr(payment_requirements, "max_timeout_seconds", 600)
        timeout_valid, timeout_error = PaymentValidator.validate_timeout(
            required_timestamp, max_timeout
        )

        if not timeout_valid:
            return PaymentValidationResult(
                is_valid=False,
                error_reason=timeout_error,
                payment_payload=payment_payload,
                payment_requirements=payment_requirements,
            )

        # Call facilitator for verification (includes balance check)
        # The facilitator.verify() call validates:
        # 1. Signature validity
        # 2. Authorization format (EIP-3009)
        # 3. Wallet balance (ensures funds are available)
        # 4. Nonce uniqueness
        # This prevents agents from doing work when payment will fail
        try:
            facilitator_client = FacilitatorClient()
            verify_response = await facilitator_client.verify(
                payment_payload, payment_requirements
            )

            if not verify_response.is_valid:
                logger.warning(
                    "x402_facilitator_verify_failed",
                    reason=verify_response.invalid_reason or "unknown",
                    is_valid=verify_response.is_valid,
                )
                return PaymentValidationResult(
                    is_valid=False,
                    error_reason=verify_response.invalid_reason or "verification_failed",
                    payment_payload=payment_payload,
                    payment_requirements=payment_requirements,
                )

            logger.info(
                "x402_facilitator_verify_success",
                is_valid=verify_response.is_valid,
            )

            return PaymentValidationResult(
                is_valid=True,
                payment_payload=payment_payload,
                payment_requirements=payment_requirements,
            )

        except Exception as e:
            logger.error(
                "x402_payment_verification_exception",
                error=str(e),
                error_type=type(e).__name__,
            )
            return PaymentValidationResult(
                is_valid=False,
                error_reason=f"Payment processing error: {e}",
                payment_payload=payment_payload,
                payment_requirements=payment_requirements,
            )
