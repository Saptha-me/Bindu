"""Unit tests for bindufy x402 capability injection."""

import pytest

from bindu.extensions.x402 import X402AgentExtension
from bindu.utils import add_extension_to_capabilities

pytestmark = pytest.mark.x402


class TestBindufyX402:
    def test_appends_extension_to_existing(self):
        """Test adding X402 extension to existing capabilities."""
        x402_ext = X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            required=True,
            pay_to_address="0x1234567890123456789012345678901234567890",
        )

        caps = add_extension_to_capabilities(
            {"streaming": True, "extensions": []}, x402_ext
        )

        assert "extensions" in caps
        assert len(caps["extensions"]) == 1
        assert caps["extensions"][0] == x402_ext
