"""Pebbling protocol core implementation and enums."""

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Core protocol
class CoreProtocolMethod(str, Enum):
    """Supported protocol methods."""

    CONTEXT = "context"
    ACT = "act"
    LISTEN = "listen"
    VIEW = "view"

# Security protocol
class SecurityProtocolMethod(str, Enum):
    """Security protocol methods."""

    EXCHANGE_DID = "exchange_did"
    VERIFY_IDENTITY = "verify_identity"
    
    # mTLS security methods
    EXCHANGE_CERTIFICATES = "exchange_certificates"
    VERIFY_CONNECTION = "verify_connection"

# Discovery protocol
class DiscoveryProtocolMethod(str, Enum):
    """Discovery protocol methods."""

    DISCOVER_AGENTS = "discover_agents"
    REGISTER_AGENT = "register_agent"

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
