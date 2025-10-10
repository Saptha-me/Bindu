"""Unit tests for Configuration Validator."""

import json
import tempfile
from pathlib import Path

import pytest

from bindu.penguin.config_validator import ConfigValidator, load_and_validate_config


class TestConfigValidator:
    """Test suite for ConfigValidator."""

    @pytest.fixture
    def minimal_config(self):
        """Minimal valid configuration."""
        return {
            "author": "test@example.com",
            "capabilities": {
                "streaming": True,
                "push_notifications": False,
            },
            "deployment": {
                "host": "localhost",
                "port": 3773,
            },
            "storage": {
                "type": "memory",
            },
            "scheduler": {
                "type": "memory",
            },
        }

    @pytest.fixture
    def full_config(self):
        """Full configuration with all optional fields."""
        return {
            "author": "test@example.com",
            "name": "test_agent",
            "description": "A test agent",
            "version": "2.0.0",
            "recreate_keys": False,
            "skills": [
                {"name": "skill1", "description": "First skill"},
                {"name": "skill2", "description": "Second skill"},
            ],
            "kind": "agent",
            "debug_mode": True,
            "debug_level": 2,
            "monitoring": True,
            "telemetry": False,
            "num_history_sessions": 20,
            "documentation_url": "https://docs.example.com",
            "extra_metadata": {"key": "value"},
            "capabilities": {
                "streaming": True,
                "push_notifications": True,
            },
            "deployment": {
                "host": "0.0.0.0",
                "port": 8080,
            },
            "storage": {
                "type": "memory",
            },
            "scheduler": {
                "type": "memory",
            },
        }

    def test_validate_minimal_config(self, minimal_config):
        """Test validation of minimal configuration."""
        result = ConfigValidator.validate_and_process(minimal_config)

        assert result["author"] == "test@example.com"
        assert "capabilities" in result
        assert result["capabilities"]["streaming"] is True
        # Check defaults are applied
        assert result["name"] == "bindu-agent"
        assert result["version"] == "1.0.0"
        assert result["recreate_keys"] is True

    def test_validate_full_config(self, full_config):
        """Test validation of full configuration."""
        result = ConfigValidator.validate_and_process(full_config)

        assert result["author"] == "test@example.com"
        assert result["name"] == "test_agent"
        assert result["version"] == "2.0.0"
        assert result["recreate_keys"] is False
        assert result["debug_mode"] is True
        assert result["debug_level"] == 2
        assert len(result["skills"]) == 2
        assert result["skills"][0]["name"] == "skill1"

    def test_missing_required_field(self):
        """Test error when required field is missing."""
        config = {
            "author": "test@example.com",
            # Missing capabilities, deployment, storage, scheduler
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            ConfigValidator.validate_and_process(config)

    def test_missing_multiple_required_fields(self):
        """Test error message lists all missing fields."""
        config = {
            "author": "test@example.com",
        }

        with pytest.raises(ValueError) as exc_info:
            ConfigValidator.validate_and_process(config)

        error_msg = str(exc_info.value)
        assert "capabilities" in error_msg
        assert "deployment" in error_msg
        assert "storage" in error_msg
        assert "scheduler" in error_msg

    def test_process_skills_from_dict(self, minimal_config):
        """Test processing skills from dictionary list."""
        minimal_config["skills"] = [
            {"name": "skill1", "description": "First skill"},
            {"name": "skill2", "description": "Second skill"},
        ]

        result = ConfigValidator.validate_and_process(minimal_config)

        assert len(result["skills"]) == 2
        assert result["skills"][0]["name"] == "skill1"
        assert result["skills"][1]["name"] == "skill2"

    def test_process_capabilities_from_dict(self, minimal_config):
        """Test processing capabilities from dictionary."""
        result = ConfigValidator.validate_and_process(minimal_config)

        assert "capabilities" in result
        assert result["capabilities"]["streaming"] is True

    def test_process_agent_trust_from_dict(self, minimal_config):
        """Test processing agent_trust from dictionary."""
        minimal_config["agent_trust"] = {
            "level": "verified",
            "issuer": "test-issuer",
        }

        result = ConfigValidator.validate_and_process(minimal_config)

        assert "agent_trust" in result
        assert result["agent_trust"]["level"] == "verified"

    def test_key_password_none(self, minimal_config):
        """Test that key_password can be None."""
        minimal_config["key_password"] = None

        result = ConfigValidator.validate_and_process(minimal_config)

        assert result["key_password"] is None

    def test_validate_string_fields(self, minimal_config):
        """Test validation of string field types."""
        minimal_config["name"] = 123  # Should be string

        with pytest.raises(ValueError, match="Field 'name' must be a string"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_validate_boolean_fields(self, minimal_config):
        """Test validation of boolean field types."""
        minimal_config["recreate_keys"] = "true"  # Should be boolean

        with pytest.raises(ValueError, match="Field 'recreate_keys' must be a boolean"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_validate_debug_level(self, minimal_config):
        """Test validation of debug_level field."""
        minimal_config["debug_level"] = 3  # Should be 1 or 2

        with pytest.raises(ValueError, match="Field 'debug_level' must be 1 or 2"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_validate_debug_level_string(self, minimal_config):
        """Test validation rejects string debug_level."""
        minimal_config["debug_level"] = "1"  # Should be int

        with pytest.raises(ValueError, match="Field 'debug_level' must be 1 or 2"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_validate_num_history_sessions_negative(self, minimal_config):
        """Test validation rejects negative num_history_sessions."""
        minimal_config["num_history_sessions"] = -1

        with pytest.raises(ValueError, match="Field 'num_history_sessions' must be a non-negative integer"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_validate_kind_invalid(self, minimal_config):
        """Test validation of kind field."""
        minimal_config["kind"] = "invalid"

        with pytest.raises(ValueError, match="Field 'kind' must be one of: agent, team, workflow"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_validate_kind_valid_values(self, minimal_config):
        """Test all valid kind values."""
        for kind in ["agent", "team", "workflow"]:
            minimal_config["kind"] = kind
            result = ConfigValidator.validate_and_process(minimal_config)
            assert result["kind"] == kind

    def test_auth_disabled(self, minimal_config):
        """Test auth configuration when disabled."""
        minimal_config["auth"] = {
            "enabled": False,
        }

        # Should not raise error even without domain/audience
        result = ConfigValidator.validate_and_process(minimal_config)
        assert result["auth"]["enabled"] is False

    def test_auth_enabled_missing_fields(self, minimal_config):
        """Test auth validation when enabled but missing required fields."""
        minimal_config["auth"] = {
            "enabled": True,
            # Missing domain and audience
        }

        with pytest.raises(ValueError, match="Auth is enabled but missing required fields"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_auth_enabled_valid(self, minimal_config):
        """Test valid auth configuration."""
        minimal_config["auth"] = {
            "enabled": True,
            "domain": "tenant.auth0.com",
            "audience": "https://api.example.com",
        }

        result = ConfigValidator.validate_and_process(minimal_config)
        assert result["auth"]["enabled"] is True

    def test_auth_invalid_domain(self, minimal_config):
        """Test auth validation with invalid domain."""
        minimal_config["auth"] = {
            "enabled": True,
            "domain": "invalid",  # No dot
            "audience": "https://api.example.com",
        }

        with pytest.raises(ValueError, match="Invalid auth domain"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_auth_invalid_audience(self, minimal_config):
        """Test auth validation with invalid audience."""
        minimal_config["auth"] = {
            "enabled": True,
            "domain": "tenant.auth0.com",
            "audience": "not-a-url",  # Not a URL
        }

        with pytest.raises(ValueError, match="Invalid auth audience"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_auth_valid_algorithms(self, minimal_config):
        """Test auth with valid algorithms."""
        minimal_config["auth"] = {
            "enabled": True,
            "domain": "tenant.auth0.com",
            "audience": "https://api.example.com",
            "algorithms": ["RS256", "RS384"],
        }

        result = ConfigValidator.validate_and_process(minimal_config)
        assert result["auth"]["algorithms"] == ["RS256", "RS384"]

    def test_auth_invalid_algorithms_type(self, minimal_config):
        """Test auth with invalid algorithms type."""
        minimal_config["auth"] = {
            "enabled": True,
            "domain": "tenant.auth0.com",
            "audience": "https://api.example.com",
            "algorithms": "RS256",  # Should be list
        }

        with pytest.raises(ValueError, match="Field 'auth.algorithms' must be a list"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_auth_invalid_algorithm_value(self, minimal_config):
        """Test auth with invalid algorithm value."""
        minimal_config["auth"] = {
            "enabled": True,
            "domain": "tenant.auth0.com",
            "audience": "https://api.example.com",
            "algorithms": ["RS256", "INVALID"],
        }

        with pytest.raises(ValueError, match="Invalid algorithms in auth config"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_auth_not_dict(self, minimal_config):
        """Test auth validation when not a dictionary."""
        minimal_config["auth"] = "invalid"

        with pytest.raises(ValueError, match="Field 'auth' must be a dictionary"):
            ConfigValidator.validate_and_process(minimal_config)

    def test_create_bindufy_config(self, minimal_config):
        """Test creating bindufy-ready config."""
        result = ConfigValidator.create_bindufy_config(minimal_config)

        assert "deployment" in result
        assert "storage" in result
        assert "scheduler" in result
        assert isinstance(result, dict)

    def test_create_bindufy_config_ensures_nested_dicts(self):
        """Test that create_bindufy_config ensures nested configs exist."""
        config = {
            "author": "test@example.com",
            "capabilities": {"streaming": True},
            # Missing deployment, storage, scheduler - should be added
        }

        # This should fail validation first
        with pytest.raises(ValueError, match="Missing required fields"):
            ConfigValidator.create_bindufy_config(config)


class TestLoadAndValidateConfig:
    """Test suite for load_and_validate_config function."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file."""
        config = {
            "author": "test@example.com",
            "name": "test_agent",
            "capabilities": {
                "streaming": True,
                "push_notifications": False,
            },
            "deployment": {
                "host": "localhost",
                "port": 3773,
            },
            "storage": {
                "type": "memory",
            },
            "scheduler": {
                "type": "memory",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink()

    def test_load_and_validate_config(self, temp_config_file):
        """Test loading and validating config from file."""
        result = load_and_validate_config(temp_config_file)

        assert result["author"] == "test@example.com"
        assert result["name"] == "test_agent"
        assert "capabilities" in result

    def test_load_nonexistent_file(self):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_and_validate_config("/nonexistent/path/config.json")

    def test_load_invalid_json(self):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_and_validate_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_config(self):
        """Test loading file with invalid config."""
        config = {
            "author": "test@example.com",
            # Missing required fields
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Missing required fields"):
                load_and_validate_config(temp_path)
        finally:
            Path(temp_path).unlink()


class TestConfigValidatorDefaults:
    """Test default values in ConfigValidator."""

    def test_default_values(self):
        """Test that default values are correct."""
        assert ConfigValidator.DEFAULTS["name"] == "bindu-agent"
        assert ConfigValidator.DEFAULTS["version"] == "1.0.0"
        assert ConfigValidator.DEFAULTS["recreate_keys"] is True
        assert ConfigValidator.DEFAULTS["debug_mode"] is False
        assert ConfigValidator.DEFAULTS["telemetry"] is True

    def test_required_fields(self):
        """Test that required fields list is correct."""
        expected_required = ["author", "capabilities", "deployment", "storage", "scheduler"]
        assert ConfigValidator.REQUIRED_FIELDS == expected_required
