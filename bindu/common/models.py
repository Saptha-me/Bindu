# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Core data models for the Bindu agent framework.

This module defines the foundational structures that shape an agent's identity,
configuration, and runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from uuid import UUID

from bindu.extensions.did import DIDAgentExtension

from .protocol.types import AgentCapabilities, AgentCard, AgentTrust, Skill


@dataclass(frozen=True)
class DeploymentConfig:
    """Configuration for agent deployment and network exposure.

    Defines how an agent presents itself to the world - its URL, protocol version,
    and the gateways through which it communicates.
    """

    url: str
    expose: bool
    protocol_version: str = "1.0.0"
    proxy_urls: list[str] | None = None
    cors_origins: list[str] | None = None
    openapi_schema: str | None = None


@dataclass(frozen=True)
class StorageConfig:
    """Configuration for agent state persistence.

    Every agent needs memory - a place to store conversations, tasks, and context.
    This defines where that memory lives.
    """

    type: Literal["postgres", "qdrant", "memory"]
    connection_string: str | None = None


@dataclass(frozen=True)
class SchedulerConfig:
    """Configuration for task scheduling and coordination.

    Agents need to orchestrate their work - this defines the mechanism for
    managing asynchronous tasks and workflows.
    """

    type: Literal["redis", "memory"]


@dataclass(frozen=True)
class OLTPConfig:
    """Configuration for observability and tracing.

    This defines where and how observability data is sent.
    """

    endpoint: str
    service_name: str


@dataclass(frozen=True)
class AgentFrameworkSpec:
    """Specification for an agent framework.

    This class defines the properties of an agent framework, including its name,
    the instrumentation package required for it, and the minimum version supported.
    """

    framework: str
    instrumentation_package: str
    min_version: str


@dataclass
class AgentManifest:
    """The living blueprint of an agent.

    This is more than configuration - it's the complete specification of an agent's
    identity, capabilities, and purpose. The manifest bridges the gap between
    static definition and dynamic execution, holding both the agent's metadata
    and its runtime behavior.

    Think of it as the agent's soul - containing everything that makes it unique,
    from its DID and skills to its execution logic.
    """

    # Core Identity
    id: UUID
    name: str
    description: str
    url: str
    version: str
    protocol_version: str

    # Security & Trust
    did_extension: DIDAgentExtension
    agent_trust: AgentTrust

    # Capabilities
    capabilities: AgentCapabilities
    skills: list[Skill]

    # Agent Type & Configuration
    kind: Literal["agent", "team", "workflow"]
    num_history_sessions: int
    enable_system_message: bool = True
    enable_context_based_history: bool = False
    extra_data: dict[str, Any] = field(default_factory=dict)

    # Observability
    debug_mode: bool = False
    debug_level: Literal[1, 2] = 1
    monitoring: bool = False
    telemetry: bool = True
    oltp_endpoint: str | None = None
    oltp_service_name: str | None = None

    # Optional Metadata
    documentation_url: str | None = None

    # Runtime Execution (injected by framework)
    run: Callable[..., Any] | None = field(default=None, init=False)

    def to_agent_card(self) -> AgentCard:
        """Transform the manifest into a protocol-compliant agent card.

        The agent card is the agent's public face - a standardized representation
        that other agents and clients can understand and interact with.
        """
        return AgentCard(
            id=self.id,
            name=self.name,
            description=self.description,
            url=self.url,
            version=self.version,
            protocol_version=self.protocol_version,
            documentation_url=self.documentation_url,
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
            default_input_modes=["text/plain", "application/json"],
            default_output_modes=["text/plain", "application/json"],
        )

    def __repr__(self) -> str:
        """Human-readable representation of the agent."""
        return f"AgentManifest(name='{self.name}', id='{self.id}', version='{self.version}', kind='{self.kind}')"
