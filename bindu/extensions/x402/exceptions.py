"""x402 Payment Exceptions - Exception-based payment requirements.

Following the official Google a2a-x402 pattern, agents throw exceptions
to dynamically request payments instead of using static configuration.

This approach enables:
- Dynamic pricing based on request parameters
- Per-service payment requirements
- Multiple payment tiers (basic, premium, ultra)
- Clean separation between business logic and payment logic
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from x402.types import PaymentRequirements, Price, TokenAmount, TokenAsset


class x402PaymentRequiredException(Exception):
    """Exception raised when payment is required for a service.
    
    Agents throw this exception to dynamically request payment,
    following the official a2a-x402 pattern.
    
    Example:
        >>> if is_premium_feature(request):
        ...     raise x402PaymentRequiredException.for_service(
        ...         price="$5.00",
        ...         pay_to_address="0x123...",
        ...         resource="/premium-feature"
        ...     )
    """

    def __init__(
        self,
        payment_requirements: PaymentRequirements,
        message: str = "Payment required",
        resource: Optional[str] = None,
    ):
        """Initialize payment required exception.
        
        Args:
            payment_requirements: The payment requirements object
            message: Human-readable message
            resource: Optional resource identifier
        """
        self.payment_requirements = payment_requirements
        self.resource = resource
        super().__init__(message)

    @classmethod
    def for_service(
        cls,
        price: str,
        pay_to_address: str,
        resource: str,
        network: str = "base-sepolia",
        token: str = "USDC",
        description: Optional[str] = None,
    ) -> x402PaymentRequiredException:
        """Create payment exception for a service.
        
        Args:
            price: Price in USD format (e.g., "$5.00" or "5.00")
            pay_to_address: Merchant's payment address
            resource: Resource identifier (e.g., "/premium-feature")
            network: Blockchain network (default: "base-sepolia")
            token: Token symbol (default: "USDC")
            description: Optional service description
            
        Returns:
            x402PaymentRequiredException instance
            
        Example:
            >>> raise x402PaymentRequiredException.for_service(
            ...     price="$10.00",
            ...     pay_to_address="0x123...",
            ...     resource="/ai-generation"
            ... )
        """
        # Parse price string
        price_str = price.replace("$", "").strip()
        
        # Create payment requirements
        payment_req = PaymentRequirements(
            accepts=[
                {
                    "scheme": "eip3009",
                    "network": network,
                    "price": Price(amount=price_str, currency="USD"),
                    "payTo": pay_to_address,
                    "token": TokenAsset(symbol=token),
                }
            ],
            resource=resource,
            description=description or f"Payment required for {resource}",
        )
        
        return cls(
            payment_requirements=payment_req,
            message=f"Payment of {price} required for {resource}",
            resource=resource,
        )

    @classmethod
    def for_tiered_service(
        cls,
        tiers: List[Dict[str, Any]],
        pay_to_address: str,
        resource: str,
        network: str = "base-sepolia",
        token: str = "USDC",
        description: Optional[str] = None,
    ) -> x402PaymentRequiredException:
        """Create payment exception with multiple pricing tiers.
        
        Args:
            tiers: List of tier dicts with 'price' and 'description' keys
            pay_to_address: Merchant's payment address
            resource: Resource identifier
            network: Blockchain network
            token: Token symbol
            description: Optional service description
            
        Returns:
            x402PaymentRequiredException instance
            
        Example:
            >>> raise x402PaymentRequiredException.for_tiered_service(
            ...     tiers=[
            ...         {"price": "$2.00", "description": "Basic tier"},
            ...         {"price": "$5.00", "description": "Premium tier"},
            ...         {"price": "$10.00", "description": "Ultra tier"}
            ...     ],
            ...     pay_to_address="0x123...",
            ...     resource="/ai-service"
            ... )
        """
        accepts = []
        for tier in tiers:
            price_str = tier["price"].replace("$", "").strip()
            accepts.append({
                "scheme": "eip3009",
                "network": network,
                "price": Price(amount=price_str, currency="USD"),
                "payTo": pay_to_address,
                "token": TokenAsset(symbol=token),
                "description": tier.get("description"),
            })
        
        payment_req = PaymentRequirements(
            accepts=accepts,
            resource=resource,
            description=description or f"Payment required for {resource}",
        )
        
        return cls(
            payment_requirements=payment_req,
            message=f"Payment required for {resource} (multiple tiers available)",
            resource=resource,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format for A2A protocol.
        
        Returns:
            Dictionary representation of payment requirements
        """
        return {
            "state": "payment-required",
            "payment_requirements": self.payment_requirements,
            "resource": self.resource,
        }
