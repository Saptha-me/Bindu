import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

@dataclass
class SecurityCredentials:
    """Organized security credentials for different server types."""
    # Core cryptographic keys
    keys_dir: str
    private_key_path: Optional[str] = None
    public_key_path: Optional[str] = None
    
    # DID-based identity (for agent-to-agent communication)
    did_manager: Optional[DIDManager] = None
    did_document: Optional[Dict[str, Any]] = None
    
    # Certificate-based security
    cert_path: Optional[str] = None
    csr_path: Optional[str] = None
    
    # JWT tokens (for MCP servers and API access)
    jwt_token: Optional[str] = None
    jwt_secret: Optional[str] = None
    access_token: Optional[str] = None
    
    # Server type configuration
    server_type: str = "agent"  # "agent" or "mcp"
