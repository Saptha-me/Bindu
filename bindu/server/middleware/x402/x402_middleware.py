# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""X402 Payment Middleware for Bindu.

This middleware implements the x402 payment protocol for HTTP requests,
following the official Coinbase x402 specification.

Based on: https://github.com/coinbase/x402/blob/main/python/x402/src/x402/fastapi/middleware.py
"""

from __future__ import annotations

import base64
import json
import os
from typing import TYPE_CHECKING, get_args, cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, HTMLResponse
from x402.common import x402_VERSION, process_price_to_atomic_amount, find_matching_payment_requirements
from x402.encoding import safe_base64_decode
from x402.facilitator import FacilitatorClient, FacilitatorConfig
from x402.paywall import is_browser_request, get_paywall_html
from x402.types import (
    PaymentPayload, 
    SupportedNetworks, 
    PaymentRequirements, 
    x402PaymentRequiredResponse,
    PaywallConfig,
)

from bindu.utils.logging import get_logger
from bindu.extensions.x402 import X402AgentExtension

if TYPE_CHECKING:
    from bindu.common.models import AgentManifest

logger = get_logger("bindu.server.middleware.x402")


class X402Middleware(BaseHTTPMiddleware):
    """Middleware that enforces x402 payment protocol for agent execution.
    
    This middleware:
    1. Checks if the agent requires payment (has execution_cost configured)
    2. Intercepts requests to the A2A endpoint (/)
    3. Returns 402 Payment Required if no X-PAYMENT header is present
    4. Verifies and settles payments if X-PAYMENT header is provided
    5. Allows request to proceed only after successful payment
    
    Attributes:
        manifest: Agent manifest containing payment configuration
        protected_path: Path that requires payment (default: "/" for A2A endpoint)
    """

    def __init__(self,
                 app,
                 manifest: AgentManifest,
                 facilitator_config: FacilitatorConfig,
                 x402_ext: X402AgentExtension,
                 payment_requirements: list[PaymentRequirements]):
        """Initialize X402 middleware.
        
        Args:
            app: ASGI application
            manifest: Agent manifest with x402 configuration
            facilitator_config: Facilitator configuration
            x402_ext: X402AgentExtension instance
            payment_requirements: Pre-configured payment requirements from application
        """
        super().__init__(app)
        self.manifest = manifest
        self.x402_ext = x402_ext
        self.facilitator = FacilitatorClient(facilitator_config)
        self._payment_requirements = payment_requirements
        
        self.protected_path = "/"  # A2A protocol endpoint

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and enforce payment if required.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with payment enforcement or agent execution result
        """

        if (
            not self.x402_ext
            or request.url.path != self.protected_path
            or request.method != "POST"
        ):
            return await call_next(request)

        # Check for X-PAYMENT header
        payment_header = request.headers.get("X-PAYMENT", "")

        if not payment_header:
            # No payment provided - return 402 Payment Required
            logger.info(f"Payment required for {request.url.path} from {request.client.host if request.client else 'unknown'}")

        # Decode and parse payment payload
        try:
            payment_dict = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload(**payment_dict)
        except Exception as e:
            logger.warning(
                f"Invalid X-PAYMENT header from {request.client.host if request.client else 'unknown'}: {e}"
            )
            return self._create_402_response(f"Invalid X-PAYMENT header format: {str(e)}")

        selected_payment_requirements = find_matching_payment_requirements(
            self._payment_requirements, payment_payload
        )

        if not selected_payment_requirements:
            return self._create_402_response("No matching payment requirements found")
        
        try:
            verify_response = await self.facilitator.verify(
                payment_payload, selected_payment_requirements
            )
            logger.info(f"Facilitator verify response: is_valid={verify_response.is_valid}, invalid_reason={verify_response.invalid_reason}")
        except Exception as e:
            logger.error(f"Payment verification error: {e}", exc_info=True)
            return self._create_402_response(f"Payment verification error: {str(e)}")

        if not verify_response.is_valid:
            error_reason = verify_response.invalid_reason or "Unknown error"
            logger.warning(
                f"Payment verification failed from {request.client.host if request.client else 'unknown'}: {error_reason}"
            )
            logger.warning(f"Payment payload: {payment_payload}")
            logger.warning(f"Payment requirements: {selected_payment_requirements}")
            return self._create_402_response(f"Invalid payment: {error_reason}")

        logger.info(
            f"Payment verified for {request.url.path} from {request.client.host if request.client else 'unknown'}"
        )

        # Attach payment details to request for later use
        request.state.payment_payload = payment_payload
        request.state.payment_requirements = selected_payment_requirements
        request.state.verify_response = verify_response

        # Process the request (execute agent)
        response = await call_next(request)

        # Only settle payment if response is successful (2xx status code)
        if 200 <= response.status_code < 300:
            try:
                settle_response = await self.facilitator.settle(
                    payment_payload, selected_payment_requirements
                )

                if settle_response.success:
                    # Add payment confirmation to response headers
                    response.headers["X-PAYMENT-RESPONSE"] = base64.b64encode(
                        settle_response.model_dump_json(by_alias=True).encode("utf-8")
                    ).decode("utf-8")
                    
                    logger.info(
                        f"Payment settled for {request.url.path} from {request.client.host if request.client else 'unknown'}"
                    )
                else:
                    error_reason = settle_response.error_reason or "Unknown error"
                    logger.error(f"Payment settlement failed: {error_reason}")
                    return self._create_402_response(f"Settlement failed: {error_reason}")

            except Exception as e:
                logger.error(f"Payment settlement error: {e}", exc_info=True)
                return self._create_402_response(f"Settlement error: {str(e)}")

        return response

    def _create_402_response(self, error: str) -> JSONResponse:
        """Create a 402 Payment Required response using x402PaymentRequiredResponse.
        
        Args:
            error: Error message to include in response
            
        Returns:
            JSONResponse with 402 status and payment requirements
        """
        # Use the official x402PaymentRequiredResponse type
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=self.payment_requirements,
            error=error,
        ).model_dump(by_alias=True)
        
        # Add agent discovery metadata (Bindu-specific extension)
        response_data["agent"] = {
            "name": self.manifest.name,
            "description": self.manifest.description or "",
            "agentCard": "/.well-known/agent.json",
        }
            
        # Add DID if available (Bindu-specific extension)
        if self.manifest.did_extension and self.manifest.did_extension.did:
            response_data["agent"]["did"] = self.manifest.did_extension.did

        return JSONResponse(
            content=response_data,
            status_code=402,
            headers={"Content-Type": "application/json"},
        )
