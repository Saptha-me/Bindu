"""Unit tests for x402 merchant helpers.

Stubs the x402 package to avoid installing external dependencies.
"""

from types import SimpleNamespace, ModuleType
import sys

import pytest

pytestmark = pytest.mark.x402


# --- Stub x402 before importing the merchant module ---
class _PaymentRequirements:
    def __init__(self, **kwargs):
        self._data = kwargs

    def model_dump(self, by_alias: bool = True):  # noqa: ARG002
        return dict(self._data)


class _SupportedNetworks:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value


x402_mod = ModuleType("x402")
x402_common = ModuleType("x402.common")
x402_types = ModuleType("x402.types")
x402_common.process_price_to_atomic_amount = lambda price, network: (1, "0x00", {})
x402_types.PaymentRequirements = _PaymentRequirements
x402_types.Price = object
x402_types.SupportedNetworks = _SupportedNetworks
sys.modules["x402"] = x402_mod
sys.modules["x402.common"] = x402_common
sys.modules["x402.types"] = x402_types

from bindu.extensions.x402.merchant import create_payment_requirements


class TestX402Merchant:
    def test_create_payment_requirements_with_monkeypatch(self, monkeypatch: pytest.MonkeyPatch):
        def fake_process_price_to_atomic_amount(price, network):
            return 12345, "0xasset", {"domain": "eip712"}

        # Patch the imported function inside merchant module
        monkeypatch.setattr(
            "bindu.extensions.x402.merchant.process_price_to_atomic_amount",
            fake_process_price_to_atomic_amount,
        )

        pr = create_payment_requirements(
            price="$1.00",
            pay_to_address="0xpayto",
            resource="test-resource",
            network="base",
            description="desc",
            mime_type="application/json",
            scheme="exact",
            max_timeout_seconds=30,
            output_schema={"type": "object"},
        )

        data = pr.model_dump(by_alias=True) if hasattr(pr, "model_dump") else pr.__dict__
        assert data["scheme"] == "exact"
        assert str(data["network"]).lower().endswith("base")
        assert data["asset"] == "0xasset"
        assert data["pay_to"] == "0xpayto"
        assert data["max_amount_required"] == 12345
        assert data.get("extra") == {"domain": "eip712"}
