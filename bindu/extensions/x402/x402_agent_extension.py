"""X402 Agent Extension for Payment Management.

Why is x402 an Extension?
--------------------------
According to the A2A Protocol specification, extensions provide a standardized way to add
optional capabilities to agents without modifying the core protocol. Extensions are declared
in the agent's capabilities and can be discovered by clients.

By implementing x402 as an extension (https://github.com/google-a2a/a2a-x402):
- **Modularity**: Agents can choose whether to require payment
- **Discoverability**: Clients can detect payment support through the agent card
- **Interoperability**: Standard extension format ensures cross-agent compatibility
- **Flexibility**: Different payment mechanisms can coexist as separate extensions

This extension provides comprehensive payment management using the x402 protocol,
enabling agents to monetize their services in a decentralized manner.

This module consolidates all x402 functionality:
- Payment requirements creation and management
- Metadata building and merging for payment states
- Settlement tracking and retry logic
- Extension activation and header management
- Payment verification and validation
"""

from __future__ import annotations

import time
from functools import cached_property
from typing import Any, Dict, Optional

from starlette.requests import Request
from starlette.responses import Response
from x402.common import process_price_to_atomic_amount
from x402.types import PaymentRequirements, Price, SupportedNetworks

from bindu.common.protocol.types import AgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.x402_extension")


class X402AgentExtension:
    """X402 extension for agent payment management.

    This class manages payment requirements for an agent, including pricing,
    token type, and network configuration. It integrates with the x402 protocol
    to enable decentralized payments on blockchain networks.
    """

    def __init__(
        self,
        amount: str,
        token: str = "USDC",
        network: str = "base-sepolia",
        required: bool = True,
        pay_to_address: Optional[str] = None,
    ):
        """Initialize the X402 extension with payment configuration.

        Args:
            amount: Payment amount in atomic units (e.g., "1000000" for 1 USDC)
            token: Token symbol (default: "USDC")
            network: Blockchain network (default: "base-sepolia")
            required: Whether payment is mandatory (default: True)
            pay_to_address: Optional payment recipient address

        Example:
            >>> x402_ext = X402AgentExtension(
            ...     amount="1000000",  # 1 USDC = $1.00
            ...     token="USDC",
            ...     network="base-sepolia",
            ...     required=True,
            ...     pay_to_address="0x1234..."
            ... )
            >>> print(x402_ext.amount_usd)
            1.0
        """
        self.amount = amount
        self.token = token
        self.network = network
        self.required = required
        self.pay_to_address = pay_to_address

        logger.info(
            f"X402 extension initialized: {self.amount_usd} USD ({amount} atomic units) on {network}"
        )

    @property
    def amount_usd(self) -> float:
        """Convert atomic units to USD (assuming USDC with 6 decimals).

        Returns:
            USD amount as float
        """
        if self.token == "USDC":
            return int(self.amount) / 1_000_000
        # Add support for other tokens here
        return 0.0

    @cached_property
    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension object for capabilities.

        Returns:
            AgentExtension dict for agent card
        """
        return AgentExtension(
            uri=app_settings.x402.extension_uri,
            description=f"Requires {self.amount_usd} USD payment in {self.token} on {self.network}",
            required=self.required,
            params={
                "amount": self.amount,
                "token": self.token,
                "network": self.network,
                "pay_to_address": self.pay_to_address,
            },
        )

    def get_payment_info(self) -> Dict[str, Any]:
        """Get payment information for the agent.

        Returns:
            Dict containing payment details
        """
        return {
            "amount": self.amount,
            "amount_usd": self.amount_usd,
            "token": self.token,
            "network": self.network,
            "required": self.required,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dict with all payment configuration
        """
        return {
            "amount": self.amount,
            "token": self.token,
            "network": self.network,
            "required": self.required,
            "amount_usd": self.amount_usd,
        }

    def __repr__(self) -> str:
        """String representation of the extension."""
        return (
            f"X402AgentExtension(amount={self.amount}, "
            f"token={self.token}, network={self.network}, "
            f"required={self.required}, amount_usd=${self.amount_usd})"
        )

    # ========================================================================
    # Payment Requirements Creation (from merchant.py)
    # ========================================================================

    def create_payment_requirements(
        self,
        resource: str,
        description: str = "",
        mime_type: str = "application/json",
        scheme: str = "exact",
        max_timeout_seconds: Optional[int] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Any] = None,
        pay_to_address: Optional[str] = None,
        **kwargs: Any,
    ) -> PaymentRequirements:
        """Create a PaymentRequirements object suitable for x402.

        Args:
            resource: Resource identifier for the payment
            description: Human-readable description of what's being paid for
            mime_type: MIME type of the resource (default: "application/json")
            scheme: Payment scheme (default: "exact")
            max_timeout_seconds: Maximum timeout for payment (default: from settings)
            input_schema: JSON schema describing request parameters (for AI agent discovery)
            output_schema: JSON schema describing response format (for AI agent discovery)
            pay_to_address: Payment recipient address (overrides instance default)
            **kwargs: Additional parameters for PaymentRequirements

        Returns:
            PaymentRequirements object configured for this extension

        Raises:
            ValueError: If pay_to_address not provided and not set in instance

        Example:
            >>> req = x402_ext.create_payment_requirements(
            ...     resource="skill:analyze_data",
            ...     description="Analyze dataset and return insights",
            ...     input_schema={
            ...         "type": "object",
            ...         "properties": {
            ...             "dataset": {"type": "string", "description": "Dataset URL"}
            ...         },
            ...         "required": ["dataset"]
            ...     },
            ...     output_schema={
            ...         "type": "object",
            ...         "properties": {
            ...             "insights": {"type": "array"},
            ...             "summary": {"type": "string"}
            ...         }
            ...     },
            ...     pay_to_address="0x1234..."
            ... )
        """
        # Use provided address or fall back to instance address
        pay_to = pay_to_address or self.pay_to_address
        if not pay_to:
            raise ValueError(
                "pay_to_address must be provided either in __init__ or create_payment_requirements"
            )

        # Use instance timeout or provided timeout
        timeout = max_timeout_seconds or app_settings.x402.max_timeout_seconds

        # Create price from amount and token
        price = Price(amount=self.amount, currency=self.token)

        # Process price to atomic amount
        max_amount_required, asset_address, eip712_domain = process_price_to_atomic_amount(
            price, self.network
        )

        # Build PaymentRequirements with discovery metadata
        payment_req_kwargs = {
            "scheme": scheme,
            "network": SupportedNetworks(self.network),
            "asset": asset_address,
            "pay_to": pay_to,
            "max_amount_required": max_amount_required,
            "resource": resource,
            "description": description,
            "mime_type": mime_type,
            "max_timeout_seconds": timeout,
            "extra": eip712_domain,
            **kwargs,
        }
        
        # Add discovery metadata if provided (for AI agent compatibility)
        if input_schema is not None:
            payment_req_kwargs["input_schema"] = input_schema
        if output_schema is not None:
            payment_req_kwargs["output_schema"] = output_schema
        
        return PaymentRequirements(**payment_req_kwargs)

    @staticmethod
    def merge_task_metadata(task: dict, updates: Dict[str, Any]) -> dict:
        """Merge metadata updates into a task dict in-place and return it.

        Args:
            task: Task dictionary to update
            updates: Metadata updates to merge

        Returns:
            Updated task dictionary

        Example:
            >>> task = {"task_id": "123", "metadata": {"foo": "bar"}}
            >>> X402AgentExtension.merge_task_metadata(task, {"baz": "qux"})
            {'task_id': '123', 'metadata': {'foo': 'bar', 'baz': 'qux'}}
        """
        if "metadata" not in task or task["metadata"] is None:
            task["metadata"] = {}
        task["metadata"].update(updates)
        return task

    @staticmethod
    def build_payment_required_metadata(required: dict) -> dict:
        """Build metadata dict for payment-required state.

        Includes timestamp for timeout validation.

        Args:
            required: Payment requirements dictionary

        Returns:
            Metadata dictionary with payment-required status

        Example:
            >>> metadata = X402AgentExtension.build_payment_required_metadata(
            ...     {"amount": "1000000", "network": "base"}
            ... )
            >>> metadata["x402.payment.status"]
            'payment-required'
        """
        return {
            app_settings.x402.meta_status_key: app_settings.x402.status_required,
            app_settings.x402.meta_required_key: required,
            "x402.payment.required_timestamp": time.time(),
        }

    @staticmethod
    def build_payment_verified_metadata() -> dict:
        """Build metadata dict for payment-verified state.

        Returns:
            Metadata dictionary with payment-verified status
        """
        return {app_settings.x402.meta_status_key: app_settings.x402.status_verified}

    @staticmethod
    def build_payment_completed_metadata(receipt: dict) -> dict:
        """Build metadata dict for payment-completed state.

        Args:
            receipt: Payment receipt dictionary

        Returns:
            Metadata dictionary with payment-completed status and receipt
        """
        return {
            app_settings.x402.meta_status_key: app_settings.x402.status_completed,
            app_settings.x402.meta_receipts_key: [receipt],
        }

    @staticmethod
    def build_payment_failed_metadata(error: str, receipt: Optional[dict] = None) -> dict:
        """Build metadata dict for payment-failed state.

        Args:
            error: Error message describing the failure
            receipt: Optional payment receipt if available

        Returns:
            Metadata dictionary with payment-failed status and error
        """
        md = {
            app_settings.x402.meta_status_key: app_settings.x402.status_failed,
            app_settings.x402.meta_error_key: error,
        }
        if receipt:
            md[app_settings.x402.meta_receipts_key] = [receipt]
        return md

    @staticmethod
    def get_settlement_attempts(metadata: dict) -> int:
        """Get the number of settlement attempts from metadata.

        Args:
            metadata: Task metadata dictionary

        Returns:
            Number of settlement attempts (0 if not present)
        """
        return metadata.get("x402.settlement.attempts", 0)

    @staticmethod
    def increment_settlement_attempts(metadata: dict) -> dict:
        """Increment settlement attempts counter and update timestamp.

        Args:
            metadata: Task metadata dictionary

        Returns:
            Updated metadata dict with incremented attempts
        """
        attempts = X402AgentExtension.get_settlement_attempts(metadata)
        return {
            **metadata,
            "x402.settlement.attempts": attempts + 1,
            "x402.settlement.last_attempt": time.time(),
        }

    @staticmethod
    def build_settlement_retry_metadata(attempts: int, next_retry_after: float) -> dict:
        """Build metadata for settlement retry state.

        Args:
            attempts: Number of settlement attempts
            next_retry_after: Timestamp for next retry

        Returns:
            Metadata dictionary with retry information
        """
        return {
            "x402.settlement.attempts": attempts,
            "x402.settlement.last_attempt": time.time(),
            "x402.settlement.next_retry_after": next_retry_after,
        }

    # ========================================================================
    # Extension Activation (from extension.py)
    # ========================================================================

    @staticmethod
    def is_activation_requested(request: Request) -> bool:
        """Check if the client requested x402 extension activation via header.

        Args:
            request: Starlette request object

        Returns:
            True if x402 extension is requested in X-A2A-Extensions header

        Example:
            >>> from starlette.requests import Request
            >>> # In endpoint handler
            >>> if X402AgentExtension.is_activation_requested(request):
            ...     # Handle x402 payment flow
            ...     pass
        """
        exts = request.headers.get("X-A2A-Extensions", "")
        return app_settings.x402.extension_uri in exts

    @staticmethod
    def add_activation_header(response: Response) -> Response:
        """Echo the x402 extension URI in response header to confirm activation.

        Args:
            response: Starlette response object

        Returns:
            Response with X-A2A-Extensions header added

        Example:
            >>> from starlette.responses import JSONResponse
            >>> response = JSONResponse({"status": "ok"})
            >>> response = X402AgentExtension.add_activation_header(response)
        """
        response.headers["X-A2A-Extensions"] = app_settings.x402.extension_uri
        return response

    @staticmethod
    def get_agent_extension(
        required: bool = False, description: Optional[str] = None
    ) -> AgentExtension:
        """Create an AgentExtension declaration for x402.

        This is a static helper for creating extension declarations without
        instantiating the full X402AgentExtension class.

        Args:
            required: Whether clients must support the extension
            description: Optional description override

        Returns:
            AgentExtension dict for capabilities.extensions

        Example:
            >>> ext = X402AgentExtension.get_agent_extension(
            ...     required=True,
            ...     description="Payment required for premium features"
            ... )
        """
        return AgentExtension(
            uri=app_settings.x402.extension_uri,
            description=description or "Supports x402 A2A agent payments",
            required=required,
            params={},
        )
