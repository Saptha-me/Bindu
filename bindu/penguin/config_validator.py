"""
Configuration validation and processing for Pebbling agents.

This module provides utilities to validate and process agent configurations,
ensuring they meet the required schema and have proper defaults.
"""

import os
from typing import Dict, Any, List, Optional
from pebbling.common.models import DeploymentConfig, SchedulerConfig, StorageConfig
from pebbling.common.protocol.types import AgentCapabilities, Skill, AgentTrust


class ConfigValidator:
    """Validates and processes agent configuration."""
    
    # Default values for optional fields
    DEFAULTS = {
        "name": "pebble-agent",
        "description": "A Pebble agent",
        "version": "1.0.0",
        "recreate_keys": True,
        "skills": [],
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
    }
    
    # Required fields that must be present
    REQUIRED_FIELDS = [
        "author",
        "capabilities",
        "deployment",
        "storage", 
        "scheduler"
    ]
    
    @classmethod
    def validate_and_process(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and process agent configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Processed configuration with defaults applied
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Check required fields
        missing_fields = [field for field in cls.REQUIRED_FIELDS if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Start with defaults
        processed_config = cls.DEFAULTS.copy()
        
        # Update with provided config
        processed_config.update(config)
        
        # Process complex fields
        processed_config = cls._process_complex_fields(processed_config)
        
        # Validate field types
        cls._validate_field_types(processed_config)
        
        return processed_config
    
    @classmethod
    def _process_complex_fields(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process fields that need special handling."""
        # Process skills if provided as dict list
        if isinstance(config.get("skills"), list) and config["skills"]:
            if isinstance(config["skills"][0], dict):
                config["skills"] = [Skill(**skill) for skill in config["skills"]]
        
        # Process capabilities
        if isinstance(config.get("capabilities"), dict):
            config["capabilities"] = AgentCapabilities(**config["capabilities"])
        
        # Process agent_trust if provided
        if isinstance(config.get("agent_trust"), dict):
            config["agent_trust"] = AgentTrust(**config["agent_trust"])
        
        # Process key password - support environment variable and prompt
        if config.get("key_password"):
            from pebbling.utils.security import get_key_password
            config["key_password"] = get_key_password(config)
        
        return config
    
    @classmethod
    def _validate_field_types(cls, config: Dict[str, Any]) -> None:
        """Validate that fields have correct types."""
        # Validate string fields
        string_fields = ["author", "name", "description", "version", "kind", "key_password"]
        for field in string_fields:
            if field in config and config[field] is not None and not isinstance(config[field], str):
                raise ValueError(f"Field '{field}' must be a string")
        
        # Validate boolean fields
        bool_fields = ["recreate_keys", "debug_mode", "monitoring", "telemetry"]
        for field in bool_fields:
            if field in config and not isinstance(config[field], bool):
                raise ValueError(f"Field '{field}' must be a boolean")
        
        # Validate numeric fields
        if "debug_level" in config:
            if not isinstance(config["debug_level"], int) or config["debug_level"] not in [1, 2]:
                raise ValueError("Field 'debug_level' must be 1 or 2")
        
        if "num_history_sessions" in config:
            if not isinstance(config["num_history_sessions"], int) or config["num_history_sessions"] < 0:
                raise ValueError("Field 'num_history_sessions' must be a non-negative integer")
        
        # Validate kind
        if config.get("kind") not in ["agent", "team", "workflow"]:
            raise ValueError("Field 'kind' must be one of: agent, team, workflow")
    
    @classmethod
    def create_pebblify_config(cls, raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a configuration dict ready for pebblify function.
        
        This is a convenience method that validates, processes, and ensures
        the config is in the right format for the pebblify function.
        
        Args:
            raw_config: Raw configuration (e.g., from JSON file)
            
        Returns:
            Configuration dictionary ready for pebblify
        """
        # Validate and process
        config = cls.validate_and_process(raw_config)
        
        # Ensure nested configs are dictionaries (not model instances)
        # for compatibility with pebblify
        if "deployment" not in config:
            config["deployment"] = {}
        if "storage" not in config:
            config["storage"] = {}
        if "scheduler" not in config:
            config["scheduler"] = {}
        
        return config


def load_and_validate_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from file and validate it.
    
    Args:
        config_path: Path to configuration file (JSON)
        
    Returns:
        Validated and processed configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    import json
    import os
    
    # Handle relative paths
    if not os.path.isabs(config_path):
        caller_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(caller_dir, config_path)
    
    # Load config
    with open(config_path, "r") as f:
        raw_config = json.load(f)
    
    # Validate and return
    return ConfigValidator.create_pebblify_config(raw_config)
