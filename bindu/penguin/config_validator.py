"""
Configuration validation and processing for bindu agents.

This module provides utilities to validate and process agent configurations,
ensuring they meet the required schema and have proper defaults.
"""

import os
from typing import Any, Dict
from urllib.parse import urlparse

import pydantic

from bindu import __version__
from bindu.common.protocol.types import AgentCapabilities, AgentTrustConfig, Skill


class ConfigError(ValueError):
    """Raised when bindufy configuration is invalid."""


class ConfigValidator:
    """Validates and processes agent configuration."""

    # Default port for example configurations
    DEFAULT_EXAMPLE_PORT = 3773

    # Example configuration for error messages
    EXAMPLE_CONFIG = """{
        "author": "you@example.com",
        "name": "my-agent",
        "deployment": {"url": "http://localhost:3773"}
    }"""

    DEFAULTS = {
        "name": "bindu-agent",
        "description": "A Bindu agent",
        "version": __version__,
        "recreate_keys": False,
        "skills": [],
        # Private skills surface — visible only to callers whose DID is on
        # `allowed_dids`, served from /agent/private.json behind Hydra auth.
        # Empty by default so existing agents keep their current behavior.
        "private_skills": [],
        "allowed_dids": [],
        "capabilities": {},
        "storage": {"type": "memory"},
        "scheduler": {"type": "memory"},
        "kind": "agent",
        "debug_mode": False,
        "debug_level": 1,
        "monitoring": False,
        "telemetry": True,
        "num_history_sessions": 10,
        "documentation_url": None,
        "extra_metadata": {},
        "agent_trust": None,
        "key_password": None,
        "auth": None,
        "oltp_endpoint": None,
        "oltp_service_name": None,
        "oltp_verbose_logging": False,
        "oltp_service_version": "1.0.0",
        "oltp_deployment_environment": "production",
        "oltp_batch_max_queue_size": 2048,
        "oltp_batch_schedule_delay_millis": 5000,
        "oltp_batch_max_export_batch_size": 512,
        "oltp_batch_export_timeout_millis": 30000,
    }

    # Required fields (supports nested keys via dot notation)
    REQUIRED_FIELDS = [
        "author",
        "name",
        "deployment.url",
    ]

    @classmethod
    def validate_and_process(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and process agent configuration."""
        if not isinstance(config, dict):
            raise ConfigError(
                "ConfigError: configuration must be a dictionary passed to bindufy(config=...)."
            )

        # Validate required fields first (fail-fast)
        cls._validate_required_fields(config)

        # Start with defaults
        processed_config = cls.DEFAULTS.copy()

        # Update with provided config
        processed_config.update(config)

        # Process complex fields
        processed_config = cls._process_complex_fields(processed_config)

        # Validate field types
        cls._validate_field_types(processed_config)

        return processed_config

    # ------------------------------------------------------------------
    # Required field validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_required_fields(cls, config: Dict[str, Any]) -> None:
        """Validate required fields including nested fields."""
        missing: list[str] = []

        for field in cls.REQUIRED_FIELDS:
            keys = field.split(".")
            value = config

            for key in keys:
                if not isinstance(value, dict) or key not in value:
                    missing.append(field)
                    break
                value = value[key]

            if field not in missing and (
                value is None or (isinstance(value, str) and not value.strip())
            ):
                missing.append(field)

        if missing:
            if len(missing) == 1:
                field_name = missing[0]
                raise ConfigError(
                    f"ConfigError: '{field_name}' is a required field in the agent configuration."
                )

            formatted_fields = "\n".join(f"- {f}" for f in missing)
            raise ConfigError(
                f"ConfigError: missing required fields in the agent configuration:\n"
                f"{formatted_fields}\n\n"
                f"Example:\n{cls.EXAMPLE_CONFIG}"
            )

        cls._validate_deployment_url(config)

    @classmethod
    def _validate_deployment_url(cls, config: Dict[str, Any]) -> None:
        """Validate deployment URL format when provided."""
        deployment_config = config.get("deployment")
        if deployment_config is None:
            return

        if not isinstance(deployment_config, dict):
            raise ConfigError(
                "ConfigError: 'deployment' must be a dictionary in the agent configuration."
            )

        deployment_url = deployment_config.get("url")
        if not isinstance(deployment_url, str) or not deployment_url.strip():
            raise ConfigError(
                "ConfigError: 'deployment.url' is a required field in the agent configuration."
            )

        parsed = urlparse(deployment_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError(
                f"ConfigError: 'deployment.url' must be a valid http(s) URL, got '{deployment_url}'."
            )

    # ------------------------------------------------------------------
    # Complex field processing
    # ------------------------------------------------------------------

    @classmethod
    def _process_complex_fields(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(config.get("skills"), list) and config["skills"]:
            if isinstance(config["skills"][0], dict):
                config["skills"] = [Skill(**skill) for skill in config["skills"]]

        if isinstance(config.get("capabilities"), dict):
            config["capabilities"] = AgentCapabilities(**config["capabilities"])

        if config.get("auth"):
            cls._validate_auth_config(config["auth"])

        if config.get("agent_trust") is not None:
            cls._validate_agent_trust_config(config["agent_trust"])

        if config.get("telemetry"):
            cls._process_oltp_config(config)

        return config

    # ------------------------------------------------------------------
    # Field type validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_field_type(
        cls,
        config: Dict[str, Any],
        field: str,
        expected_type: type,
        allow_none: bool = False,
    ) -> None:
        """Validate a single field's type.

        Args:
            config: Configuration dictionary
            field: Field name to validate
            expected_type: Expected Python type
            allow_none: Whether None values are allowed

        Raises:
            ValueError: If field type is invalid
        """
        if field not in config:
            return

        value = config[field]
        if allow_none and value is None:
            return

        if not isinstance(value, expected_type):
            type_name = expected_type.__name__
            raise ValueError(f"Field '{field}' must be a {type_name}")

    @classmethod
    def _validate_field_types(cls, config: Dict[str, Any]) -> None:
        # Validate string fields
        string_fields = [
            "author",
            "name",
            "description",
            "version",
            "kind",
            "key_password",
        ]
        for field in string_fields:
            cls._validate_field_type(config, field, str, allow_none=True)

        # Validate boolean fields
        bool_fields = ["recreate_keys", "debug_mode", "monitoring", "telemetry"]
        for field in bool_fields:
            cls._validate_field_type(config, field, bool)

        if "debug_level" in config:
            if not isinstance(config["debug_level"], int) or config[
                "debug_level"
            ] not in [1, 2]:
                raise ValueError("Field 'debug_level' must be 1 or 2")

        if "num_history_sessions" in config:
            if (
                not isinstance(config["num_history_sessions"], int)
                or config["num_history_sessions"] < 0
            ):
                raise ValueError(
                    "Field 'num_history_sessions' must be a non-negative integer"
                )

        if config.get("kind") not in ["agent", "team", "workflow"]:
            raise ValueError("Field 'kind' must be one of: agent, team, workflow")

        # execution_cost can be either a single dict or a list of dicts
        if "execution_cost" in config and config["execution_cost"] is not None:
            execution_cost = config["execution_cost"]

            # Normalize basic type – we accept a dict or list of dicts
            if isinstance(execution_cost, dict):
                # Single option – valid
                pass
            elif isinstance(execution_cost, list):
                if not execution_cost:
                    raise ValueError("Field 'execution_cost' list cannot be empty")

                for item in execution_cost:
                    if not isinstance(item, dict):
                        raise ValueError(
                            "Field 'execution_cost' must be a dict or a list of dicts"
                        )
            else:
                # Any other type is invalid
                raise ValueError(
                    "Field 'execution_cost' must be a dict or a list of dicts"
                )

    # ------------------------------------------------------------------
    # Auth validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_auth_config(cls, auth_config: Dict[str, Any]) -> None:
        if not isinstance(auth_config, dict):
            raise ValueError("Field 'auth' must be a dictionary")

        if not auth_config.get("enabled", False):
            return

        provider = auth_config.get("provider", "hydra").lower()

        if provider == "hydra":
            cls._validate_hydra_config(auth_config)
        else:
            raise ValueError(
                f"Unknown auth provider: '{provider}'. Supported providers: hydra"
            )

    @classmethod
    def _validate_agent_trust_config(cls, trust_config: Dict[str, Any]) -> None:
        """Validate the agent_trust configuration dict against AgentTrustConfig schema.

        Raises:
            ValueError: If trust_config is not a dict or fails Pydantic validation.
        """
        if not isinstance(trust_config, dict):
            raise ValueError("Field 'agent_trust' must be a dictionary")
        try:
            AgentTrustConfig(**trust_config)
        except (pydantic.ValidationError, TypeError) as exc:
            raise ValueError(f"Invalid 'agent_trust' configuration: {exc}") from exc

    @classmethod
    def _validate_hydra_config(cls, auth_config: Dict[str, Any]) -> None:
        if "admin_url" in auth_config:
            admin_url = auth_config["admin_url"]
            if not admin_url.startswith(("http://", "https://")):
                raise ValueError(
                    f"Invalid Hydra admin_url: '{admin_url}'. "
                    f"Expected format: 'https://hydra-admin.getbindu.com'"
                )

    # ------------------------------------------------------------------
    # Telemetry processing
    # ------------------------------------------------------------------

    @classmethod
    def _process_oltp_config(cls, config: Dict[str, Any]) -> None:
        oltp_endpoint = config.get("oltp_endpoint")
        if oltp_endpoint and isinstance(oltp_endpoint, str):
            if oltp_endpoint.startswith("env:"):
                config["oltp_endpoint"] = os.getenv(oltp_endpoint[4:])

    # ------------------------------------------------------------------
    # Public helper
    # ------------------------------------------------------------------

    @classmethod
    def create_bindufy_config(cls, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create bindufy configuration from raw config."""
        return cls.validate_and_process(raw_config)


def load_and_validate_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration from file path."""
    import json

    if not os.path.isabs(config_path):
        caller_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(caller_dir, config_path)

    with open(config_path, "r") as f:
        raw_config = json.load(f)

    return ConfigValidator.create_bindufy_config(raw_config)
