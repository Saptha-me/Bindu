from dataclasses import dataclass
from typing import Optional, NamedTuple, List


class KeyPaths(NamedTuple):
    private_key_path: str
    public_key_path: str

@dataclass
class SecurityConfig:
    recreate_keys: bool = True
    did_required: bool = True
    create_csr: bool = True
    allow_anonymous: bool = False

@dataclass
class AgentRegistrationConfig:
    """Organized agent registration information."""
    url: str
    type: str

@dataclass
class CAConfig:
    """Organized CA configuration."""
    url: str 
    type: str

@dataclass
class DeploymentConfig:
    """Organized deployment configuration."""
    expose: bool
    port: int
    endpoint_type: str
    proxy_urls: Optional[List[str]] = None
    cors_origins: Optional[List[str]] = None
    openapi_schema: Optional[str] = None