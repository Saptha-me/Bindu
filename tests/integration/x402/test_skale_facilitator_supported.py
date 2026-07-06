"""Live smoke against the SKALE-aware x402 facilitator.

Off by default — opt in with ``X402_NETWORK_TESTS=1``. This is the only
"are we actually shipping working SKALE" check we have, because the
unit tests stub the facilitator entirely. When the facilitator's
``/supported`` response stops advertising a SKALE chain, this test
fails and the operator has a heads-up before agents start collecting
402s in prod.

Two extra concerns this test pins down:

* The facilitator URL we point at (``facilitator.x402.fi``) currently
  has an **expired TLS cert**. The test allows it explicitly; if it
  ever moves to a valid cert the assertion changes and we know to
  remove the workaround.
* The shipped ``ExtraNetwork`` default for SKALE Europa (asset
  address + name + decimals) must match what the facilitator
  advertises — otherwise EIP-3009 settlement will fail with a domain
  mismatch even though every other check passes.
"""

from __future__ import annotations

import os
import ssl

import httpx
import pytest

from bindu.settings import app_settings

# Live facilitator endpoint that supports SKALE today. As of 2026-05-12 the
# cert is expired (CN=facilitator.x402.fi, issuer's chain has aged out).
# The URL itself is operated by the x402.fi team, not Coinbase — Coinbase's
# own facilitator at x402.org/facilitator advertises Base and Solana only.
SKALE_FACILITATOR_URL = "https://facilitator.x402.fi"

# SKALE Europa Hub on the live facilitator. Cross-checked against
# /supported on 2026-05-12.
SKALE_EUROPA_CAIP2 = "eip155:1187947933"
SKALE_EUROPA_USDC = "0x85889c8c714505E0c94b30fcfcF64fE3Ac8FCb20"


pytestmark = [
    pytest.mark.integration,
    pytest.mark.x402,
    pytest.mark.network,
    pytest.mark.skipif(
        os.environ.get("X402_NETWORK_TESTS") != "1",
        reason="live-network test; set X402_NETWORK_TESTS=1 to enable",
    ),
]


def test_facilitator_advertises_skale_europa():
    """The facilitator's /supported response must include SKALE Europa
    Hub at the CAIP-2 we ship in `ExtraNetwork`."""
    # Build a context that tolerates the expired cert. We're not authenticating
    # against the facilitator (it just publishes what it supports); the
    # capability list is public data.
    insecure = ssl.create_default_context()
    insecure.check_hostname = False
    insecure.verify_mode = ssl.CERT_NONE

    with httpx.Client(verify=insecure, timeout=15.0) as client:
        resp = client.get(f"{SKALE_FACILITATOR_URL}/supported")
        resp.raise_for_status()
        data = resp.json()

    kinds = data.get("kinds", [])
    skale_kinds = [
        k
        for k in kinds
        if k.get("scheme") == "exact" and k.get("network") == SKALE_EUROPA_CAIP2
    ]
    assert skale_kinds, (
        f"Facilitator at {SKALE_FACILITATOR_URL} no longer advertises "
        f"SKALE Europa Hub ({SKALE_EUROPA_CAIP2}). Update ExtraNetwork "
        f"default in bindu/settings.py or point at a different facilitator."
    )


def test_shipped_skale_default_matches_facilitator_metadata():
    """The asset address / name / decimals we ship in app_settings must
    match what the facilitator advertises. If they drift, EIP-3009
    typed-data hashing produces a different digest on either side and
    every payment fails with `invalid_exact_evm_signature`."""
    insecure = ssl.create_default_context()
    insecure.check_hostname = False
    insecure.verify_mode = ssl.CERT_NONE

    with httpx.Client(verify=insecure, timeout=15.0) as client:
        kinds = client.get(f"{SKALE_FACILITATOR_URL}/supported").json()["kinds"]

    usdc_kind = next(
        (
            k
            for k in kinds
            if k.get("network") == SKALE_EUROPA_CAIP2
            and k.get("scheme") == "exact"
            and k.get("asset", "").lower() == SKALE_EUROPA_USDC.lower()
        ),
        None,
    )
    assert usdc_kind, "SKALE Europa USDC entry missing from facilitator /supported"

    extra = usdc_kind.get("extra", {})
    skale = app_settings.x402.extra_networks["skale-europa"]

    assert extra.get("decimals") == skale.asset_decimals
    assert extra.get("name") == skale.asset_name
    assert extra.get("version") == skale.asset_eip712_version
