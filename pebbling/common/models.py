from dataclasses import dataclass
from typing import Optional, NamedTuple, List, Any, Dict, Callable
from uuid import UUID
import inspect
import abc

from pebbling.common.protocol.types import (
    AgentCard, 
    AgentCapabilities, 
    AgentSkill, 
    AgentIdentity,
    agent_card_ta
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
    expose: bool
    port: int
    endpoint_type: str
    proxy_urls: Optional[List[str]] = None
    cors_origins: Optional[List[str]] = None
    openapi_schema: Optional[str] = None


class AgentManifest(abc.ABC):
    """Agent manifest class."""
    
    @property
    def name(self) -> AgentName:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return ""

    @property
    def input_content_types(self) -> list[str]:
        return []

    @property
    def output_content_types(self) -> list[str]:
        return []

    @property
    def metadata(self) -> Metadata:
        return Metadata()

    @abc.abstractmethod
    def run(
        self, input: list[Message], context: Context
    ) -> (
        AsyncGenerator[RunYield, RunYieldResume] | Generator[RunYield, RunYieldResume] | Coroutine[RunYield] | RunYield
    ):
        pass