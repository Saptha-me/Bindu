"""x402 Executor Middleware - Automates payment flow for agents.

Following the official Google a2a-x402 pattern, this middleware catches
x402PaymentRequiredException and handles the verify→process→settle flow automatically.

Architecture:
- Exception-based: Agents throw exceptions to request payment
- Middleware: Catches exceptions and manages payment lifecycle
- State management: Uses A2A task metadata for payment state
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from x402.facilitator import FacilitatorClient
from x402.types import PaymentPayload, PaymentRequirements

from bindu.extensions.x402.core import (
    PaymentStatus,
    settle_payment,
    verify_payment,
    x402Utils,
)
from bindu.extensions.x402.exceptions import x402PaymentRequiredException
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.x402.executor")


class x402PaymentExecutor:
    """Server-side middleware for automatic payment handling.
    
    This executor:
    1. Catches x402PaymentRequiredException from agent logic
    2. Returns payment-required response to client
    3. Verifies payment when submitted
    4. Processes request after verification
    5. Settles payment on-chain after completion
    
    Example:
        >>> executor = x402PaymentExecutor()
        >>> 
        >>> # In your agent logic:
        >>> if is_premium_feature(request):
        ...     raise x402PaymentRequiredException.for_service(
        ...         price="$5.00",
        ...         pay_to_address="0x123...",
        ...         resource="/premium"
        ...     )
        >>> 
        >>> # Executor handles the rest automatically
    """
    
    def __init__(
        self,
        facilitator_client: Optional[FacilitatorClient] = None,
        max_settlement_retries: int = 3,
    ):
        """Initialize payment executor.
        
        Args:
            facilitator_client: Optional facilitator client
            max_settlement_retries: Maximum settlement retry attempts
        """
        self.facilitator_client = facilitator_client or FacilitatorClient()
        self.max_settlement_retries = max_settlement_retries
        self.utils = x402Utils()
    
    async def handle_payment_exception(
        self,
        exception: x402PaymentRequiredException,
        task: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle payment required exception.
        
        Args:
            exception: The payment exception
            task: Current A2A task
            
        Returns:
            Updated task with payment-required state
        """
        logger.info(
            "x402_payment_exception_caught",
            task_id=str(task.get("id")),
            resource=exception.resource,
        )
        
        # Create payment-required metadata
        metadata = self.utils.create_payment_required_metadata(
            exception.payment_requirements
        )
        
        # Update task metadata
        if "metadata" not in task:
            task["metadata"] = {}
        task["metadata"].update({
            app_settings.x402.meta_required_key: exception.payment_requirements
        })
        
        # Create payment-required message
        message = {
            "role": "agent",
            "parts": [
                {
                    "type": "text",
                    "text": str(exception),
                }
            ],
            "metadata": metadata,
        }
        
        return {
            "state": "payment-required",
            "message": message,
            "task": task,
        }
    
    async def verify_and_process(
        self,
        task: Dict[str, Any],
        agent_logic: Any,  # Callable that processes the request
    ) -> Dict[str, Any]:
        """Verify payment and process request.
        
        This method:
        1. Extracts payment payload and requirements from task
        2. Verifies payment with facilitator
        3. If valid, calls agent logic to process request
        4. Returns result
        
        Args:
            task: A2A task with payment submission
            agent_logic: Callable to process the request after verification
            
        Returns:
            Processing result
        """
        # Extract payment info
        payment_payload = self.utils.get_payment_payload(task)
        payment_requirements = self.utils.get_payment_requirements(task)
        
        if not payment_payload or not payment_requirements:
            logger.error(
                "x402_missing_payment_data",
                task_id=str(task.get("id")),
            )
            return {
                "state": "failed",
                "error": "Missing payment data",
            }
        
        # Verify payment
        logger.info(
            "x402_verifying_payment",
            task_id=str(task.get("id")),
        )
        
        verify_response = await verify_payment(
            payment_payload,
            payment_requirements,
            self.facilitator_client,
        )
        
        if not verify_response.is_valid:
            logger.warning(
                "x402_verification_failed",
                task_id=str(task.get("id")),
                reason=verify_response.invalid_reason,
            )
            
            return {
                "state": "failed",
                "error": f"Payment verification failed: {verify_response.invalid_reason}",
            }
        
        logger.info(
            "x402_verification_success",
            task_id=str(task.get("id")),
        )
        
        # Update task with verified status
        verified_metadata = self.utils.create_payment_verified_metadata(payment_payload)
        if "metadata" not in task:
            task["metadata"] = {}
        
        # Add verified metadata to latest message
        if task.get("history"):
            latest_msg = task["history"][-1]
            if "metadata" not in latest_msg:
                latest_msg["metadata"] = {}
            latest_msg["metadata"].update(verified_metadata)
        
        # Process request with agent logic
        logger.info(
            "x402_processing_request",
            task_id=str(task.get("id")),
        )
        
        result = await agent_logic(task)
        
        return result
    
    async def settle_after_completion(
        self,
        task: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Settle payment after successful task completion.
        
        Args:
            task: Completed A2A task
            
        Returns:
            Settlement result metadata
        """
        # Extract payment info
        payment_payload = self.utils.get_payment_payload(task)
        payment_requirements = self.utils.get_payment_requirements(task)
        
        if not payment_payload or not payment_requirements:
            logger.warning(
                "x402_settlement_skipped_no_payment",
                task_id=str(task.get("id")),
            )
            return {}
        
        # Check if already settled
        payment_status = self.utils.get_payment_status(task)
        if payment_status == PaymentStatus.SETTLED:
            logger.info(
                "x402_already_settled",
                task_id=str(task.get("id")),
            )
            return {}
        
        # Settle payment
        logger.info(
            "x402_settling_payment",
            task_id=str(task.get("id")),
        )
        
        settle_response = await settle_payment(
            payment_payload,
            payment_requirements,
            self.facilitator_client,
            max_retries=self.max_settlement_retries,
        )
        
        if settle_response.success:
            logger.info(
                "x402_settlement_success",
                task_id=str(task.get("id")),
                tx_hash=getattr(settle_response, "tx_hash", None),
            )
            
            return self.utils.create_payment_settled_metadata(settle_response)
        else:
            logger.error(
                "x402_settlement_failed",
                task_id=str(task.get("id")),
                error_reason=settle_response.error_reason,
            )
            
            return self.utils.create_payment_failed_metadata(
                settle_response.error_reason or "unknown",
                attempts=self.max_settlement_retries + 1,
            )
    
    def is_payment_flow_active(self, task: Dict[str, Any]) -> bool:
        """Check if payment flow is active for this task.
        
        Args:
            task: A2A task
            
        Returns:
            True if payment flow is active
        """
        task_metadata = task.get("metadata") or {}
        return app_settings.x402.meta_required_key in task_metadata
    
    def get_payment_state(self, task: Dict[str, Any]) -> Optional[str]:
        """Get current payment state for task.
        
        Args:
            task: A2A task
            
        Returns:
            Payment status or None
        """
        return self.utils.get_payment_status(task)


# Decorator for easy payment requirements
def require_payment(
    price: str,
    pay_to_address: str,
    resource: str,
    network: str = "base-sepolia",
    token: str = "USDC",
):
    """Decorator to require payment for a function.
    
    Args:
        price: Price in USD format
        pay_to_address: Merchant's payment address
        resource: Resource identifier
        network: Blockchain network
        token: Token symbol
        
    Example:
        >>> @require_payment(
        ...     price="$5.00",
        ...     pay_to_address="0x123...",
        ...     resource="/premium-feature"
        ... )
        >>> async def premium_feature(request):
        ...     return "Premium content"
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Check if payment context exists (set by executor)
            # If not, raise payment exception
            task = kwargs.get("task") or (args[0] if args else None)
            
            if task and isinstance(task, dict):
                payment_status = x402Utils.get_payment_status(task)
                if payment_status != PaymentStatus.VERIFIED:
                    raise x402PaymentRequiredException.for_service(
                        price=price,
                        pay_to_address=pay_to_address,
                        resource=resource,
                        network=network,
                        token=token,
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
