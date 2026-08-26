"""Minimal focused tests for ConfigValidator."""

import copy
from typing import ClassVar

import pytest

from bindu.common.protocol.types import AgentTrustConfig
from bindu.penguin.config_validator import ConfigError, ConfigValidator


class TestConfigValidator:
    """Test ConfigValidator with strong test cases."""

    def test_validate_and_process_valid_config(self):
        """Test validation and processing of valid config."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

        result = ConfigValidator.validate_and_process(config)

        assert result is not None
        assert result["name"] == "TestAgent"
        assert result["author"] == "test@example.com"

    def test_validate_missing_required_field_raises(self):
        """Test validation fails when required field is missing."""
        config = {"version": "1.0.0"}

        with pytest.raises(ConfigError, match="author"):
            ConfigValidator.validate_and_process(config)

    def test_validate_missing_deployment_url_raises(self):
        """Test validation fails when deployment.url is missing."""
        config = {"author": "test@example.com", "name": "TestAgent", "deployment": {}}

        with pytest.raises(ConfigError, match="deployment.url"):
            ConfigValidator.validate_and_process(config)

    def test_validate_invalid_deployment_url_scheme_raises(self):
        """Test validation fails when deployment.url has invalid scheme."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "ftp://localhost:3773"},
        }

        with pytest.raises(ConfigError, match="valid http\(s\) URL"):
            ConfigValidator.validate_and_process(config)

    def test_validate_invalid_deployment_url_format_raises(self):
        """Test validation fails when deployment.url is not a valid URL."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "localhost:3773"},
        }

        with pytest.raises(ConfigError, match="deployment.url"):
            ConfigValidator.validate_and_process(config)

    def test_defaults_are_applied(self):
        """Test that default values are applied to config."""
        config = {
            "author": "test@example.com",
            "name": "TestAgent",
            "deployment": {"url": "http://localhost:3773"},
        }

        result = ConfigValidator.validate_and_process(config)

        assert result["kind"] == "agent"
        assert result["num_history_sessions"] == 10
        assert result["debug_mode"] is False


class TestAgentTrustValidation:
    """Tests for agent_trust configuration validation."""

    BASE_CONFIG: ClassVar[dict] = {
        "author": "test@example.com",
        "name": "TestAgent",
        "deployment": {"url": "http://localhost:3773"},
    }

    def _config_with_trust(self, trust):
        config = copy.deepcopy(self.BASE_CONFIG)
        config["agent_trust"] = trust
        return config

    def test_valid_agent_trust_hydra(self):
        """Valid agent_trust with hydra provider passes validation."""
        config = self._config_with_trust({"identity_provider": "hydra"})
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["identity_provider"] == "hydra"

    def test_valid_agent_trust_custom_provider(self):
        """Valid agent_trust with custom provider passes validation."""
        config = self._config_with_trust({"identity_provider": "custom"})
        result = ConfigValidator.validate_and_process(config)
        assert result["agent_trust"]["identity_provider"] == "custom"

    def test_valid_agent_trust_with_all_fields(self):
        """Valid agent_trust with all optional fields passes validation and round-trips."""
        trust = {
            "identity_provider": "hydra",
            "inherited_roles": [],
            "certificate": "-----BEGIN CERTIFICATE-----",
            "certificate_fingerprint": "sha256:abc123",
            "creator_id": "user-42",
            "creation_timestamp": 1700000000,
            "trust_verification_required": True,
            "allowed_operations": {"read": "viewer", "write": "editor"},
        }
        result = ConfigValidator.validate_and_process(self._config_with_trust(trust))
        # Verify all fields survive validation by round-tripping through AgentTrustConfig
        AgentTrustConfig(**result["agent_trust"])

    def test_agent_trust_none_is_allowed(self):
        """agent_trust defaults to None and is accepted."""
        result = ConfigValidator.validate_and_process(self.BASE_CONFIG)
        assert result["agent_trust"] is None

    def test_agent_trust_not_dict_raises(self):
        """Non-dict agent_trust raises ValueError."""
        with pytest.raises(ValueError, match="agent_trust"):
            ConfigValidator.validate_and_process(self._config_with_trust("hydra"))

    def test_agent_trust_missing_identity_provider_raises(self):
        """Missing identity_provider raises ValueError."""
        with pytest.raises(ValueError, match="agent_trust"):
            ConfigValidator.validate_and_process(self._config_with_trust({}))

    def test_agent_trust_invalid_identity_provider_raises(self):
        """Unknown identity_provider raises ValueError."""
        with pytest.raises(ValueError, match="agent_trust"):
            ConfigValidator.validate_and_process(
                self._config_with_trust({"identity_provider": "keycloak"})
            )

    def test_agent_trust_invalid_certificate_type_raises(self):
        """Non-string certificate raises ValueError."""
        with pytest.raises(ValueError, match="agent_trust"):
            ConfigValidator.validate_and_process(
                self._config_with_trust(
                    {"identity_provider": "hydra", "certificate": 12345}
                )
            )

    def test_agent_trust_invalid_allowed_operations_trust_level_raises(self):
        """Invalid TrustLevel in allowed_operations raises ValueError."""
        with pytest.raises(ValueError, match="agent_trust"):
            ConfigValidator.validate_and_process(
                self._config_with_trust(
                    {
                        "identity_provider": "hydra",
                        "allowed_operations": {"read": "superuser"},
                    }
                )
            )
