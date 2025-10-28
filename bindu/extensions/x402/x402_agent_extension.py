"""X402 Agent Extension for payment management.

This module provides the X402AgentExtension class that wraps payment configuration
and integrates with the x402 protocol for agent monetization.
"""

from __future__ import annotations

from functools import cached_property
from typing import Optional

from bindu.common.protocol.types import AgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.x402_agent_extension")


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

    def __repr__(self) -> str:
        """Return string representation of the extension."""
        return (
            f"X402AgentExtension(amount={self.amount}, "
            f"token={self.token}, network={self.network}, "
            f"pay_to_address={self.pay_to_address[:10]}..., "
            f"required={self.required})"
        )

    @cached_property
    def agent_extension(self) -> AgentExtension:
        """Get agent extension configuration for capabilities.

        Returns:
            AgentExtension TypedDict with x402 extension URI
        """
        return AgentExtension(
            uri=app_settings.x402.extension_uri,
        )
