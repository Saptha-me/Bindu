"""X402 Agent Extension for payment management.

This module provides the X402AgentExtension class that wraps payment configuration
and integrates with the x402 protocol for agent monetization.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Dict, Optional

from bindu.common.protocol.types import AgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from x402.types import PaymentRequirements

from .merchant import create_payment_requirements

logger = get_logger("bindu.x402_agent_extension")


class X402AgentExtension:
    """X402 extension for agent payment management.

    This class manages payment requirements for an agent, including pricing,
    token type, and network configuration. It integrates with the x402 protocol
    to enable decentralized payments on blockchain networks.

    Example:
        >>> x402_ext = X402AgentExtension(
        ...     amount="1000000",  # 1 USDC = $1.00
        ...     token="USDC",
        ...     network="base-sepolia",
        ...     pay_to_address="0x1234..."
        ... )
        >>> payment_req = x402_ext.create_payment_requirements("/generate-quote")
    """

    def __init__(
        self,
        amount: str,
        token: str = "USDC",
        network: str = "base-sepolia",
        pay_to_address: str = "",
        required: bool = True,
        description: Optional[str] = None,
    ):
        """Initialize the X402 extension with payment configuration.

        Args:
            amount: Payment amount in atomic units (e.g., "1000000" for 1 USDC)
                   or USD string (e.g., "$1.00")
            token: Token symbol (default: "USDC")
            network: Blockchain network (default: "base-sepolia")
            pay_to_address: Payment recipient address (required for payments)
            required: Whether payment is mandatory (default: True)
            description: Optional description for agent card

        Raises:
            ValueError: If pay_to_address is empty when required=True
        """
        if required and not pay_to_address:
            raise ValueError("pay_to_address is required when payment is enabled")

        self.amount = amount
        self.token = token
        self.network = network
        self.pay_to_address = pay_to_address
        self.required = required
        self._description = description

        logger.info(
            f"X402 extension initialized: {amount} {token} on {network}, "
            f"pay_to={pay_to_address[:10]}..."
        )

    @property
    def amount_usd(self) -> float:
        """Convert atomic units to USD (assuming USDC with 6 decimals).

        Returns:
            USD amount as float

        Note:
            This is a best-effort conversion. For accurate amounts,
            use the PaymentRequirements object.
        """
        # If already USD format
        if isinstance(self.amount, str) and self.amount.startswith("$"):
            return float(self.amount[1:])

        # Convert atomic units (USDC has 6 decimals)
        if self.token == "USDC":
            try:
                return int(self.amount) / 1_000_000
            except (ValueError, TypeError):
                return 0.0

        # Unknown token
        return 0.0

    @cached_property
    def agent_extension(self) -> AgentExtension:
        """Get the AgentExtension object for agent card capabilities.

        Returns:
            AgentExtension dict for agent card
        """
        description = self._description or (
            f"Requires payment: {self.amount_usd:.2f} USD "
            f"({self.token} on {self.network})"
        )

        return AgentExtension(
            uri=app_settings.x402.extension_uri,
            description=description,
            required=self.required,
            params={
                "amount": self.amount,
                "token": self.token,
                "network": self.network,
                "pay_to_address": self.pay_to_address,
            },
        )

    def create_payment_requirements(
        self,
        resource: str = "/service",
        description: Optional[str] = None,
        mime_type: str = "application/json",
        output_schema: Optional[Any] = None,
        **kwargs: Any,
    ) -> PaymentRequirements:
        """Create PaymentRequirements for this agent.

        Args:
            resource: Resource identifier (default: "/service")
            description: Human-readable description (default: uses extension description)
            mime_type: Expected response content type (default: "application/json")
            output_schema: Optional JSON schema for response
            **kwargs: Additional parameters passed to create_payment_requirements()

        Returns:
            PaymentRequirements object ready for x402 protocol

        Example:
            >>> payment_req = ext.create_payment_requirements(
            ...     resource="/generate-quote",
            ...     description="Generate sunset quote",
            ...     output_schema={"type": "object", "properties": {...}}
            ... )
        """
        desc = description or self._description or f"Payment for {resource}"

        return create_payment_requirements(
            price=self.amount,
            pay_to_address=self.pay_to_address,
            resource=resource,
            network=self.network,
            description=desc,
            mime_type=mime_type,
            output_schema=output_schema,
            **kwargs,
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
            "pay_to_address": self.pay_to_address,
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
            "pay_to_address": self.pay_to_address,
            "required": self.required,
            "amount_usd": self.amount_usd,
        }

    def __repr__(self) -> str:
        """String representation of the extension."""
        return (
            f"X402AgentExtension(amount={self.amount}, "
            f"token={self.token}, network={self.network}, "
            f"pay_to_address={self.pay_to_address[:10]}..., "
            f"required={self.required}, amount_usd=${self.amount_usd:.2f})"
        )
