# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - Raahul

import abc
import inspect
import uuid
from collections.abc import AsyncGenerator, Coroutine, Generator
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pebbling.protocol.types import (
    AgentManifest as ProtocolAgentManifest,
    AgentCapabilities, 
    AgentSkill,
    AgentIdentity
)


class AgentManifest(abc.ABC):
    """Base agent manifest with abstract methods similar to ACP style."""
    
    @property
    def name(self) -> str:
        """Name of the agent."""
        return self.__class__.__name__

    @property
    def description(self) -> str:
        """Description of the agent."""
        return ""

    @property
    def input_content_types(self) -> list[str]:
        """Content types this agent can accept as input."""
        return []

    @property
    def output_content_types(self) -> list[str]:
        """Content types this agent can produce as output."""
        return []

    @property
    def metadata(self) -> dict[str, Any]:
        """Metadata about the agent."""
        return {}
        
    @property
    def capabilities(self) -> AgentCapabilities:
        """Agent capabilities like streaming, state history, etc."""
        return AgentCapabilities()
        
    @property
    def skills(self) -> list[AgentSkill]:
        """List of skills the agent supports."""
        return []
        
    @property
    def agent_id(self) -> Union[str, uuid.UUID]:
        """Unique identifier for the agent."""
        return str(uuid.uuid4())
    
    @property
    def user_id(self) -> Union[str, uuid.UUID]:
        """ID of the user associated with this agent."""
        return "default-user"
        
    @property
    def did(self) -> Optional[str]:
        """Decentralized Identifier for the agent."""
        return None
        
    @property
    def did_document(self) -> Optional[Dict[str, Any]]:
        """DID document associated with the agent."""
        return None

    @property
    def agent_identity(self) -> AgentIdentity:
        """Agent identity associated with this agent."""
        return AgentIdentity()
    
    def to_protocol_manifest(self) -> ProtocolAgentManifest:
        """Convert this agent to a protocol-compatible manifest."""
        return ProtocolAgentManifest(
            agent_id=self.agent_id,
            name=self.name,
            user_id=self.user_id,
            capabilities=self.capabilities,
            skills=self.skills,
            agent=self,
            did=self.did,
            did_document=self.did_document
        )


Agent = AgentManifest


def agent(
    name: str | None = None,
    description: str | None = None,
    *,
    metadata: dict[str, Any] | None = None,
    input_content_types: list[str] | None = None,
    output_content_types: list[str] | None = None,
    capabilities: Dict[str, Any] | None = None,
    skills: List[Dict[str, Any]] | None = None,
) -> Callable[[Callable], AgentManifest]:
    """Decorator to create an agent following ACP style."""

    def decorator(fn: Callable) -> AgentManifest:
        signature = inspect.signature(fn)
        parameters = list(signature.parameters.values())

        if len(parameters) == 0:
            raise TypeError("The agent function must have at least 'input' argument")
        if len(parameters) > 2:
            raise TypeError("The agent function must have only 'input' and 'context' arguments")
        if len(parameters) == 2 and parameters[1].name != "context":
            raise TypeError("The second argument of the agent function must be 'context'")

        has_context_param = len(parameters) == 2

        class DecoratorAgentBase(AgentManifest):
            @property
            def name(self) -> str:
                return name or fn.__name__

            @property
            def description(self) -> str:
                return description or inspect.getdoc(fn) or ""

            @property
            def metadata(self) -> dict[str, Any]:
                return metadata or {}

            @property
            def input_content_types(self) -> list[str]:
                return input_content_types or ["*/*"]

            @property
            def output_content_types(self) -> list[str]:
                return output_content_types or ["*/*"]
                
            @property
            def capabilities(self) -> AgentCapabilities:
                if capabilities:
                    return AgentCapabilities(**capabilities)
                return AgentCapabilities()
                
            @property
            def skills(self) -> list[AgentSkill]:
                if not skills:
                    return []
                return [AgentSkill(**skill) for skill in skills]

        # The following code would need to be implemented based on the actual Message and Context types
        # and the RunYield and RunYieldResume types from your framework
        
        agent: AgentManifest



        return agent

    return decorator
