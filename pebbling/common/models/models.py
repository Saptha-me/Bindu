from dataclasses import dataclass
from typing import Optional, NamedTuple, List


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
    
    # Server type configuration
    server_type: str = "agent"  # "agent" or "mcp"

@dataclass
class AgentRegistration:
    """Organized agent registration information."""
    #Agent ID
    agent_id: Optional[str]
    #Registry URL
    registry_url: str
    #Registry Type
    registry_type: str
    #Registry PAT Token
    registry_pat_token: Optional[str] = None

@dataclass
class CAConfig:
    """Organized CA configuration."""
    #CA URL
    ca_url: str 
    #CA Type
    ca_type: str

@dataclass
class DeploymentConfig:
    """Organized deployment configuration."""
    #Expose
    expose: bool
    #Port
    port: int
    #Endpoint Type
    endpoint_type: str
    #Proxy URLs
    proxy_urls: Optional[List[str]] = None
    #CORS Origins
    cors_origins: Optional[List[str]] = None
    #OpenAPI Schema
    openapi_schema: Optional[str] = None

    



