"""Unit tests for bindufy x402 capability injection."""

import pytest

from bindu.extensions.x402 import X402AgentExtension
from bindu.settings import app_settings
from bindu.utils import add_extension_to_capabilities

pytestmark = pytest.mark.x402


class TestBindufyX402:
    def test_appends_extension_when_none(self):
        # Create x402 extension
        x402_ext = X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            required=True,
            pay_to_address="0x1234567890123456789012345678901234567890",
        )

        caps = add_extension_to_capabilities(None, x402_ext.agent_extension)
        exts = caps.get("extensions") or []
        assert any(e.get("uri") == app_settings.x402.extension_uri for e in exts)

    def test_appends_extension_to_existing(self):
        # Create x402 extension
        x402_ext = X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            required=True,
            pay_to_address="0x1234567890123456789012345678901234567890",
        )

        caps = add_extension_to_capabilities(
            {"streaming": True, "extensions": []}, x402_ext.agent_extension
        )
        exts = caps.get("extensions") or []
        assert any(e.get("uri") == app_settings.x402.extension_uri for e in exts)
