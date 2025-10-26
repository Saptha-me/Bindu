"""Unit tests for capabilities utility functions."""

import pytest
from unittest.mock import MagicMock

from bindu.utils.capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)
from bindu.common.protocol.types import AgentExtension


class TestGetX402ExtensionFromCapabilities:
    """Test get_x402_extension_from_capabilities function."""

    def test_returns_none_when_manifest_is_none(self):
        """Test that None is returned when manifest is None."""
        result = get_x402_extension_from_capabilities(None)
        assert result is None

    def test_returns_none_when_no_capabilities(self):
        """Test that None is returned when manifest has no capabilities."""
        manifest = MagicMock()
        del manifest.capabilities  # Remove capabilities attribute
        result = get_x402_extension_from_capabilities(manifest)
        assert result is None

    def test_returns_none_when_capabilities_empty(self):
        """Test that None is returned when capabilities is empty."""
        manifest = MagicMock()
        manifest.capabilities = {}
        result = get_x402_extension_from_capabilities(manifest)
        assert result is None

    def test_returns_none_when_no_extensions(self):
        """Test that None is returned when no extensions in capabilities."""
        manifest = MagicMock()
        manifest.capabilities = {"extensions": []}
        result = get_x402_extension_from_capabilities(manifest)
        assert result is None

    def test_returns_none_when_x402_not_required(self):
        """Test that None is returned when x402 extension is not required."""
        manifest = MagicMock()
        manifest.capabilities = {
            "extensions": [
                {
                    "uri": "https://github.com/google-a2a/a2a-x402/v0.1",
                    "required": False,  # Not required
                    "params": {
                        "amount": "10000",
                        "token": "USDC",
                        "network": "base-sepolia",
                        "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                    },
                }
            ]
        }
        result = get_x402_extension_from_capabilities(manifest)
        assert result is None

    def test_returns_x402_extension_when_configured(self):
        """Test that X402AgentExtension is returned when properly configured."""
        manifest = MagicMock()
        manifest.capabilities = {
            "extensions": [
                {
                    "uri": "https://github.com/google-a2a/a2a-x402/v0.1",
                    "required": True,
                    "params": {
                        "amount": "10000",
                        "token": "USDC",
                        "network": "base-sepolia",
                        "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                    },
                }
            ]
        }
        
        result = get_x402_extension_from_capabilities(manifest)
        
        assert result is not None
        assert result.amount == "10000"
        assert result.token == "USDC"
        assert result.network == "base-sepolia"
        assert result.pay_to_address == "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
        assert result.required is True

    def test_returns_x402_extension_with_defaults(self):
        """Test that X402AgentExtension uses defaults for missing params."""
        manifest = MagicMock()
        manifest.capabilities = {
            "extensions": [
                {
                    "uri": "https://github.com/google-a2a/a2a-x402/v0.1",
                    "required": True,
                    "params": {
                        "amount": "5000",
                        "pay_to_address": "0x1234567890abcdef",
                        # token and network missing - should use defaults
                    },
                }
            ]
        }
        
        result = get_x402_extension_from_capabilities(manifest)
        
        assert result is not None
        assert result.amount == "5000"
        assert result.token == "USDC"  # Default
        assert result.network == "base-sepolia"  # Default
        assert result.pay_to_address == "0x1234567890abcdef"

    def test_ignores_other_extensions(self):
        """Test that other extensions are ignored."""
        manifest = MagicMock()
        manifest.capabilities = {
            "extensions": [
                {
                    "uri": "https://github.com/Saptha-me/saptha_me",
                    "required": True,
                    "params": {"did": "did:bindu:test"},
                },
                {
                    "uri": "https://github.com/google-a2a/a2a-x402/v0.1",
                    "required": True,
                    "params": {
                        "amount": "10000",
                        "token": "USDC",
                        "network": "base-sepolia",
                        "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                    },
                },
            ]
        }
        
        result = get_x402_extension_from_capabilities(manifest)
        
        assert result is not None
        assert result.amount == "10000"


class TestAddExtensionToCapabilities:
    """Test add_extension_to_capabilities function."""

    def test_adds_extension_to_none_capabilities(self):
        """Test adding extension when capabilities is None."""
        extension = AgentExtension(
            uri="https://example.com/extension",
            description="Test extension",
            required=True,
            params={"key": "value"},
        )
        
        result = add_extension_to_capabilities(None, extension)
        
        assert "extensions" in result
        assert len(result["extensions"]) == 1
        assert result["extensions"][0] == extension

    def test_adds_extension_to_existing_capabilities(self):
        """Test adding extension to existing capabilities."""
        existing_ext = AgentExtension(
            uri="https://example.com/existing",
            description="Existing extension",
            required=False,
            params={},
        )
        
        capabilities = {"extensions": [existing_ext]}
        
        new_ext = AgentExtension(
            uri="https://example.com/new",
            description="New extension",
            required=True,
            params={"key": "value"},
        )
        
        result = add_extension_to_capabilities(capabilities, new_ext)
        
        assert "extensions" in result
        assert len(result["extensions"]) == 2
        assert result["extensions"][0] == existing_ext
        assert result["extensions"][1] == new_ext
