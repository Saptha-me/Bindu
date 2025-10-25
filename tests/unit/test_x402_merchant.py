"""Unit tests for x402 payment requirements creation.

The x402 package is mocked in conftest.py to avoid installing external dependencies.
"""

import pytest

from bindu.extensions.x402 import X402AgentExtension

pytestmark = pytest.mark.x402


class TestX402Merchant:
    def test_create_payment_requirements_with_monkeypatch(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        def fake_process_price_to_atomic_amount(price, network):
            return 12345, "0xasset", {"domain": "eip712"}

        # Patch the imported function inside x402_agent_extension module
        monkeypatch.setattr(
            "bindu.extensions.x402.x402_agent_extension.process_price_to_atomic_amount",
            fake_process_price_to_atomic_amount,
        )

        # Create extension instance
        ext = X402AgentExtension(
            amount="1000000", token="USDC", network="base", pay_to_address="0xpayto"
        )

        # Use instance method to create payment requirements
        pr = ext.create_payment_requirements(
            resource="test-resource",
            description="desc",
            mime_type="application/json",
            scheme="exact",
            max_timeout_seconds=30,
            output_schema={"type": "object"},
        )

        data = (
            pr.model_dump(by_alias=True) if hasattr(pr, "model_dump") else pr.__dict__
        )
        assert data["scheme"] == "exact"
        assert str(data["network"]).lower().endswith("base")
        assert data["asset"] == "0xasset"
        assert data["pay_to"] == "0xpayto"
        assert data["max_amount_required"] == 12345
        assert data.get("extra") == {"domain": "eip712"}
