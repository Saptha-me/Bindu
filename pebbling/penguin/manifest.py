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

from pebbling.common.protocol.types import (
    AgentCapabilities, 
    AgentManifest, 
    AgentSkill, 
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
    identity: Optional[AgentIdentity] = None,
) -> AgentManifest:
    """
    Create a protocol-compliant AgentManifest from any Python function.
    
    This function is the core of the Pebbling framework's agent creation system. It analyzes
    user-defined functions and transforms them into fully-featured agents that can be deployed,
    discovered, and communicated with in the Pebbling distributed agent network.
    
    The function automatically detects the type of user function (async generator, coroutine,
    generator, or regular function) and creates appropriate wrapper classes that maintain
    protocol compliance while preserving the original function's behavior.
    
    Args:
        agent_function: The user's agent function to wrap. Must have 'input' as first parameter.
                       Can optionally have 'context' or 'execution_state' parameters.
        name: Human-readable agent name. If None, uses function name with underscores → hyphens.
        id: Unique identifier for the agent in the registry.
        description: Agent description. If None, uses function docstring or generates default.
        skills: List of AgentSkill objects defining agent capabilities.
        capabilities: AgentCapabilities defining technical features (streaming, notifications, etc.).
        version: Agent version string (e.g., "1.0.0").
        extra_metadata: Additional metadata to attach to the agent manifest.
        identity: Optional AgentIdentity for decentralized identity management.
    
    Returns:
        AgentManifest: A protocol-compliant agent manifest with proper execution methods.
    
    Raises:
        ValueError: If agent_function doesn't have required 'input' parameter or has invalid signature.
    
    Function Type Detection:
        The function automatically detects and handles four types of Python functions:
        
        1. **Async Generator Functions** (`async def` + `yield`):
           - Detected with: inspect.isasyncgenfunction()
           - Creates: AsyncGenDecoratorAgent with async streaming support
           - Use case: Agents that stream multiple responses over time
           
        2. **Coroutine Functions** (`async def` + `return`):
           - Detected with: inspect.iscoroutinefunction()
           - Creates: CoroDecoratorAgent with async execution
           - Use case: Agents that perform async operations and return single result
           
        3. **Generator Functions** (`def` + `yield`):
           - Detected with: inspect.isgeneratorfunction()
           - Creates: GenDecoratorAgent with sync streaming
           - Use case: Agents that yield multiple results synchronously
           
        4. **Regular Functions** (`def` + `return`):
           - Default case when others don't match
           - Creates: FuncDecoratorAgent with direct execution
           - Use case: Simple agents with synchronous processing
    
    Examples:
        
        # Async Generator Agent (Streaming Weather Forecast)
        @pebblify(name="Weather Agent", version="1.0.0")
        async def weather_agent(input: str, context=None):
            '''Provides streaming weather updates.'''
            yield f"🌤️ Fetching weather for: {input}"
            await asyncio.sleep(1)  # Simulate API call
            yield f"☀️ Current temp: 22°C, Sunny"
            yield f"📅 3-day forecast: Sunny, Cloudy, Rainy"
        
        # Coroutine Agent (Single Response)
        @pebblify(name="Translator", version="1.0.0")
        async def translator_agent(input: str):
            '''Translates text to different languages.'''
            await asyncio.sleep(0.5)  # Simulate translation API
            return f"Translated: {input} → Bonjour le monde"
        
        # Generator Agent (Batch Processing)
        @pebblify(name="Data Processor", version="1.0.0")
        def batch_processor(input: str):
            '''Processes data in batches.'''
            data_items = input.split(',')
            for i, item in enumerate(data_items):
                yield f"Processed batch {i+1}: {item.strip()}"
        
        # Regular Function Agent (Simple Processing)
        @pebblify(name="Echo Agent", version="1.0.0")
        def echo_agent(input: str):
            '''Simple echo agent.'''
            return f"Echo: {input.upper()}"
    
    Parameter Detection:
        The function analyzes the user function's parameters to determine execution context:
        
        - **input**: Required first parameter for agent input
        - **context**: Optional parameter for execution context (user preferences, session data)
        - **execution_state**: Optional parameter for pause/resume functionality
    
    Dynamic Class Generation:
        Creates a DecoratorBase class that inherits from AgentManifest and implements:
        - All required AgentManifest properties (id, name, description, etc.)
        - Protocol-compliant run() method that wraps the original function
        - Proper async/sync execution based on function type
        - Context and execution state handling
    
    Security Integration:
        When security and identity parameters are provided:
        - Integrates with DID-based authentication system
        - Supports JWT token generation and verification
        - Enables secure agent-to-agent communication
        - Works with Hibiscus registry for agent discovery
    
    Note:
        Agent names automatically convert underscores to hyphens since underscores
        are not allowed in agent names in the Pebbling protocol.
    """
    
    # Since function is already validated, we can directly check parameter names
    sig = inspect.signature(agent_function)
    param_names = list(sig.parameters.keys())
    has_context_param = 'context' in param_names
    has_execution_state = 'execution_state' in param_names
    
    # Use function name if name not provided - store with different variable names
    _name = name or agent_function.__name__.replace('_', '-') # underscores are not allowed in agent names so replace them with hyphens
    _description = description or inspect.getdoc(agent_function) or f"Agent: {_name}"
    _id = id
    _version = version
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
