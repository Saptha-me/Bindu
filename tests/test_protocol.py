"""Tests for the core protocol implementation."""

import json
import tempfile
from pathlib import Path

import pytest

from pebbling.core.protocol import MemoryType, ProtocolMethod, TaskStatus, pebblingProtocol


class TestProtocolMethod:
    """Tests for the ProtocolMethod enum."""

    def test_protocol_method_values(self):
        """Test the enum values for protocol methods."""
        assert ProtocolMethod.CONTEXT == "Context"
        assert ProtocolMethod.ACT == "Act"
        assert ProtocolMethod.LISTEN == "Listen"
        assert ProtocolMethod.VIEW == "View"


class TestTaskStatus:
    """Tests for the TaskStatus enum."""

    def test_task_status_values(self):
        """Test the enum values for task status."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.IN_PROGRESS == "in_progress"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CLARIFICATION_REQUIRED == "clarification_required"


class TestMemoryType:
    """Tests for the MemoryType enum."""

    def test_memory_type_values(self):
        """Test the enum values for memory types."""
        assert MemoryType.SHORT_TERM == "short-term"
        assert MemoryType.LONG_TERM == "long-term"


class TestPebblingProtocol:
    """Tests for the pebblingProtocol class."""

    @pytest.fixture
    def protocol(self):
        """Create a pebblingProtocol instance for testing."""
        return pebblingProtocol()

    @pytest.fixture
    def config_file(self):
        """Create a temporary configuration file for testing."""
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"protocol_version": "1.0", "test_key": "test_value"}, f)
            return f.name

    def test_init_default(self, protocol):
        """Test default initialization."""
        assert protocol.protocol_config == {}
        assert protocol.JSONRPC_VERSION == "2.0"

    def test_init_with_config(self, config_file):
        """Test initialization with a config file."""
        protocol = pebblingProtocol(protocol_config_path=config_file)
        assert "protocol_version" in protocol.protocol_config
        assert protocol.protocol_config["test_key"] == "test_value"

        # Clean up the temporary file
        Path(config_file).unlink()

    def test_create_message(self, protocol):
        """Test message creation."""
        # Using enum
        message = protocol.create_message(
            method=ProtocolMethod.ACT,
            source_agent_id="source_agent",
            destination_agent_id="dest_agent",
            params={"input": "test message"},
        )

        assert message["jsonrpc"] == "2.0"
        assert "id" in message
        assert message["method"] == "Act"
        assert message["source_agent_id"] == "source_agent"
        assert message["destination_agent_id"] == "dest_agent"
        assert "timestamp" in message
        assert message["params"] == {"input": "test message"}

        # Using string
        message = protocol.create_message(
            method="Listen",
            source_agent_id="source_agent",
            destination_agent_id="dest_agent",
            params={"input": "test audio"},
        )

        assert message["method"] == "Listen"

    def test_validate_message(self, protocol):
        """Test message validation."""
        valid_message = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "method": "Act",
            "source_agent_id": "source_agent",
            "destination_agent_id": "dest_agent",
            "timestamp": "2023-01-01T12:00:00",
            "params": {"input": "test message"},
        }

        assert protocol.validate_message(valid_message) is True

        # Test with missing key
        invalid_message = valid_message.copy()
        del invalid_message["source_agent_id"]

        assert protocol.validate_message(invalid_message) is False
