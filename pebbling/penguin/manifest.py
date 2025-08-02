# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Agent manifest creation and validation for the Penguine system.

This module provides core functions for creating AgentManifests from user functions
and validating protocol compliance for agents and workflows.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional

from pebbling.protocol.types import (
    AgentCapabilities, 
    AgentManifest, 
    AgentSkill, 
    AgentSecurity, 
    AgentIdentity
)


def validate_agent_function(agent_function: Callable):
    """Validate that the function has the correct signature for protocol compliance."""
    signature = inspect.signature(agent_function)
    params = list(signature.parameters.values())
    
    if len(params) < 1:
        raise ValueError(
            "Agent function must have at least 'input' parameter of type PebblingMessage"
        )
    
    if len(params) > 1:
        raise ValueError(
            "Agent function must have only 'input' and optional 'context' parameters"
        )
    
    # Check parameter names
    if params[0].name != "input":
        raise ValueError("First parameter must be named 'input'")


def create_manifest(
    agent_function: Callable,
    name: Optional[str],
    id: str,
    description: Optional[str],
    skills: Optional[List[AgentSkill]],
    capabilities: Optional[AgentCapabilities],
    version: str,
    extra_metadata: Optional[Dict[str, Any]],
    security: Optional[AgentSecurity] = None,
    identity: Optional[AgentIdentity] = None,
) -> AgentManifest:
    """Create dynamic agent class from function analysis."""
    
    # Since function is already validated, we can directly check parameter names
    sig = inspect.signature(agent_function)
    param_names = list(sig.parameters.keys())
    has_context_param = 'context' in param_names
    has_execution_state = 'execution_state' in param_names
    
    # Use function name if name not provided - store with different variable names
    _name = name or agent_function.__name__.replace('_', '-')
    _description = description or inspect.getdoc(agent_function) or f"Agent: {_name}"
    _id = id
    _version = version
    _security = security
    _identity = identity
    _skills = skills
    _capabilities = capabilities
    
    # Create default capabilities if not provided
    if _capabilities is None:
        _capabilities = AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=False
        )

    class DecoratorBase(AgentManifest):
        def __init__(self):
            # Initialize Pydantic model with the captured values
            super().__init__(
                id=_id,
                name=_name,
                description=_description,
                capabilities=_capabilities,
                skill=_skills[0] if _skills else None,
                version=_version,
                security=_security,
                identity=_identity
            )
        
        @property
        def id(self) -> str:
            return self.id
        
        @property
        def name(self) -> str:
            return self.name
        
        @property
        def description(self) -> str:
            return self.description
        
        @property
        def capabilities(self) -> AgentCapabilities:
            return self.capabilities
        
        @property
        def skill(self) -> Optional[AgentSkill]:
            return self.skill
        
        @property
        def version(self) -> str:
            return self.version
        
        @property
        def security(self) -> Optional[AgentSecurity]:
            return self.security
        
        @property  
        def identity(self) -> Optional[AgentIdentity]:
            return self.identity
    
    # Create agent based on function type
    agent: AgentManifest
    
    if inspect.isasyncgenfunction(agent_function):
        class AsyncGenDecoratorAgent(DecoratorBase):
            async def run(self, input_msg: str, context=None, **kwargs):
                """Run async generator agent function."""
                try:
                    if has_execution_state:
                        # Handle execution state for pause/resume
                        execution_state = kwargs.get('execution_state')
                        gen = agent_function(input_msg, execution_state)
                    elif has_context_param:
                        gen = agent_function(input_msg, context)
                    else:
                        gen = agent_function(input_msg)
                    
                    async for result in gen:
                        yield result
                        
                except StopAsyncIteration:
                    pass
        
        agent = AsyncGenDecoratorAgent()
        
    elif inspect.iscoroutinefunction(agent_function):
        class CoroDecoratorAgent(DecoratorBase):
            async def run(self, input_msg: str, context=None, **kwargs):
                """Run coroutine agent function."""
                if has_execution_state:
                    execution_state = kwargs.get('execution_state')
                    return await agent_function(input_msg, execution_state)
                elif has_context_param:
                    return await agent_function(input_msg, context)
                else:
                    return await agent_function(input_msg)
        
        agent = CoroDecoratorAgent()
        
    elif inspect.isgeneratorfunction(agent_function):
        class GenDecoratorAgent(DecoratorBase):
            def run(self, input_msg: str, context=None, **kwargs):
                """Run generator agent function."""
                if has_execution_state:
                    execution_state = kwargs.get('execution_state')
                    yield from agent_function(input_msg, execution_state)
                elif has_context_param:
                    yield from agent_function(input_msg, context)
                else:
                    yield from agent_function(input_msg)
        
        agent = GenDecoratorAgent()
        
    else:
        class FuncDecoratorAgent(DecoratorBase):
            def run(self, input_msg: str, context=None, **kwargs):
                """Run regular function agent."""
                if has_execution_state:
                    execution_state = kwargs.get('execution_state')
                    return agent_function(input_msg, execution_state)
                elif has_context_param:
                    return agent_function(input_msg, context)
                else:
                    return agent_function(input_msg)
        
        agent = FuncDecoratorAgent()
    
    # Add extra metadata if provided
    if extra_metadata:
        for key, value in extra_metadata.items():
            setattr(agent, key, value)
    
    return agent
