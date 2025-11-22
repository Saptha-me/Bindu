# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
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

import json
from web3 import Web3

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from x402.common import x402_VERSION, find_matching_payment_requirements
from x402.encoding import safe_base64_decode
from x402.facilitator import FacilitatorClient, FacilitatorConfig
from x402.types import (
    PaymentPayload,
    PaymentRequirements,
    x402PaymentRequiredResponse,
)

from bindu.utils.logging import get_logger
from bindu.extensions.x402 import X402AgentExtension
from bindu.settings import app_settings

from bindu.common.models import AgentManifest, VerifyResponse

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

    def __init__(
        self,
        app,
        manifest: AgentManifest,
        facilitator_config: FacilitatorConfig,
        x402_ext: X402AgentExtension | None,
        payment_requirements: list[PaymentRequirements],
    ):
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
        self.facilitator = FacilitatorClient(config=facilitator_config)
        self._payment_requirements = payment_requirements

        self.protected_path = "/"  # A2A protocol endpoint

        # Web3 connection pool for performance optimization
        self._web3_connections: dict[str, Web3] = {}

    def _get_web3_connection(self, network: str) -> tuple[Web3 | None, str | None]:
        """Get or create cached Web3 connection for network.

        This method maintains a connection pool to avoid creating new Web3
        instances for every payment validation request.

        Args:
            network: Network name (e.g., "base-sepolia", "base", "ethereum")

        Returns:
            Tuple of (Web3 instance or None, error message or None)
        """
        # Check if we have a cached connection
        if network in self._web3_connections:
            try:
                # Verify connection is still alive
                self._web3_connections[network].eth.chain_id
                logger.debug(f"Using cached Web3 connection for {network}")
                return self._web3_connections[network], None
            except Exception as e:
                logger.warning(
                    f"Cached connection for {network} failed: {e}. Reconnecting..."
                )
                del self._web3_connections[network]

        # Get RPC URLs for this network
        rpc_urls = app_settings.x402.rpc_urls_by_network.get(network)
        if not rpc_urls:
            error_msg = f"No RPC URLs configured for network: {network}"
            logger.warning(error_msg)
            return None, error_msg

        # Try each RPC URL until one succeeds
        last_error = None
        for rpc_url in rpc_urls:
            try:
                logger.debug(f"Creating new Web3 connection to {rpc_url}")
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))

                # Test connection
                chain_id = w3.eth.chain_id
                logger.info(
                    f"Successfully connected to {network} (chain_id={chain_id}) via {rpc_url}"
                )

                # Cache the connection
                self._web3_connections[network] = w3
                return w3, None

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Failed to connect to {rpc_url}: {e}")
                continue

        # All connections failed
        error_msg = (
            f"Failed to connect to any {network} RPC provider. Last error: {last_error}"
        )
        logger.error(error_msg)
        return None, error_msg

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

        # Check if the JSON-RPC method requires payment
        # Only methods in app_settings.x402.protected_methods require payment
        try:
            body = await request.body()
            request_data = json.loads(body.decode("utf-8"))
            method = request_data.get("method", "")

            # Recreate request with consumed body
            from starlette.requests import Request as StarletteRequest

            async def receive():
                return {"type": "http.request", "body": body}

            request = StarletteRequest(request.scope, receive)

            # Check if method requires payment (configured in settings)
            if method not in app_settings.x402.protected_methods:
                logger.debug(
                    f"Method '{method}' does not require payment, allowing request"
                )
                return await call_next(request)

            logger.debug(
                f"Method '{method}' requires payment, checking X-PAYMENT header"
            )

        except Exception as e:
            logger.warning(f"Error parsing request body: {e}")
            return await call_next(request)

        # Check for X-PAYMENT header
        payment_header = request.headers.get("X-PAYMENT", "")

        if not payment_header:
            # No payment provided - return 402 Payment Required
            logger.info(
                f"Payment required for {request.url.path} from {request.client.host if request.client else 'unknown'}"
            )
            return self._create_402_response("X-PAYMENT header required")

        # Decode and parse payment payload
        try:
            payment_dict = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload.model_validate(payment_dict)
        except Exception as e:
            logger.warning(
                f"Invalid X-PAYMENT header from {request.client.host if request.client else 'unknown'}: {e}"
            )
            return self._create_402_response(
                f"Invalid X-PAYMENT header format: {str(e)}"
            )

        selected_payment_requirements = find_matching_payment_requirements(
            self._payment_requirements, payment_payload
        )

        if not selected_payment_requirements:
            return self._create_402_response("No matching payment requirements found")

        try:
            is_valid, error_reason = await self._validate_payment_manually(
                payment_payload, selected_payment_requirements
            )
            logger.info(
                f"Manual payment validation: is_valid={is_valid}, error_reason={error_reason}"
            )
        except Exception as e:
            logger.error(f"Payment verification error: {e}", exc_info=True)
            return self._create_402_response(f"Payment verification error: {str(e)}")

        if not is_valid:
            logger.warning(
                f"Payment verification failed from {request.client.host if request.client else 'unknown'}: {error_reason}"
            )
            logger.warning(f"Payment payload: {payment_payload}")
            logger.warning(f"Payment requirements: {selected_payment_requirements}")
            return self._create_402_response(f"Invalid payment: {error_reason}")

        logger.info(
            f"Payment verified for {request.url.path} from {request.client.host if request.client else 'unknown'}"
        )

        # Attach payment details to request for later use by the worker
        request.state.payment_payload = payment_payload
        request.state.payment_requirements = selected_payment_requirements
        request.state.verify_response = VerifyResponse(
            is_valid=True, invalid_reason=None
        )

        # Process the request (execute agent)
        # Payment settlement will be handled by ManifestWorker when task completes
        response = await call_next(request)

        return response

    async def _validate_payment_manually(
        self, payment_payload: PaymentPayload, payment_requirements: PaymentRequirements
    ) -> tuple[bool, str | None]:
        """Manually validate payment without consuming nonce.

        This validates:
        1. Payment structure (already validated by Pydantic)
        2. Amount matches requirements
        3. Network matches requirements
        4. Payer has sufficient balance (on-chain check)
        5. EIP-3009 signature is valid (optional)

        Args:
            payment_payload: Payment payload from client
            payment_requirements: Payment requirements for this agent

        Returns:
            Tuple of (is_valid, error_reason)
        """
        try:
            # 1. Check scheme is 'exact'
            if payment_payload.x402_version != 1 or payment_payload.scheme != "exact":
                return False, f"Unsupported payment scheme: {payment_payload.scheme}"

            # 2. Extract authorization details
            if not hasattr(payment_payload.payload, "authorization"):
                return False, "Missing authorization in payment payload"

            auth = payment_payload.payload.authorization

            # 3. Validate amount matches requirements
            payment_value = int(auth.value)
            required_value = int(payment_requirements.max_amount_required)

            if payment_value < required_value:
                return (
                    False,
                    f"Insufficient payment amount: {payment_value} < {required_value}",
                )

            # 4. Validate network matches
            if payment_payload.network != payment_requirements.network:
                return (
                    False,
                    f"Network mismatch: {payment_payload.network} != {payment_requirements.network}",
                )

            # 5. Get RPC URL for network
            w3, connection_error = self._get_web3_connection(payment_payload.network)

            if w3 is None:
                return False, f"Cannot connect to {payment_payload.network} network"

            # 6. Check balance on-chain (optional - skip if token contract unavailable)
            try:
                # Get token contract address
                token_address = Web3.to_checksum_address(payment_requirements.asset)
                logger.info(
                    f"Checking token contract: {token_address} on {payment_payload.network}"
                )

                # Check if contract is deployed at this address
                code = w3.eth.get_code(token_address)
                if code == b"" or code == b"\x00" or code.hex() == "0x":
                    logger.warning(
                        f"No contract found at {token_address} on {payment_payload.network}. "
                        f"This may be an incorrect token address. Skipping balance check."
                    )
                else:
                    logger.info(
                        f"Contract found at {token_address}, bytecode length: {len(code)} bytes"
                    )

                    # ERC-20 balanceOf ABI
                    balance_of_abi = [
                        {
                            "constant": True,
                            "inputs": [{"name": "_owner", "type": "address"}],
                            "name": "balanceOf",
                            "outputs": [{"name": "balance", "type": "uint256"}],
                            "type": "function",
                        }
                    ]

                    token_contract = w3.eth.contract(
                        address=token_address, abi=balance_of_abi
                    )

                    # Check payer balance
                    payer_address = Web3.to_checksum_address(auth.from_)
                    balance = token_contract.functions.balanceOf(payer_address).call()

                    if balance < payment_value:
                        return (
                            False,
                            f"Insufficient balance: {balance} < {payment_value} (required)",
                        )

                    logger.info(
                        f"Payment validation passed: network={payment_payload.network}, "
                        f"token={token_address}, amount={payment_value}, balance={balance}, payer={payer_address}"
                    )

            except Exception as balance_error:
                # Balance check failed - log warning but continue validation
                logger.warning(
                    f"Could not verify on-chain balance for {payment_requirements.asset}: {balance_error}. "
                    f"Skipping balance check and allowing payment based on signature verification only."
                )
                logger.info(
                    f"Payment validation passed (without balance check): network={payment_payload.network}, "
                    f"token={payment_requirements.asset}, amount={payment_value}, payer={auth.from_}"
                )

            return True, None

        except Exception as e:
            logger.error(f"Payment validation error: {e}", exc_info=True)
            return False, f"Validation error: {str(e)}"

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
            accepts=self._payment_requirements,
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
