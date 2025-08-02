from dataclasses import dataclass
from typing import Optional, NamedTuple, List
from pebbling.protocol.types import AgentSecurity, AgentIdentity


class KeyPaths(NamedTuple):
    private_key_path: str
    public_key_path: str

@dataclass
class SecurityConfig:
    recreate_keys: bool = False
    did_required: bool = False
    require_challenge_response: bool = False
    create_csr: bool = False
    verify_requests: bool = False
    allow_anonymous: bool = False

@dataclass
class SecuritySetupResult:
    """Complete security setup result with all components."""
    security_config: AgentSecurity
    identity: AgentIdentity

@dataclass
class AgentRegistrationConfig:
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

    



