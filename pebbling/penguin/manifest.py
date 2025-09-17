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
from typing import Any, Callable, Dict, List, Literal, Optional
from uuid import UUID

from pebbling.common.models import AgentManifest
from pebbling.common.protocol.types import AgentCapabilities, AgentIdentity, AgentSkill, AgentTrust


def validate_agent_function(agent_function: Callable):
    """Validate that the function has the correct signature for protocol compliance."""
    signature = inspect.signature(agent_function)
    params = list(signature.parameters.values())

    if len(params) < 1:
        raise ValueError("Agent function must have at least 'messages' parameter of type list[PebblingMessage]")

    if len(params) > 1:
        raise ValueError("Agent function must have only 'messages' and optional 'context' parameters")

    # Check parameter names
    if params[0].name != "messages":
        raise ValueError("First parameter must be named 'messages'")


def create_manifest(
    agent_function: Callable,
    id: UUID,
    name: Optional[str],
    identity: AgentIdentity,
    description: Optional[str],
    skills: Optional[List[AgentSkill]],
    capabilities: Optional[AgentCapabilities],
    agent_trust: Optional[AgentTrust],
    version: str,
    url: str,
    protocol_version: str = "1.0.0",
    kind: Literal["agent", "team", "workflow"] = "agent",
    debug_mode: bool = False,
    debug_level: Literal[1, 2] = 1,
    monitoring: bool = False,
    telemetry: bool = True,
    num_history_sessions: int = 10,
    documentation_url: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = {},
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
        id: Agent ID (UUID).
        name: Human-readable agent name. If None, uses function name with underscores → hyphens.
        identity: AgentIdentity for decentralized identity management.
        description: Agent description. If None, uses function docstring or generates default.
        skills: List of AgentSkill objects defining agent capabilities.
        capabilities: AgentCapabilities defining technical features (streaming, notifications, etc.).
        agent_trust: AgentTrust configuration for security and trust management.
        version: Agent version string (e.g., "1.0.0").
        url: Agent URL where the agent is hosted.
        protocol_version: Pebbling protocol version (default: "1.0.0").
        kind: Agent type - 'agent', 'team', or 'workflow' (default: 'agent').
        debug_mode: Enable debug mode for detailed logging (default: False).
        debug_level: Debug verbosity level - 1 or 2 (default: 1).
        monitoring: Enable monitoring and metrics collection (default: False).
        telemetry: Enable telemetry data collection (default: True).
        num_history_sessions: Number of conversation history sessions to maintain (default: 10).
        documentation_url: URL to agent documentation (optional).
        extra_metadata: Additional metadata dictionary to attach to the agent manifest (default: {}).

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

    # Analyze function signature
    sig = inspect.signature(agent_function)
    param_names = list(sig.parameters.keys())
    has_context_param = "context" in param_names
    has_execution_state = "execution_state" in param_names

    # Prepare manifest data
    manifest_name = name or agent_function.__name__.replace("_", "-")
    manifest_description = description or inspect.getdoc(agent_function) or f"Agent: {manifest_name}"

    # Create base manifest
    manifest = AgentManifest(
        id=id,
        name=manifest_name,
        description=manifest_description,
        url=url,
        version=version,
        protocol_version=protocol_version,
        identity=identity,
        agent_trust=agent_trust,
        capabilities=capabilities,
        skills=skills,
        kind=kind,
        num_history_sessions=num_history_sessions,
        extra_data=extra_metadata,
        debug_mode=debug_mode,
        debug_level=debug_level,
        monitoring=monitoring,
        telemetry=telemetry,
        documentation_url=documentation_url,
    )

    # Add execution method based on function type
    def create_run_method():
        # Extract parameter resolution logic (DRY principle)
        def resolve_params(input_msg: str, **kwargs):
            """Resolve function parameters based on signature analysis.

            Note: Context is managed at session level via context_id in the architecture.
            Each session IS a context, so no separate context parameter needed.
            """
            if has_execution_state:
                return (input_msg, kwargs.get("execution_state"))
            elif has_context_param:
                # Context comes from session-level context_id, not parameter
                session_context = kwargs.get("session_context", {})
                return (input_msg, session_context)
            else:
                return (input_msg,)

        # Function type handlers following ACP pattern
        if inspect.isasyncgenfunction(agent_function):

            async def run(input_msg: str, **kwargs):
                params = resolve_params(input_msg, **kwargs)
                try:
                    gen = agent_function(*params)
                    value = None
                    while True:
                        value = yield await gen.asend(value)
                except StopAsyncIteration:
                    pass

        elif inspect.iscoroutinefunction(agent_function):

            async def run(input_msg: str, **kwargs):
                params = resolve_params(input_msg, **kwargs)
                result = await agent_function(*params)

                # Handle different result types from coroutine
                if hasattr(result, "__aiter__"):
                    # Result is async iterable (streaming)
                    async for chunk in result:
                        yield chunk
                elif hasattr(result, "__iter__") and not isinstance(result, (str, bytes)):
                    # Result is iterable but not string/bytes
                    for chunk in result:
                        yield chunk
                else:
                    # Single result - yield it (can't mix return and yield)
                    yield result

        elif inspect.isgeneratorfunction(agent_function):

            def run(input_msg: str, **kwargs):
                params = resolve_params(input_msg, **kwargs)
                yield from agent_function(*params)

        else:

            def run(input_msg: str, **kwargs):
                params = resolve_params(input_msg, **kwargs)
                return agent_function(*params)

        return run

    # Attach run method to manifest
    manifest.run = create_run_method()

    # Add extra metadata if provided
    if extra_metadata:
        for key, value in extra_metadata.items():
            setattr(manifest, key, value)

    return manifest
