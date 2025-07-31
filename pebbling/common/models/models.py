from dataclasses import dataclass
from typing import Optional, NamedTuple


class KeyPaths(NamedTuple):
    private_key_path: str
    public_key_path: str

@dataclass
class SecurityCredentials:
    """Organized security credentials for different server types."""
    #Agent ID
    agent_id: Optional[str]

    # Core cryptographic keys
    pki_dir: str
    key_paths: Optional[KeyPaths] = None
    
    # Certificate-based security
    cert_path: Optional[str] = None
    csr_path: Optional[str] = None

    # DID Document
    did_document: Optional[str] = None
    
    # JWT tokens (for MCP servers and API access)
    jwt_token: Optional[str] = None
    jwt_secret: Optional[str] = None
    access_token: Optional[str] = None
    
    # Server type configuration
    server_type: str = "agent"  # "agent" or "mcp"



