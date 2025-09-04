from dataclasses import dataclass
from typing import Optional, NamedTuple, List, Any, Dict, Callable, Literal
from uuid import UUID
import inspect
import abc
from typing import AsyncGenerator, Generator, Coroutine

from .protocol.types import (
    AgentCard, 
    AgentCapabilities, 
    AgentSkill, 
    AgentIdentity,
    AgentTrust
)


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
    url: str
    protocol_version: str
    expose: bool
    port: int
    endpoint_type: str
    proxy_urls: Optional[List[str]] = None
    cors_origins: Optional[List[str]] = None
    openapi_schema: Optional[str] = None


class AgentManifest:
    """Runtime agent manifest with all AgentCard properties and execution capability."""
    
    def __init__(
        self,
        id: UUID,
        name: str,
        description: str,
        url: str,
        version: str,
        protocol_version: str,
        identity: AgentIdentity,
        trust_config: AgentTrust,
        capabilities: AgentCapabilities,
        skill: AgentSkill,
        kind: Literal['agent', 'team', 'workflow'],
        num_history_sessions: int,
        extra_data: Dict[str, Any],
        debug_mode: bool,
        debug_level: Literal[1, 2],
        monitoring: bool,
        telemetry: bool,
        documentation_url: Optional[str] = None
    ):
        """Initialize AgentManifest with all AgentCard properties."""
        # Core identification
        self.id = id
        self.name = name
        self.description = description
        self.url = url
        self.version = version
        self.protocol_version = protocol_version
        self.documentation_url = documentation_url
        
        # Security and identity
        self.identity = identity
        self.trust_config = trust_config
        
        # Capabilities and skills
        self.capabilities = capabilities
        self.skill = skill
        
        # Type and configuration
        self.kind = kind
        self.num_history_sessions = num_history_sessions
        self.extra_data = extra_data
        
        # Debug and monitoring
        self.debug_mode = debug_mode
        self.debug_level = debug_level
        self.monitoring = monitoring
        self.telemetry = telemetry
        
        # Runtime execution method (set by create_manifest)
        self.run = None
    
    def to_agent_card(self) -> AgentCard:
        """Convert AgentManifest to AgentCard protocol format."""
        return AgentCard(
            id=self.id,
            name=self.name,
            description=self.description,
            url=self.url,
            version=self.version,
            protocol_version=self.protocol_version,
            documentation_url=self.documentation_url,
            identity=self.identity,
            trust_config=self.trust_config,
            capabilities=self.capabilities,
            skill=self.skill,
            kind=self.kind,
            num_history_sessions=self.num_history_sessions,
            extra_data=self.extra_data,
            debug_mode=self.debug_mode,
            debug_level=self.debug_level,
            monitoring=self.monitoring,
            telemetry=self.telemetry
        )
    
    def __repr__(self) -> str:
        return f"AgentManifest(name='{self.name}', id='{self.id}', version='{self.version}')"