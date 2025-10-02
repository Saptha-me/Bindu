
from typing import Optional, Dict, Any
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    PaymentRequiredResponse,
    VerifyResponse,
    SettleResponse,
    TokenAmount,
    TokenAsset,
    EIP712Domain,
)
from x402.facilitator import FacilitatorClient
from x402.encoding import safe_base64_decode
import json


class X402PaymentExtension:
    """
    X402 Payment Extension for handling payment verification and settlement.
  """
    
    def __init__(
        self,
        pay_to_address: str,
        facilitator_url: Optional[str] = None,
        network: str = "base-sepolia",
    ):
        """
        Initialize the X402 Payment Extension.
        
        Args:
            pay_to_address: Ethereum address to receive payments (required).
            facilitator_url: URL of the x402 facilitator server.
                           Defaults to testnet facilitator if not provided.
            network: Blockchain network to use (default: "base-sepolia").
        """
        self.facilitator_url = facilitator_url or "https://x402.org/facilitator"
        self.pay_to_address = pay_to_address
        self.network = network
        self.facilitator = FacilitatorClient(self.facilitator_url)
    
    async def verify_payment(
        self,
        payment_header: str,
        payment_requirements: PaymentRequirements,
    ) -> VerifyResponse:
        """
        Verify a payment using the x402 facilitator without executing on-chain.
        
        Args:
            payment_header: Base64-encoded X-PAYMENT header from the client request.
            payment_requirements: The payment requirements for the resource.
            
        Returns:
            VerifyResponse with is_valid and invalid_reason fields.
        """
        try:
            payment_data = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload(**payment_data)
            
            verify_response = await self.facilitator.verify(
                payment_payload,
                payment_requirements
            )
            
            return verify_response
            
        except Exception as e:
            return VerifyResponse(
                is_valid=False,
                invalid_reason=f"Verification error: {str(e)}"
            )
    
    async def settle_payment(
        self,
        payment_header: str,
        payment_requirements: PaymentRequirements,
    ) -> SettleResponse:
        """
        Settle a payment on-chain using the x402 facilitator.
        
        Args:
            payment_header: Base64-encoded X-PAYMENT header from the client request.
            payment_requirements: The payment requirements for the resource.
            
        Returns:
            SettleResponse with success, error, tx_hash, and network_id fields.
        """
        try:
            payment_data = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload(**payment_data)
            
            settle_response = await self.facilitator.settle(
                payment_payload,
                payment_requirements
            )
            
            return settle_response
            
        except Exception as e:
            return SettleResponse(
                success=False,
                error=f"Settlement error: {str(e)}",
                tx_hash=None,
                network_id=None
            )
    
    def create_payment_requirements(
        self,
        price: str,
        resource: str,
        description: str,
        mime_type: str = "application/json",
        max_timeout_seconds: int = 60,
        asset_address: Optional[str] = None,
        output_schema: Optional[Dict[str, Any]] = None,
    ) -> PaymentRequirements:
        """
        Create PaymentRequirements for a protected resource.
        
        Args:
            price: Price in USD format (e.g., "$0.001") or atomic units.
            resource: URL path of the resource (e.g., "/api/weather").
            description: Human-readable description of the resource.
            mime_type: MIME type of the resource response.
            max_timeout_seconds: Maximum time in seconds for payment processing.
            asset_address: ERC20 token contract address (defaults to USDC on base-sepolia).
            output_schema: Optional JSON schema describing the response format.
            
        Returns:
            PaymentRequirements object ready to use with verify/settle methods.
        """
        default_asset = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        asset = asset_address or default_asset
        
        if price.startswith("$"):
            dollar_amount = float(price[1:])
            atomic_amount = str(int(dollar_amount * 1_000_000))
        else:
            atomic_amount = price
        
        return PaymentRequirements(
            scheme="exact",
            network=self.network,
            maxAmountRequired=atomic_amount,
            resource=resource,
            description=description,
            mimeType=mime_type,
            payTo=self.pay_to_address,
            maxTimeoutSeconds=max_timeout_seconds,
            asset=asset,
            outputSchema=output_schema,
            extra={"name": "USDC", "version": "2"}
        )


def initialize_x402_payment(
    pay_to_address: str,
    facilitator_url: Optional[str] = None,
    network: str = "base-sepolia",
) -> X402PaymentExtension:
    """
    Initialize and return an X402PaymentExtension instance.
    
    Args:
        pay_to_address: Ethereum address to receive payments.
        facilitator_url: URL of the x402 facilitator server.
        network: Blockchain network to use.
        
    Returns:
        Initialized X402PaymentExtension instance.
    """
    return X402PaymentExtension(
        pay_to_address=pay_to_address,
        facilitator_url=facilitator_url,
        network=network,
    )
