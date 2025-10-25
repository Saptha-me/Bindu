"""x402 Core Protocol - Pure functions for payment operations.

Following the official Google a2a-x402 "functional core, imperative shell" architecture.
This module provides implementation-agnostic core protocol functions.

Core Functions:
- create_payment_requirements: Create payment requirements from exception
- verify_payment: Verify payment submission
- settle_payment: Settle payment on-chain
- State management utilities for A2A task metadata
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

from x402.facilitator import FacilitatorClient
from x402.types import PaymentPayload, PaymentRequirements, SettleResponse, VerifyResponse

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.x402.core")


# Extension Constants
X402_EXTENSION_URI = "https://github.com/google-agentic-commerce/a2a-x402"


class PaymentStatus:
    """Payment status constants for A2A task metadata."""
    
    REQUIRED = "payment-required"
    SUBMITTED = "payment-submitted"
    VERIFIED = "payment-verified"
    SETTLED = "payment-settled"
    FAILED = "payment-failed"


def create_payment_requirements(
    price: str,
    pay_to_address: str,
    resource: str,
    network: str = "base-sepolia",
    token: str = "USDC",
    description: Optional[str] = None,
) -> PaymentRequirements:
    """Create payment requirements for a service.
    
    Args:
        price: Price in USD format (e.g., "$5.00" or "5.00")
        pay_to_address: Merchant's payment address
        resource: Resource identifier
        network: Blockchain network
        token: Token symbol
        description: Optional description
        
    Returns:
        PaymentRequirements object
    """
    from x402.types import Price, TokenAsset
    
    price_str = price.replace("$", "").strip()
    
    return PaymentRequirements(
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


async def verify_payment(
    payment_payload: PaymentPayload,
    payment_requirements: PaymentRequirements,
    facilitator_client: Optional[FacilitatorClient] = None,
) -> VerifyResponse:
    """Verify payment submission against requirements.
    
    Args:
        payment_payload: Payment payload from client
        payment_requirements: Payment requirements from merchant
        facilitator_client: Optional facilitator client (creates new if None)
        
    Returns:
        VerifyResponse with validation result
    """
    if facilitator_client is None:
        facilitator_client = FacilitatorClient()
    
    logger.info(
        "x402_verify_payment",
        scheme=getattr(payment_payload, "scheme", None),
        network=getattr(payment_payload, "network", None),
    )
    
    return await facilitator_client.verify(payment_payload, payment_requirements)


async def settle_payment(
    payment_payload: PaymentPayload,
    payment_requirements: PaymentRequirements,
    facilitator_client: Optional[FacilitatorClient] = None,
    max_retries: int = 3,
) -> SettleResponse:
    """Settle payment on-chain with retry logic.
    
    Args:
        payment_payload: Payment payload from client
        payment_requirements: Payment requirements from merchant
        facilitator_client: Optional facilitator client
        max_retries: Maximum number of retry attempts
        
    Returns:
        SettleResponse with settlement result
    """
    if facilitator_client is None:
        facilitator_client = FacilitatorClient()
    
    logger.info(
        "x402_settle_payment",
        scheme=getattr(payment_payload, "scheme", None),
        network=getattr(payment_payload, "network", None),
    )
    
    # Initial settlement attempt
    response = await facilitator_client.settle(payment_payload, payment_requirements)
    
    if response.success:
        logger.info(
            "x402_settle_success",
            tx_hash=getattr(response, "tx_hash", None),
            network_id=getattr(response, "network_id", None),
        )
        return response
    
    # Retry logic with exponential backoff
    for attempt in range(1, max_retries + 1):
        backoff_seconds = 2 ** attempt  # 2, 4, 8 seconds
        
        logger.warning(
            "x402_settle_retry",
            attempt=attempt,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            error_reason=response.error_reason,
        )
        
        await asyncio.sleep(backoff_seconds)
        
        response = await facilitator_client.settle(payment_payload, payment_requirements)
        
        if response.success:
            logger.info(
                "x402_settle_success_after_retry",
                attempt=attempt,
                tx_hash=getattr(response, "tx_hash", None),
            )
            return response
    
    logger.error(
        "x402_settle_max_retries_exceeded",
        total_attempts=max_retries + 1,
        error_reason=response.error_reason,
    )
    
    return response


# Import asyncio here to avoid circular imports
import asyncio


class x402Utils:
    """State management utilities for A2A task metadata.
    
    Provides helper functions to read/write payment state in A2A task metadata,
    following the official a2a-x402 pattern.
    """
    
    @staticmethod
    def get_payment_status(task: Dict[str, Any]) -> Optional[str]:
        """Get payment status from task metadata.
        
        Args:
            task: A2A task object
            
        Returns:
            Payment status string or None
        """
        latest_msg = (task.get("history") or [])[-1] if task.get("history") else None
        if not latest_msg:
            return None
        
        metadata = latest_msg.get("metadata") or {}
        return metadata.get(app_settings.x402.meta_status_key)
    
    @staticmethod
    def get_payment_requirements(task: Dict[str, Any]) -> Optional[PaymentRequirements]:
        """Get payment requirements from task metadata.
        
        Args:
            task: A2A task object
            
        Returns:
            PaymentRequirements object or None
        """
        task_metadata = task.get("metadata") or {}
        required_data = task_metadata.get(app_settings.x402.meta_required_key)
        
        if not required_data:
            return None
        
        # Parse PaymentRequirements from dict
        if isinstance(required_data, dict):
            return PaymentRequirements(**required_data)
        
        return required_data
    
    @staticmethod
    def get_payment_payload(task: Dict[str, Any]) -> Optional[PaymentPayload]:
        """Get payment payload from task metadata.
        
        Args:
            task: A2A task object
            
        Returns:
            PaymentPayload object or None
        """
        latest_msg = (task.get("history") or [])[-1] if task.get("history") else None
        if not latest_msg:
            return None
        
        metadata = latest_msg.get("metadata") or {}
        payload_data = metadata.get(app_settings.x402.meta_payload_key)
        
        if not payload_data:
            return None
        
        # Parse PaymentPayload from dict
        if isinstance(payload_data, dict):
            return PaymentPayload(**payload_data)
        
        return payload_data
    
    @staticmethod
    def create_payment_required_metadata(
        payment_requirements: PaymentRequirements,
    ) -> Dict[str, Any]:
        """Create metadata for payment-required state.
        
        Args:
            payment_requirements: Payment requirements object
            
        Returns:
            Metadata dictionary
        """
        return {
            app_settings.x402.meta_status_key: PaymentStatus.REQUIRED,
            app_settings.x402.meta_required_key: payment_requirements,
        }
    
    @staticmethod
    def create_payment_verified_metadata(
        payment_payload: PaymentPayload,
    ) -> Dict[str, Any]:
        """Create metadata for payment-verified state.
        
        Args:
            payment_payload: Payment payload object
            
        Returns:
            Metadata dictionary
        """
        return {
            app_settings.x402.meta_status_key: PaymentStatus.VERIFIED,
            app_settings.x402.meta_payload_key: payment_payload,
        }
    
    @staticmethod
    def create_payment_settled_metadata(
        settle_response: SettleResponse,
    ) -> Dict[str, Any]:
        """Create metadata for payment-settled state.
        
        Args:
            settle_response: Settlement response
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            app_settings.x402.meta_status_key: PaymentStatus.SETTLED,
            "x402.settlement.success": True,
            "x402.settlement.timestamp": time.time(),
        }
        
        if hasattr(settle_response, "tx_hash") and settle_response.tx_hash:
            metadata["x402.settlement.tx_hash"] = settle_response.tx_hash
        
        if hasattr(settle_response, "network_id") and settle_response.network_id:
            metadata["x402.settlement.network_id"] = settle_response.network_id
        
        return metadata
    
    @staticmethod
    def create_payment_failed_metadata(
        error_reason: str,
        attempts: int = 1,
    ) -> Dict[str, Any]:
        """Create metadata for payment-failed state.
        
        Args:
            error_reason: Reason for failure
            attempts: Number of attempts made
            
        Returns:
            Metadata dictionary
        """
        return {
            app_settings.x402.meta_status_key: PaymentStatus.FAILED,
            "x402.settlement.success": False,
            "x402.settlement.error_reason": error_reason,
            "x402.settlement.attempts": attempts,
            "x402.settlement.timestamp": time.time(),
        }


def get_extension_declaration() -> Dict[str, Any]:
    """Get x402 extension declaration for agent card.
    
    Returns:
        Extension declaration dictionary
    """
    return {
        "uri": X402_EXTENSION_URI,
        "required": False,  # Extension is optional
    }


def check_extension_activation(task: Dict[str, Any]) -> bool:
    """Check if x402 extension is activated for a task.
    
    Args:
        task: A2A task object
        
    Returns:
        True if extension is activated
    """
    task_metadata = task.get("metadata") or {}
    return app_settings.x402.meta_required_key in task_metadata
