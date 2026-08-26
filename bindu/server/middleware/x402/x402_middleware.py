# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""X402 Payment Middleware for Bindu (x402 SDK v2).

Pipeline on a protected request:

1. Parse the JSON-RPC body. Malformed body → 402. (Previously bare
   ``except Exception`` let the request through; CVE-shape "fails-open
   on body parse".)
2. Method check — only methods listed in ``app_settings.x402.protected_methods``
   demand payment.
3. ``X-PAYMENT`` header decoded and parsed via the SDK's
   ``parse_payment_payload`` (handles both v1 and v2 payloads).
4. Match the payload to one of the agent's payment requirements.
5. **Replay-prevention**: claim ``(network, asset, nonce)`` in the nonce
   store before paying for verification. Replays are rejected here, not
   after the facilitator round-trip.
6. **Verification**: ``x402ResourceServer.verify_payment`` delegates the
   EIP-3009 signature recovery and on-chain balance check to the
   configured facilitator. We trust ``result.is_valid``; on False we
   reject without falling through.

Compared with the v0.2.1 middleware this rewrite removes the manual
Web3 connection pool, the manual ``balanceOf`` call, the
silent fall-through when no contract code is found at the asset
address, and the unused signature-verification branch — all of those
responsibilities now live in the facilitator and are exercised by the
SDK's verify path.
"""

from __future__ import annotations

import json
import httpx

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from x402 import X402_VERSION, PaymentPayload, PaymentRequired, PaymentRequirements
from x402.http.utils import safe_base64_decode
from x402.schemas.helpers import parse_payment_payload
from x402.server import x402ResourceServer

from bindu.common.models import AgentManifest, VerifyResponse
from bindu.extensions.x402 import X402AgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .nonce_store import NonceStore

logger = get_logger("bindu.server.middleware.x402")

PROTECTED_PATH = "/"  # A2A protocol endpoint
PROTECTED_METHOD = "POST"

# Buffer added on top of `max_timeout_seconds` when we set the nonce TTL.
# Keeps the dedupe key alive a bit past the EIP-3009 validBefore window so
# that clock skew or a slow settlement doesn't free the slot prematurely.
NONCE_TTL_BUFFER_SECONDS = 60


class X402Middleware(BaseHTTPMiddleware):
    """Enforce x402 payment for the A2A endpoint."""

    def __init__(
        self,
        app,
        manifest: AgentManifest,
        resource_server: x402ResourceServer,
        x402_ext: X402AgentExtension | None,
        payment_requirements: list[PaymentRequirements],
        nonce_store: NonceStore,
    ):
        """Wire the middleware to its ResourceServer, requirements list, and nonce store."""
        super().__init__(app)
        self.manifest = manifest
        self.x402_ext = x402_ext
        self._resource_server = resource_server
        self._payment_requirements = payment_requirements
        self._nonce_store = nonce_store
        self.protected_path = PROTECTED_PATH

    async def dispatch(self, request: Request, call_next) -> Response:
        """Enforce x402 payment on protected methods; pass everything else through."""
        if (
            not self.x402_ext
            or request.url.path != self.protected_path
            or request.method != PROTECTED_METHOD
        ):
            return await call_next(request)

        # 1. Parse body. We narrow the exception class — a bare
        # `except Exception` here lets non-payment errors silently bypass
        # the payment check. JSON-decode failure must be a 402, not an
        # implicit allow.
        body = await request.body()
        try:
            request_data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.info("x402: rejecting request with unparseable body: %s", e)
            return self._create_402_response("Malformed JSON-RPC body")

        method = request_data.get("method", "")

        # Replace request with one that has a re-readable body.
        async def receive():
            return {"type": "http.request", "body": body}

        request = Request(request.scope, receive)

        if method not in app_settings.x402.protected_methods:
            logger.debug("x402: method %r does not require payment", method)
            return await call_next(request)

        # 2. X-PAYMENT header presence.
        payment_header = request.headers.get("X-PAYMENT", "")
        if not payment_header:
            return self._create_402_response("X-PAYMENT header required")

        # 3. Decode and parse payload. The X-PAYMENT header is base64-encoded
        # JSON by convention; the SDK's `parse_payment_payload` itself takes
        # JSON bytes, so we decode first. Both steps' exceptions are caught
        # and surfaced as a 402.
        try:
            decoded = safe_base64_decode(payment_header)
            payload = parse_payment_payload(decoded.encode("utf-8"))
        except (ValueError, TypeError) as e:
            logger.warning("x402: invalid X-PAYMENT payload: %s", e)
            return self._create_402_response(f"Invalid X-PAYMENT header: {e}")

        if not isinstance(payload, PaymentPayload):
            # We only support v2 payloads on the verify side. A v1 payload
            # could be auto-upgraded in future via the SDK's compat shim,
            # but the v1 verification path is unsigned and stays disabled.
            return self._create_402_response(
                "x402 v1 payment payloads are no longer accepted; please re-sign with v2"
            )

        # 4. Match to one of the requirements we publish.
        requirement = self._resource_server.find_matching_requirements(
            self._payment_requirements, payload
        )
        if requirement is None:
            return self._create_402_response("No matching payment requirements found")

        # 5. Replay prevention — claim before verifying.
        # Doing the claim first means a replayed payload doesn't burn a
        # facilitator round-trip; doing it before settlement means we don't
        # rely on the on-chain contract to reject our replays.
        nonce = self._extract_nonce(payload)
        if not nonce:
            return self._create_402_response("Payment payload missing nonce")

        ttl = requirement.max_timeout_seconds + NONCE_TTL_BUFFER_SECONDS
        try:
            claimed = await self._nonce_store.claim(
                payload.get_network(), requirement.asset, nonce, ttl
            )
        except Exception:
            # The nonce store should fail loudly: a silent failure here would
            # collapse straight back into the replay vulnerability we're trying
            # to fix. Reject the request and let the operator investigate.
            logger.exception("x402: nonce store error; rejecting payment")
            return self._create_402_response(
                "Payment validation temporarily unavailable"
            )

        if not claimed:
            logger.warning(
                "x402: replay detected — nonce already used (network=%s, asset=%s, nonce=%s)",
                payload.get_network(),
                requirement.asset,
                nonce,
            )
            return self._create_402_response("Payment nonce already used (replay)")

        # 6. Verify via the configured facilitator. In v2 this performs the
        # EIP-3009 signature recovery, network/scheme match, amount check,
        # and on-chain balance check. We trust the structured response and
        # do NOT fall through on errors.
        try:
            result = await self._resource_server.verify_payment(payload, requirement)
        except Exception:
            logger.exception("x402: facilitator verify_payment raised")
            return self._create_402_response("Payment verification failed")

        if not result.is_valid:
            logger.warning(
                "x402: payment rejected by facilitator: %s (payer=%s)",
                result.invalid_reason,
                result.payer,
            )
            return self._create_402_response(
                f"Invalid payment: {result.invalid_reason or 'unknown reason'}"
            )

        logger.info(
            "x402: payment verified (payer=%s, network=%s, asset=%s)",
            result.payer,
            payload.get_network(),
            requirement.asset,
        )

        # 7. TRACE Trust API Integration
        if app_settings.x402.trace_api_key and result.payer:
            try:
                async with httpx.AsyncClient() as client:
                    trace_resp = await client.post(
                        f"{app_settings.x402.trace_api_url}/v1/score",
                        json={
                            "provider_id": result.payer,
                            "job": {
                                "capability": method,
                            },
                        },
                        headers={"X-API-Key": app_settings.x402.trace_api_key},
                        timeout=5.0,
                    )
                if trace_resp.status_code == 200:
                    trace_result = trace_resp.json()
                    
                    try:
                        score = float(trace_result.get("score", 1.0))
                    except (TypeError, ValueError):
                        score = 1.0
                        
                    decision = trace_result.get("routing_decision")
                    if (
                        decision in ("HOLD", "INVESTIGATE")
                        or score < app_settings.x402.trace_min_score
                    ):
                        logger.warning(
                            "x402: payment rejected by TRACE trust API (payer=%s, score=%s, decision=%s)",
                            result.payer,
                            score,
                            decision,
                        )
                        return self._create_402_response(
                            f"Agent trust score too low: {score}"
                        )
                else:
                    logger.warning(
                        "x402: TRACE API error (status=%s)", trace_resp.status_code
                    )
            except Exception as e:
                logger.warning("x402: TRACE API call failed: %s", e)

        # Attach for the worker — settlement happens at task completion.
        request.state.payment_payload = payload
        request.state.payment_requirements = requirement
        request.state.verify_response = VerifyResponse(
            is_valid=True, invalid_reason=None
        )
        request.state.payer = result.payer

        return await call_next(request)

    @staticmethod
    def _extract_nonce(payload: PaymentPayload) -> str | None:
        """Pull the replay-prevention key out of the payload.

        For EIP-3009 (the only currently-supported scheme) the nonce lives
        at ``payload.payload["authorization"]["nonce"]``. For Permit2 it
        would be at the top level. We tolerate both shapes.
        """
        scheme_payload = payload.payload or {}
        auth = scheme_payload.get("authorization")
        if isinstance(auth, dict) and "nonce" in auth:
            return str(auth["nonce"])
        if "nonce" in scheme_payload:
            return str(scheme_payload["nonce"])
        return None

    def _create_402_response(self, error: str) -> JSONResponse:
        """Build a 402 Payment Required response using the v2 SDK type."""
        response_data = PaymentRequired(
            x402_version=X402_VERSION,
            accepts=self._payment_requirements,
            error=error,
        ).model_dump(by_alias=True)

        # Bindu-specific agent discovery metadata. Not part of the x402 spec,
        # but useful to clients that want to discover the agent card.
        agent_meta: dict[str, str] = {
            "name": self.manifest.name,
            "description": self.manifest.description or "",
            "agentCard": "/.well-known/agent.json",
        }
        if self.manifest.did_extension and self.manifest.did_extension.did:
            agent_meta["did"] = self.manifest.did_extension.did
        response_data["agent"] = agent_meta

        return JSONResponse(
            content=response_data,
            status_code=402,
            headers={"Content-Type": "application/json"},
        )
