"""Pebbling protocol core implementation and enums."""

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union


class ProtocolMethod(str, Enum):
    """Supported protocol methods."""

    CONTEXT = "Context"
    ACT = "Act"
    LISTEN = "Listen"
    VIEW = "View"


class TaskStatus(str, Enum):
    """Task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CLARIFICATION_REQUIRED = "clarification_required"


class MemoryType(str, Enum):
    """Memory types."""

    SHORT_TERM = "short-term"
    LONG_TERM = "long-term"


class pebblingProtocol:
    """pebbling protocol implementation."""

    JSONRPC_VERSION = "2.0"

    def __init__(self, protocol_config_path: Optional[str] = None):
        """Initialize with optional config file."""
        self.protocol_config: Dict[str, Any] = {}
        if protocol_config_path:
            self._load_config(protocol_config_path)

    def _load_config(self, config_path: str) -> None:
        """Load configuration from JSON file."""
        path = Path(config_path)
        if path.exists():
            with open(path, "r") as f:
                self.protocol_config = json.load(f)

    def create_message(
        self,
        method: Union[str, ProtocolMethod],
        source_agent_id: str,
        destination_agent_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a protocol message."""
        if isinstance(method, ProtocolMethod):
            method = method.value

        return {
            "jsonrpc": self.JSONRPC_VERSION,
            "id": str(uuid.uuid4()),
            "method": method,
            "source_agent_id": source_agent_id,
            "destination_agent_id": destination_agent_id,
            "timestamp": datetime.now().isoformat(),
            "params": params,
        }

    def validate_message(self, message: Dict[str, Any]) -> bool:
        """Validate a protocol message."""
        required_keys = [
            "jsonrpc",
            "id",
            "method",
            "source_agent_id",
            "timestamp",
            "params",
        ]

        # Check required keys and version
        if not all(key in message for key in required_keys):
            return False
        if message.get("jsonrpc") != self.JSONRPC_VERSION:
            return False

        # Method and params validation
        method = message.get("method", "")
        if self.protocol_config and "methods" in self.protocol_config:
            if method not in self.protocol_config["methods"]:
                return False

            method_config = self.protocol_config["methods"][method]
            required_params = method_config.get("required_params", [])
            if required_params and not all(param in message.get("params", {}) for param in required_params):
                return False

        return True

    def create_response(self, result: Any, request_id: str) -> Dict[str, Any]:
        """Create a protocol response."""
        return {"jsonrpc": self.JSONRPC_VERSION, "id": request_id, "result": result}

    def create_error(self, code: int, message: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a protocol error response."""
        return {
            "jsonrpc": self.JSONRPC_VERSION,
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def make(
        self,
        method: Union[str, ProtocolMethod],
        source_agent_id: str,
        destination_agent_id: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a protocol message dictionary."""
        return self.create_message(
            method=method,
            source_agent_id=source_agent_id,
            destination_agent_id=destination_agent_id,
            params=params,
        )
