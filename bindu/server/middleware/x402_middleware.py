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
from typing import TYPE_CHECKING, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from x402.common import find_matching_payment_requirements
from x402.encoding import safe_base64_decode
from x402.types import PaymentPayload

from bindu.utils.coinbase_utils import CoinbaseFacilitatorClient as FacilitatorClient
from bindu.utils.logging import get_logger

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

    def __init__(self, app, manifest: AgentManifest):
        """Initialize X402 middleware.
        
        Args:
            app: ASGI application
            manifest: Agent manifest with x402 configuration
        """
        super().__init__(app)
        self.manifest = manifest
        self.protected_path = "/"  # A2A protocol endpoint
        
        # Get x402 extension from manifest capabilities
        from bindu.utils import get_x402_extension_from_capabilities
        self.x402_ext = get_x402_extension_from_capabilities(manifest)
        
        if self.x402_ext:
            logger.info(
                f"X402 middleware enabled for agent '{manifest.name}': "
                f"${self.x402_ext.amount_usd:.4f} USD ({self.x402_ext.token} on {self.x402_ext.network})"
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and enforce payment if required.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with payment enforcement or agent execution result
        """
        # Skip payment check if:
        # 1. Agent doesn't require payment
        # 2. Request is not to the protected A2A endpoint
        # 3. Request method is not POST (A2A uses POST)
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
            logger.debug(f"Payment required for {request.url.path} from {request.client.host if request.client else 'unknown'}")
            return self._create_402_response("No X-PAYMENT header provided")

        # Decode and parse payment payload
        try:
            payment_dict = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload(**payment_dict)
        except Exception as e:
            logger.warning(
                f"Invalid X-PAYMENT header from {request.client.host if request.client else 'unknown'}: {e}"
            )
            return self._create_402_response(f"Invalid X-PAYMENT header format: {str(e)}")

        # Create payment requirements for this agent
        payment_requirements = self.x402_ext.create_payment_requirements(
            resource=self.manifest.did_extension.did if self.manifest.did_extension else self.manifest.id,
            description=f"Payment required to use {self.manifest.name}",
        )

        # Find matching payment requirements
        selected_payment_requirements = find_matching_payment_requirements(
            [payment_requirements], payment_payload
        )

        if not selected_payment_requirements:
            logger.warning(
                f"No matching payment requirements from {request.client.host if request.client else 'unknown'}"
            )
            return self._create_402_response("No matching payment requirements found")

        # Verify payment with facilitator
        facilitator = FacilitatorClient(
            manifest_coinbase_config=self.manifest.coinbase_config,
        )

        try:
            verify_response = await facilitator.verify(
                payment_payload, selected_payment_requirements
            )
        except Exception as e:
            logger.error(f"Payment verification error: {e}", exc_info=True)
            return self._create_402_response(f"Payment verification error: {str(e)}")

        if not verify_response.is_valid:
            error_reason = verify_response.invalid_reason or "Unknown error"
            logger.warning(
                f"Payment verification failed from {request.client.host if request.client else 'unknown'}: {error_reason}"
            )
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
                settle_response = await facilitator.settle(
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
        """Create a 402 Payment Required response.
        
        Args:
            error: Error message to include in response
            
        Returns:
            JSONResponse with 402 status and payment requirements
        """
        # Create payment requirements
        payment_requirements = self.x402_ext.create_payment_requirements(
            resource=self.manifest.did_extension.did if self.manifest.did_extension else self.manifest.id,
            description=f"Payment required to use {self.manifest.name}",
        )

        response_data = {
            "x402Version": 1,
            "accepts": [payment_requirements.model_dump(by_alias=True)],
            "error": error,
        }

        return JSONResponse(
            content=response_data,
            status_code=402,
            headers={"Content-Type": "application/json"},
        )
