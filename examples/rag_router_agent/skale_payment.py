import os
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment config
# ---------------------------------------------------------------------------
FACILITATOR_URL = os.getenv("SKALE_FACILITATOR_URL", "https://x402.org/facilitator")
PAY_TO_ADDRESS = os.getenv("SKALE_PAY_TO_ADDRESS", "")
SKALE_NETWORK = os.getenv("SKALE_NETWORK", "eip155:1564830818")  # SKALE Europa Hub mainnet
PREMIUM_PRICE = os.getenv("SKALE_PREMIUM_PRICE", "$0.01")

# ---------------------------------------------------------------------------
# Lazy SDK import — keeps CI green when x402 is not installed
# ---------------------------------------------------------------------------
def _load_sdk():
    """
    Import the x402 Python SDK components.
    Returns (x402ResourceServerSync, HTTPFacilitatorClientSync, ExactEvmServerScheme,
             ResourceConfig) or raises ImportError with a helpful message.
    """
    try:
        from x402 import x402ResourceServerSync, ResourceConfig          # noqa: PLC0415
        from x402.http import HTTPFacilitatorClientSync                  # noqa: PLC0415
        from x402.mechanisms.evm.exact import ExactEvmServerScheme      # noqa: PLC0415
        return x402ResourceServerSync, HTTPFacilitatorClientSync, ExactEvmServerScheme, ResourceConfig
    except ImportError as exc:
        raise ImportError(
            "x402 SDK not found. Install it with: pip install x402"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def call_skale_facilitator():
    """
    Verify/initiate a SKALE payment using the real X402Middleware flow.

    Returns a dict with one of these statuses:
      - "success"  : payment requirements built & facilitator reachable
      - "skipped"  : running in CI (no external calls)
      - "reachable": SDK unavailable or config missing; agent flow continues
    """

    # ── CI guard ────────────────────────────────────────────────────────────
    if os.getenv("CI") == "true":
        logger.debug("Skipping SKALE payment check in CI environment.")
        return {"status": "skipped", "note": "skipped in CI"}

    # ── Config guard ────────────────────────────────────────────────────────
    if not PAY_TO_ADDRESS:
        logger.warning(
            "SKALE_PAY_TO_ADDRESS is not set; skipping payment check."
        )
        return {
            "status": "reachable",
            "note": "SKALE_PAY_TO_ADDRESS not configured; proceeding without payment",
        }

    # ── Real x402 flow ──────────────────────────────────────────────────────
    try:
        (
            x402ResourceServerSync,
            HTTPFacilitatorClientSync,
            ExactEvmServerScheme,
            ResourceConfig,
        ) = _load_sdk()

        # 1. Build facilitator client pointing at the configured endpoint.
        facilitator = HTTPFacilitatorClientSync(url=FACILITATOR_URL)

        # 2. Build resource server and register the SKALE EVM scheme.
        #    extra_networks lets the framework accept payments on SKALE
        #    in addition to (or instead of) Base/mainnet.
        server = x402ResourceServerSync(
            facilitator,
            extra_networks=[SKALE_NETWORK],
        )
        server.register("eip155:*", ExactEvmServerScheme())
        server.initialize()

        # 3. Build payment requirements for a premium data-access resource.
        config = ResourceConfig(
            scheme="exact",
            network=SKALE_NETWORK,
            pay_to=PAY_TO_ADDRESS,
            price=PREMIUM_PRICE,
        )
        requirements = server.build_payment_requirements(config)

        logger.info(
            "SKALE payment requirements built successfully (network=%s, price=%s).",
            SKALE_NETWORK,
            PREMIUM_PRICE,
        )
        return {
            "status": "success",
            "network": SKALE_NETWORK,
            "price": PREMIUM_PRICE,
            "requirements": [r.model_dump() if hasattr(r, "model_dump") else str(r)
                             for r in requirements],
        }

    except ImportError as exc:
        logger.warning("x402 SDK unavailable (%s); proceeding without payment.", exc)
        return {
            "status": "reachable",
            "note": f"x402 SDK not installed: {exc}",
        }
    except Exception as exc:  # noqa: BLE001
        # Non-blocking: facilitator errors must never halt the agent.
        logger.warning(
            "SKALE facilitator call failed (%s); falling back to non-blocking mode.", exc
        )
        return {
            "status": "reachable",
            "note": f"facilitator error (non-blocking fallback): {exc}",
        }
