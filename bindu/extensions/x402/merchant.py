"""Helpers for creating x402 PaymentRequirements in Bindu.

Use this when your agent needs to ask for payment by returning a structured
response with state: "payment-required" and a `required` object.
"""

from __future__ import annotations

from typing import Any, Optional

from x402.common import process_price_to_atomic_amount
from x402.types import PaymentRequirements, Price, SupportedNetworks


def create_payment_requirements(
    price: Price,
    pay_to_address: str,
    resource: str,
    network: str = "base",
    description: str = "",
    mime_type: str = "application/json",
    scheme: str = "exact",
    max_timeout_seconds: int = 600,
    output_schema: Optional[Any] = None,
    **kwargs: Any,
) -> PaymentRequirements:
    """Create a PaymentRequirements object suitable for x402.

    Price can be money (e.g., "$1.00") or a TokenAmount.
    """
    max_amount_required, asset_address, eip712_domain = process_price_to_atomic_amount(
        price, network
    )

    return PaymentRequirements(
        scheme=scheme,
        network=SupportedNetworks(network),
        asset=asset_address,
        pay_to=pay_to_address,
        max_amount_required=max_amount_required,
        resource=resource,
        description=description,
        mime_type=mime_type,
        max_timeout_seconds=max_timeout_seconds,
        output_schema=output_schema,
        extra=eip712_domain,
        **kwargs,
    )
