import pytest

from bindu.penguin.config_validator import ConfigValidator, ConfigError


def test_valid_agent_trust_config():
    raw = {
        "author": "a@b.com",
        "name": "x",
        "deployment": {"url": "http://localhost:3773"},
        "agent_trust": {
            "required_verification_level": 1,
            "allowed_origins": ["https://example.com"],
            "max_agent_hierarchy_depth": 3,
        },
    }

    processed = ConfigValidator.create_bindufy_config(raw)
    assert processed["agent_trust"]["required_verification_level"] == 1
    assert processed["agent_trust"]["allowed_origins"] == ["https://example.com"]


def test_invalid_agent_trust_config_missing_field():
    raw = {
        "author": "a@b.com",
        "name": "x",
        "deployment": {"url": "http://localhost:3773"},
        "agent_trust": {
            # missing required_verification_level
            "allowed_origins": ["https://example.com"],
        },
    }

    with pytest.raises(ValueError):
        ConfigValidator.create_bindufy_config(raw)


def test_invalid_agent_trust_config_bad_types():
    raw = {
        "author": "a@b.com",
        "name": "x",
        "deployment": {"url": "http://localhost:3773"},
        "agent_trust": {
            "required_verification_level": -1,
            "allowed_origins": "not-a-list",
        },
    }

    with pytest.raises(ValueError):
        ConfigValidator.create_bindufy_config(raw)
