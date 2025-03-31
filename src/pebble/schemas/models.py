from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from pydantic import BaseModel

# Add security configuration models
class SecurityConfig(BaseModel):
    """Security configuration for agent communication."""
    
    use_mtls: bool = False
    """Whether to use mTLS for secure communication."""
    
    certs_dir: Optional[str] = None
    """Directory to store certificates and keys."""
    
    ca_bundle_path: Optional[str] = None
    """Path to CA bundle for verifying server certificates."""
    
    require_client_cert: bool = True
    """Whether to require client certificates for incoming connections."""
    
    cert_path: Optional[str] = None
    """Path to server certificate (set by the system)."""
    
    key_path: Optional[str] = None
    """Path to server private key (set by the system)."""

class DeploymentMode(str, Enum):
    """Deployment modes for pebblification."""
    LOCAL = "local"             # Run server locally
    REGISTER = "register"       # Deploy and register with router
    DOCKER = "docker"           # Generate Docker artifacts
    
class RouterRegistration(BaseModel):
    """Configuration for router registration."""
    router_url: str
    api_key: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    organization_id: Optional[str] = None

class DockerConfig(BaseModel):
    """Configuration for Docker deployment."""
    base_image: str = "python:3.10-slim"
    output_dir: str = "./docker"
    include_requirements: bool = True
    expose_port: int = 8000
    environment_vars: Optional[Dict[str, str]] = None
    
class DeploymentConfig(BaseModel):
    """Configuration for deploying an agent."""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["*"]
    enable_docs: bool = True
    require_auth: bool = True
    mode: DeploymentMode = DeploymentMode.LOCAL
    log_level: str = "INFO"
    logging_config: Optional[Dict] = None
    router_config: Optional[RouterRegistration] = None
    docker_config: Optional[DockerConfig] = None