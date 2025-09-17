from dataclasses import dataclass
from typing import Any, Dict, List, Literal, NamedTuple, Optional
from uuid import UUID

from .protocol.types import AgentCapabilities, AgentCard, AgentIdentity, AgentSkill, AgentTrust


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
    expose: bool
    protocol_version: str = "1.0.0"
    proxy_urls: Optional[List[str]] = None
    cors_origins: Optional[List[str]] = None
    openapi_schema: Optional[str] = None


@dataclass
class StorageConfig:
    """Organized storage configuration."""

    type: Literal["postgres", "qdrant", "memory"]
    connection_string: str


@dataclass
class SchedulerConfig:
    """Organized scheduler configuration."""

    type: Literal["redis", "memory"]


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
        agent_trust: AgentTrust,
        capabilities: AgentCapabilities,
        skills: List[AgentSkill],
        kind: Literal["agent", "team", "workflow"],
        num_history_sessions: int,
        extra_data: Dict[str, Any],
        debug_mode: bool,
        debug_level: Literal[1, 2],
        monitoring: bool,
        telemetry: bool,
        documentation_url: Optional[str] = None,
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
        self.agent_trust = agent_trust

        # Capabilities and skills
        self.capabilities = capabilities
        self.skills = skills

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
            agent_trust=self.agent_trust,
            capabilities=self.capabilities,
            skills=self.skills,
            kind=self.kind,
            num_history_sessions=self.num_history_sessions,
            extra_data=self.extra_data,
            debug_mode=self.debug_mode,
            debug_level=self.debug_level,
            monitoring=self.monitoring,
            telemetry=self.telemetry,
        )

    def __repr__(self) -> str:
        return f"AgentManifest(name='{self.name}', id='{self.id}', version='{self.version}')"
