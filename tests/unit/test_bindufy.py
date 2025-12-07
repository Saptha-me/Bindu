"""Tests for bindufy decorator and helper functions.

This module tests the bindufy functionality:
- URL parsing
- Config creation helpers
- bindufy decorator
- Configuration validation integration
"""

from unittest.mock import MagicMock, patch

from bindu.penguin.bindufy import (
    _parse_deployment_url,
    _create_deployment_config,
    _create_storage_config,
    _create_scheduler_config,
    bindufy,
)
from bindu.common.models import (
    DeploymentConfig,
)


class TestParseDeploymentUrl:
    """Test _parse_deployment_url function."""

    def test_parse_url_with_host_and_port(self):
        """Test parsing URL with explicit host and port."""
        config = DeploymentConfig(url="http://example.com:8080", expose=True)

        host, port = _parse_deployment_url(config)

        assert host == "example.com"
        assert port == 8080

    def test_parse_url_with_host_only(self):
        """Test parsing URL with host but no port."""
        config = DeploymentConfig(url="http://example.com", expose=True)

        host, port = _parse_deployment_url(config)

        assert host == "example.com"
        # Should use default port from settings

    def test_parse_url_with_https(self):
        """Test parsing HTTPS URL."""
        config = DeploymentConfig(url="https://secure.example.com:443", expose=True)

        host, port = _parse_deployment_url(config)

        assert host == "secure.example.com"
        assert port == 443

    def test_parse_url_none_config(self):
        """Test parsing with None config."""
        host, port = _parse_deployment_url(None)

        # Should return defaults from settings
        assert host is not None
        assert port is not None

    def test_parse_url_localhost(self):
        """Test parsing localhost URL."""
        config = DeploymentConfig(url="http://localhost:3773", expose=True)

        host, port = _parse_deployment_url(config)

        assert host == "localhost"
        assert port == 3773

    def test_parse_url_ip_address(self):
        """Test parsing IP address URL."""
        config = DeploymentConfig(url="http://127.0.0.1:5000", expose=True)

        host, port = _parse_deployment_url(config)

        assert host == "127.0.0.1"
        assert port == 5000


class TestCreateDeploymentConfig:
    """Test _create_deployment_config function."""

    def test_create_deployment_config_complete(self):
        """Test creating deployment config with all fields."""
        validated_config = {
            "deployment": {
                "url": "http://localhost:3773",
                "expose": True,
                "protocol_version": "1.0.0",
                "proxy_urls": ["http://proxy1.com", "http://proxy2.com"],
                "cors_origins": ["http://localhost:3000"],
                "openapi_schema": {"title": "Test API"},
            }
        }

        config = _create_deployment_config(validated_config)

        assert config is not None
        assert config.url == "http://localhost:3773"
        assert config.expose is True
        assert config.protocol_version == "1.0.0"
        assert config.proxy_urls == ["http://proxy1.com", "http://proxy2.com"]
        assert config.cors_origins == ["http://localhost:3000"]

    def test_create_deployment_config_minimal(self):
        """Test creating deployment config with minimal fields."""
        validated_config = {
            "deployment": {"url": "http://localhost:3773", "expose": True}
        }

        config = _create_deployment_config(validated_config)

        assert config is not None
        assert config.url == "http://localhost:3773"
        assert config.expose is True
        assert config.protocol_version == "1.0.0"  # Default

    def test_create_deployment_config_missing(self):
        """Test creating deployment config when not provided."""
        validated_config = {}

        config = _create_deployment_config(validated_config)

        assert config is None

    def test_create_deployment_config_missing_required_fields(self):
        """Test creating deployment config with missing required fields."""
        validated_config = {
            "deployment": {
                "expose": True
                # Missing 'url'
            }
        }

        config = _create_deployment_config(validated_config)

        assert config is None

    def test_create_deployment_config_partial_fields(self):
        """Test creating deployment config with some optional fields."""
        validated_config = {
            "deployment": {
                "url": "http://localhost:3773",
                "expose": True,
                "cors_origins": ["*"],
            }
        }

        config = _create_deployment_config(validated_config)

        assert config is not None
        assert config.cors_origins == ["*"]


class TestCreateStorageConfig:
    """Test _create_storage_config function."""

    def test_create_storage_config_memory(self):
        """Test creating memory storage config."""
        validated_config = {"storage": {"type": "memory"}}

        config = _create_storage_config(validated_config)

        assert config is not None
        assert config.type == "memory"

    def test_create_storage_config_postgres(self):
        """Test creating PostgreSQL storage config."""
        validated_config = {
            "storage": {
                "type": "postgres",
                "database_url": "postgresql://localhost/testdb",
            }
        }

        config = _create_storage_config(validated_config)

        assert config is not None
        assert config.type == "postgres"
        assert config.database_url == "postgresql://localhost/testdb"

    def test_create_storage_config_missing(self):
        """Test creating storage config when not provided."""
        validated_config = {}

        config = _create_storage_config(validated_config)

        assert config is None

    def test_create_storage_config_missing_type(self):
        """Test creating storage config with missing type."""
        validated_config = {
            "storage": {"database_url": "postgresql://localhost/testdb"}
        }

        config = _create_storage_config(validated_config)

        assert config is None

    def test_create_storage_config_empty_dict(self):
        """Test creating storage config with empty dict."""
        validated_config = {"storage": {}}

        config = _create_storage_config(validated_config)

        assert config is None


class TestCreateSchedulerConfig:
    """Test _create_scheduler_config function."""

    def test_create_scheduler_config_memory(self):
        """Test creating memory scheduler config."""
        validated_config = {"scheduler": {"type": "memory"}}

        config = _create_scheduler_config(validated_config)

        assert config is not None
        assert config.type == "memory"

    def test_create_scheduler_config_missing(self):
        """Test creating scheduler config when not provided."""
        validated_config = {}

        config = _create_scheduler_config(validated_config)

        assert config is None

    def test_create_scheduler_config_missing_type(self):
        """Test creating scheduler config with missing type."""
        validated_config = {"scheduler": {}}

        config = _create_scheduler_config(validated_config)

        assert config is None


class TestBindufy:
    """Test bindufy decorator function."""

    def test_bindufy_minimal_config(self):
        """Test bindufy with minimal configuration."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "id": "test-id",
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
            }

            with patch("bindu.penguin.bindufy.validate_agent_function"):
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch("bindu.penguin.bindufy.uvicorn.run"):
                            mock_manifest = MagicMock()
                            mock_create.return_value = mock_manifest

                            manifest = bindufy(config, test_handler)

                            assert manifest == mock_manifest
                            mock_validator.validate_and_process.assert_called_once_with(
                                config
                            )

    def test_bindufy_with_auth_enabled(self):
        """Test bindufy with authentication enabled."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
            "auth": {
                "enabled": True,
                "domain": "test.auth0.com",
                "audience": "test-api",
                "algorithms": ["RS256"],
            },
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "id": "test-id",
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
            }

            with patch("bindu.penguin.bindufy.validate_agent_function"):
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch(
                            "bindu.penguin.bindufy.app_settings"
                        ) as mock_settings:
                            with patch("bindu.penguin.bindufy.uvicorn.run"):
                                mock_manifest = MagicMock()
                                mock_create.return_value = mock_manifest

                                _manifest = bindufy(config, test_handler)

                                # Auth settings should be updated
                                assert mock_settings.auth.enabled is True
                                assert mock_settings.auth.domain == "test.auth0.com"

    def test_bindufy_with_auth_disabled(self):
        """Test bindufy with authentication disabled."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
            "auth": {"enabled": False},
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "id": "test-id",
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
            }

            with patch("bindu.penguin.bindufy.validate_agent_function"):
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch(
                            "bindu.penguin.bindufy.app_settings"
                        ) as mock_settings:
                            with patch("bindu.penguin.bindufy.uvicorn.run"):
                                mock_manifest = MagicMock()
                                mock_create.return_value = mock_manifest

                                _manifest = bindufy(config, test_handler)

                                # Auth should be disabled
                                assert mock_settings.auth.enabled is False

    def test_bindufy_with_deployment_config(self):
        """Test bindufy with deployment configuration."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
            "deployment": {"url": "http://localhost:3773", "expose": True},
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "id": "test-id",
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
            }

            with patch("bindu.penguin.bindufy.validate_agent_function"):
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch("bindu.penguin.bindufy.uvicorn.run"):
                            mock_manifest = MagicMock()
                            mock_create.return_value = mock_manifest

                            _manifest = bindufy(config, test_handler)

                            assert _manifest == mock_manifest

    def test_bindufy_with_storage_and_scheduler(self):
        """Test bindufy with storage and scheduler configs."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
            "storage": {"type": "memory"},
            "scheduler": {"type": "memory"},
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "id": "test-id",
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
            }

            with patch("bindu.penguin.bindufy.validate_agent_function"):
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch("bindu.penguin.bindufy.uvicorn.run"):
                            mock_manifest = MagicMock()
                            mock_create.return_value = mock_manifest

                            _manifest = bindufy(config, test_handler)

                            assert _manifest == mock_manifest

    def test_bindufy_auto_generates_agent_id(self):
        """Test that bindufy auto-generates agent_id if not provided."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
            # No 'id' provided
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
                # No 'id' in validated config either
            }

            with patch("bindu.penguin.bindufy.validate_agent_function"):
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch("bindu.penguin.bindufy.uuid4") as mock_uuid:
                            with patch("bindu.penguin.bindufy.uvicorn.run"):
                                mock_uuid.return_value.hex = "auto-generated-id"
                                mock_manifest = MagicMock()
                                mock_create.return_value = mock_manifest

                                _manifest = bindufy(config, test_handler)

                                # Should have called uuid4 to generate ID
                                mock_uuid.assert_called()

    def test_bindufy_validates_handler_function(self):
        """Test that bindufy validates the handler function."""

        def test_handler(messages):
            return "response"

        config = {
            "author": "test@example.com",
            "name": "test-agent",
            "description": "Test agent",
            "recreate_keys": False,
        }

        with patch("bindu.penguin.config_validator.ConfigValidator") as mock_validator:
            mock_validator.validate_and_process.return_value = {
                **config,
                "id": "test-id",
                "version": "1.0.0",
                "kind": "agent",
                "agent_trust": {},
                "debug_mode": False,
                "debug_level": 1,
                "monitoring": False,
                "telemetry": False,
                "num_history_sessions": 10,
                "documentation_url": None,
                "extra_metadata": {},
            }

            with patch(
                "bindu.penguin.bindufy.validate_agent_function"
            ) as mock_validate:
                with patch("bindu.penguin.bindufy.DIDAgentExtension") as mock_did:
                    mock_did_instance = MagicMock()
                    mock_did.return_value = mock_did_instance

                    with patch("bindu.penguin.bindufy.create_manifest") as mock_create:
                        with patch("bindu.penguin.bindufy.uvicorn.run"):
                            mock_manifest = MagicMock()
                            mock_create.return_value = mock_manifest

                            _manifest = bindufy(config, test_handler)

                            # Should have validated the handler
                            mock_validate.assert_called_once_with(test_handler)


class TestBindufyEdgeCases:
    """Test edge cases in bindufy."""

    def test_parse_url_with_path(self):
        """Test URL parsing with path component."""
        config = DeploymentConfig(url="http://example.com:8080/api/v1", expose=True)

        host, port = _parse_deployment_url(config)

        assert host == "example.com"
        assert port == 8080

    def test_create_configs_with_extra_fields(self):
        """Test config creation ignores extra fields."""
        validated_config = {
            "deployment": {
                "url": "http://localhost:3773",
                "expose": True,
                "extra_field": "ignored",
            }
        }

        config = _create_deployment_config(validated_config)

        assert config is not None
        assert config.url == "http://localhost:3773"
