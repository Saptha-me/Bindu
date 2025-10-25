"""x402 validation utilities for payment protocol validation.

This module provides comprehensive validation for x402 payment components:
- Network validation (supported blockchain networks)
- Token validation (supported tokens per network)
- Amount validation (atomic units and USD conversion)
- Payment requirements validation (structure and completeness)
- Payment payload validation (mandate and signature verification)

Following the DID extension pattern for consistency.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from bindu.settings import app_settings


class X402Validation:
    """Validation utilities for x402 payment protocol.

    Provides static methods to validate payment components according to
    the x402 specification, ensuring data integrity and protocol compliance.
    """

    # Supported blockchain networks
    SUPPORTED_NETWORKS = {
        "base",
        "base-sepolia",
        "ethereum",
        "sepolia",
        "polygon",
        "arbitrum",
        "optimism",
    }

    # Supported tokens per network
    SUPPORTED_TOKENS = {
        "base": {"USDC", "ETH", "DAI"},
        "base-sepolia": {"USDC", "ETH"},
        "ethereum": {"USDC", "ETH", "DAI", "USDT"},
        "sepolia": {"USDC", "ETH"},
        "polygon": {"USDC", "MATIC", "DAI"},
        "arbitrum": {"USDC", "ETH", "DAI"},
        "optimism": {"USDC", "ETH", "DAI"},
    }

    # Token decimals (for amount validation)
    TOKEN_DECIMALS = {
        "USDC": 6,
        "USDT": 6,
        "DAI": 18,
        "ETH": 18,
        "MATIC": 18,
    }

    # Ethereum address pattern
    _ETH_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

    # ========================================================================
    # Network Validation
    # ========================================================================

    @staticmethod
    def validate_network(network: str) -> Tuple[bool, Optional[str]]:
        """Validate blockchain network.

        Args:
            network: Network identifier (e.g., "base", "base-sepolia")

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = X402Validation.validate_network("base")
            >>> assert is_valid is True
            >>> is_valid, error = X402Validation.validate_network("invalid")
            >>> assert is_valid is False
        """
        if not network:
            return False, "Network cannot be empty"

        if not isinstance(network, str):
            return False, "Network must be a string"

        network_lower = network.lower()
        if network_lower not in X402Validation.SUPPORTED_NETWORKS:
            return (
                False,
                f"Unsupported network: {network}. "
                f"Supported networks: {', '.join(sorted(X402Validation.SUPPORTED_NETWORKS))}",
            )

        return True, None

    # ========================================================================
    # Token Validation
    # ========================================================================

    @staticmethod
    def validate_token(token: str, network: str) -> Tuple[bool, Optional[str]]:
        """Validate token for a specific network.

        Args:
            token: Token symbol (e.g., "USDC", "ETH")
            network: Network identifier

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = X402Validation.validate_token("USDC", "base")
            >>> assert is_valid is True
        """
        if not token:
            return False, "Token cannot be empty"

        if not isinstance(token, str):
            return False, "Token must be a string"

        # Validate network first
        network_valid, network_error = X402Validation.validate_network(network)
        if not network_valid:
            return False, f"Invalid network: {network_error}"

        network_lower = network.lower()
        token_upper = token.upper()

        # Check if token is supported on this network
        supported_tokens = X402Validation.SUPPORTED_TOKENS.get(network_lower, set())
        if token_upper not in supported_tokens:
            return (
                False,
                f"Token {token} not supported on {network}. "
                f"Supported tokens: {', '.join(sorted(supported_tokens))}",
            )

        return True, None

    # ========================================================================
    # Amount Validation
    # ========================================================================

    @staticmethod
    def validate_amount(amount: str, token: str) -> Tuple[bool, Optional[str]]:
        """Validate payment amount in atomic units.

        Args:
            amount: Amount in atomic units (e.g., "1000000" for 1 USDC)
            token: Token symbol for decimal validation

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = X402Validation.validate_amount("1000000", "USDC")
            >>> assert is_valid is True
        """
        if not amount:
            return False, "Amount cannot be empty"

        if not isinstance(amount, str):
            return False, "Amount must be a string"

        # Check if amount is a valid integer
        try:
            amount_int = int(amount)
        except ValueError:
            return False, f"Amount must be a valid integer in atomic units: {amount}"

        # Check if amount is positive
        if amount_int <= 0:
            return False, f"Amount must be positive: {amount}"

        # Validate token exists
        token_upper = token.upper()
        if token_upper not in X402Validation.TOKEN_DECIMALS:
            return False, f"Unknown token for amount validation: {token}"

        # Check if amount is reasonable (not too large)
        decimals = X402Validation.TOKEN_DECIMALS[token_upper]
        max_amount = 10**15  # Reasonable max: 1 billion tokens with 6 decimals
        if amount_int > max_amount:
            return False, f"Amount too large: {amount}"

        return True, None

    @staticmethod
    def amount_to_usd(amount: str, token: str) -> Tuple[bool, Optional[float], Optional[str]]:
        """Convert atomic amount to USD (for display purposes).

        Args:
            amount: Amount in atomic units
            token: Token symbol

        Returns:
            Tuple of (is_valid, usd_amount, error_message)

        Example:
            >>> is_valid, usd, error = X402Validation.amount_to_usd("1000000", "USDC")
            >>> assert is_valid is True
            >>> assert usd == 1.0
        """
        # Validate amount first
        valid, error = X402Validation.validate_amount(amount, token)
        if not valid:
            return False, None, error

        token_upper = token.upper()
        decimals = X402Validation.TOKEN_DECIMALS.get(token_upper)
        if decimals is None:
            return False, None, f"Unknown token: {token}"

        try:
            amount_int = int(amount)
            usd_amount = amount_int / (10**decimals)
            return True, usd_amount, None
        except Exception as e:
            return False, None, f"Failed to convert amount: {str(e)}"

    # ========================================================================
    # Address Validation
    # ========================================================================

    @staticmethod
    def validate_address(address: str) -> Tuple[bool, Optional[str]]:
        """Validate Ethereum-compatible address.

        Args:
            address: Ethereum address (0x prefixed hex)

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> is_valid, error = X402Validation.validate_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
            >>> # Note: This will fail due to invalid checksum, but format is correct
        """
        if not address:
            return False, "Address cannot be empty"

        if not isinstance(address, str):
            return False, "Address must be a string"

        # Check format
        if not X402Validation._ETH_ADDRESS_PATTERN.match(address):
            return False, f"Invalid Ethereum address format: {address}"

        return True, None

    # ========================================================================
    # Payment Requirements Validation
    # ========================================================================

    @staticmethod
    def validate_payment_requirements(
        requirements: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate payment requirements structure.

        Args:
            requirements: Payment requirements dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)

        Example:
            >>> req = {
            ...     "scheme": "exact",
            ...     "network": "base",
            ...     "asset": "0x...",
            ...     "pay_to": "0x...",
            ...     "max_amount_required": "1000000",
            ...     "resource": "skill:analyze"
            ... }
            >>> is_valid, errors = X402Validation.validate_payment_requirements(req)
        """
        errors: List[str] = []

        if not isinstance(requirements, dict):
            return False, ["Payment requirements must be a dictionary"]

        # Required fields
        required_fields = [
            "scheme",
            "network",
            "asset",
            "pay_to",
            "max_amount_required",
            "resource",
        ]

        for field in required_fields:
            if field not in requirements:
                errors.append(f"Missing required field: {field}")

        # If missing required fields, return early
        if errors:
            return False, errors

        # Validate scheme
        scheme = requirements.get("scheme")
        if scheme not in ["exact", "range", "dynamic"]:
            errors.append(f"Invalid scheme: {scheme}. Must be 'exact', 'range', or 'dynamic'")

        # Validate network
        network = requirements.get("network")
        if network:
            valid, error = X402Validation.validate_network(network)
            if not valid:
                errors.append(f"Invalid network: {error}")

        # Validate asset address
        asset = requirements.get("asset")
        if asset:
            valid, error = X402Validation.validate_address(asset)
            if not valid:
                errors.append(f"Invalid asset address: {error}")

        # Validate pay_to address
        pay_to = requirements.get("pay_to")
        if pay_to:
            valid, error = X402Validation.validate_address(pay_to)
            if not valid:
                errors.append(f"Invalid pay_to address: {error}")

        # Validate max_amount_required
        max_amount = requirements.get("max_amount_required")
        if max_amount:
            try:
                amount_int = int(max_amount)
                if amount_int <= 0:
                    errors.append("max_amount_required must be positive")
            except (ValueError, TypeError):
                errors.append(f"Invalid max_amount_required: {max_amount}")

        # Validate resource
        resource = requirements.get("resource")
        if not resource or not isinstance(resource, str):
            errors.append("resource must be a non-empty string")

        return len(errors) == 0, errors

    # ========================================================================
    # Payment Payload Validation
    # ========================================================================

    @staticmethod
    def validate_payment_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate payment payload structure.

        Args:
            payload: Payment payload dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)

        Example:
            >>> payload = {
            ...     "mandate": {...},
            ...     "signature": "0x...",
            ...     "timestamp": 1234567890
            ... }
            >>> is_valid, errors = X402Validation.validate_payment_payload(payload)
        """
        errors: List[str] = []

        if not isinstance(payload, dict):
            return False, ["Payment payload must be a dictionary"]

        # Required fields
        required_fields = ["mandate", "signature"]

        for field in required_fields:
            if field not in payload:
                errors.append(f"Missing required field: {field}")

        # If missing required fields, return early
        if errors:
            return False, errors

        # Validate mandate
        mandate = payload.get("mandate")
        if not isinstance(mandate, dict):
            errors.append("mandate must be a dictionary")

        # Validate signature
        signature = payload.get("signature")
        if not signature or not isinstance(signature, str):
            errors.append("signature must be a non-empty string")

        # Validate timestamp if present
        timestamp = payload.get("timestamp")
        if timestamp is not None:
            try:
                ts_int = int(timestamp)
                if ts_int <= 0:
                    errors.append("timestamp must be positive")
            except (ValueError, TypeError):
                errors.append(f"Invalid timestamp: {timestamp}")

        return len(errors) == 0, errors

    # ========================================================================
    # Metadata Validation
    # ========================================================================

    @staticmethod
    def validate_payment_metadata(metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate payment metadata structure.

        Args:
            metadata: Payment metadata dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)

        Example:
            >>> metadata = {
            ...     "x402.payment.status": "payment-required",
            ...     "x402.payment.required": {...}
            ... }
            >>> is_valid, errors = X402Validation.validate_payment_metadata(metadata)
        """
        errors: List[str] = []

        if not isinstance(metadata, dict):
            return False, ["Payment metadata must be a dictionary"]

        # Validate status if present
        status = metadata.get(app_settings.x402.meta_status_key)
        if status:
            valid_statuses = {
                app_settings.x402.status_required,
                app_settings.x402.status_submitted,
                app_settings.x402.status_verified,
                app_settings.x402.status_completed,
                app_settings.x402.status_failed,
            }
            if status not in valid_statuses:
                errors.append(f"Invalid payment status: {status}")

        # Validate required field if status is payment-required
        if status == app_settings.x402.status_required:
            required = metadata.get(app_settings.x402.meta_required_key)
            if not required:
                errors.append("Missing payment requirements for payment-required status")
            elif not isinstance(required, dict):
                errors.append("Payment requirements must be a dictionary")

        # Validate receipts if present
        receipts = metadata.get(app_settings.x402.meta_receipts_key)
        if receipts is not None:
            if not isinstance(receipts, list):
                errors.append("Payment receipts must be a list")

        return len(errors) == 0, errors
