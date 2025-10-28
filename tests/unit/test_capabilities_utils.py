"""Unit tests for capabilities utility functions."""

from unittest.mock import MagicMock

from bindu.utils.capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)
from bindu.extensions.x402 import X402AgentExtension


class TestGetX402ExtensionFromCapabilities:
    """Test get_x402_extension_from_capabilities function."""

    def test_returns_none_when_no_extensions(self):
        """Test that None is returned when no extensions in capabilities."""
        manifest = MagicMock()
        manifest.capabilities = {"extensions": []}
        result = get_x402_extension_from_capabilities(manifest)
        assert result is None

    def test_returns_x402_extension_when_present(self):
        """Test that X402AgentExtension is returned when present in extensions."""
        manifest = MagicMock()
        x402_ext = X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            required=True,
        )
        manifest.capabilities = {"extensions": [x402_ext]}

        result = get_x402_extension_from_capabilities(manifest)

        assert result is not None
        assert result.amount == "10000"
        assert result.token == "USDC"
        assert result.network == "base-sepolia"
        assert result.pay_to_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        assert result.required is True

    def test_ignores_other_extension_types(self):
        """Test that other extension types are ignored."""
        manifest = MagicMock()
        
        # Mock another extension type
        other_ext = MagicMock()
        other_ext.__class__.__name__ = "DIDAgentExtension"
        
        x402_ext = X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )
        
        manifest.capabilities = {"extensions": [other_ext, x402_ext]}

        result = get_x402_extension_from_capabilities(manifest)

        assert result is not None
        assert result.amount == "10000"


class TestAddExtensionToCapabilities:
    """Test add_extension_to_capabilities function."""

    def test_adds_extension_to_existing_capabilities(self):
        """Test adding extension to existing capabilities."""
        x402_ext = X402AgentExtension(
            amount="10000",
            token="USDC",
            network="base-sepolia",
            pay_to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
        )

        capabilities = {"extensions": []}

        result = add_extension_to_capabilities(capabilities, x402_ext)

        assert "extensions" in result
        assert len(result["extensions"]) == 1
        assert result["extensions"][0] == x402_ext
