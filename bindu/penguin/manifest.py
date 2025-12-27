#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""
Agent manifest creation and validation for the Penguine system.

This module provides core functions for creating AgentManifests from user functions
and validating protocol compliance for agents and workflows.
"""

import inspect
from datetime import UTC, datetime
from typing import Any, Callable, Literal
from uuid import UUID

from bindu.common.models import AgentManifest
from bindu.extensions.did import DIDAgentExtension
from bindu.common.protocol.types import (
    AgentCapabilities,
    AgentTrust,
    Skill,
)
from bindu.utils.logging import get_logger

logger = get_logger("bindu.penguin.manifest")


def _create_default_agent_trust() -> AgentTrust:
    """Create a default AgentTrust configuration with minimal required fields.

    Returns:
        AgentTrust: A minimal valid AgentTrust instance for agents without
                    explicit trust configuration.
    """
    return AgentTrust(
        identity_provider="custom",
        inherited_roles=[],
        creator_id="system",
        creation_timestamp=int(datetime.now(UTC).timestamp()),
        trust_verification_required=False,
        allowed_operations={},
    )


def validate_agent_function(agent_function: Callable) -> None:
    """Validate that the function has the correct signature for protocol compliance.

    Args:
        agent_function: The function to validate

    Raises:
        ValueError: If function signature is invalid
    """
    func_name = getattr(agent_function, "__name__", "<unknown>")
    logger.debug(f"Validating agent function: {func_name}")

    params = list(inspect.signature(agent_function).parameters.values())

    if not params:
        raise ValueError(
            "Agent function must have at least 'messages' parameter of type list[binduMessage]"
        )

    if len(params) > 1:
        raise ValueError("Agent function must have only 'messages' parameter")

    if params[0].name != "messages":
        raise ValueError(
            f"First parameter must be named 'messages', got '{params[0].name}'"
        )

    logger.debug(f"Agent function '{func_name}' validated successfully")


def create_manifest(
    agent_function: Callable,
    id: UUID,
    did_extension: DIDAgentExtension,
    name: str | None,
    description: str | None,
    skills: list[Skill] | None,
    capabilities: AgentCapabilities | None,
    agent_trust: AgentTrust | None,
    version: str,
    url: str,
    protocol_version: str = "1.0.0",
    kind: Literal["agent", "team", "workflow"] = "agent",
    debug_mode: bool = False,
    debug_level: Literal[1, 2] = 1,
    monitoring: bool = False,
    telemetry: bool = True,
    oltp_endpoint: str | None = None,
    oltp_service_name: str | None = None,
    num_history_sessions: int = 10,
    negotiation: dict[str, Any] | None = None,
    enable_system_message: bool = True,
    enable_context_based_history: bool = False,
    documentation_url: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
    global_webhook_url: str | None = None,
    global_webhook_token: str | None = None,
) -> AgentManifest:
    """Create a protocol-compliant AgentManifest from any Python function.

    This function is the core of the bindu framework's agent creation system. It analyzes
    user-defined functions and transforms them into fully-featured agents that can be deployed,
    discovered, and communicated with in the bindu distributed agent network.

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
        skills: List of Skill objects defining agent capabilities.
        capabilities: AgentCapabilities defining technical features (streaming, notifications, etc.).
        agent_trust: AgentTrust configuration for security and trust management.
        version: Agent version string (e.g., "1.0.0").
        url: Agent URL where the agent is hosted.
        protocol_version: bindu protocol version (default: "1.0.0").
        kind: Agent type - 'agent', 'team', or 'workflow' (default: 'agent').
        debug_mode: Enable debug mode for detailed logging (default: False).
        debug_level: Debug verbosity level - 1 or 2 (default: 1).
        monitoring: Enable monitoring and metrics collection (default: False).
        telemetry: Enable telemetry data collection (default: True).
        num_history_sessions: Number of conversation history sessions to maintain (default: 10).
        negotiation: Negotiation configuration (optional).
        enable_system_message: Enable system message/prompt in agent execution (default: True).
        enable_context_based_history: Enable context-based history in agent execution (default: False).
        documentation_url: URL to agent documentation (optional).
        extra_metadata: Additional metadata dictionary to attach to the agent manifest (default: {}).
        global_webhook_url: Default webhook URL for all tasks (optional).
        global_webhook_token: Authentication token for global webhook (optional).

    Returns:
        AgentManifest: A protocol-compliant agent manifest with proper execution methods.

    Raises:
        ValueError: If agent_function doesn't have required 'input' parameter or has invalid signature.

    """
    # Analyze function signature for parameter detection
    func_name = getattr(agent_function, "__name__", "<unknown>")
    logger.debug(f"Creating manifest for agent function: {func_name}")
    sig = inspect.signature(agent_function)
    param_names = list(sig.parameters.keys())
    has_context_param = "context" in param_names

    logger.debug(f"Function parameters: {param_names}, has_context={has_context_param}")

    # Prepare manifest metadata
    manifest_name = name or getattr(agent_function, "__name__", "agent").replace(
        "_", "-"
    )
    manifest_description = (
        description or inspect.getdoc(agent_function) or f"Agent: {manifest_name}"
    )

    logger.info(
        f"Creating agent manifest: name='{manifest_name}', version={version}, kind={kind}"
    )

    _agent_trust = (
        agent_trust if agent_trust is not None else _create_default_agent_trust()
    )
    _capabilities = capabilities if capabilities is not None else AgentCapabilities()
    _skills = skills if skills is not None else []

    # Create base manifest
    manifest = AgentManifest(
        id=id,
        did_extension=did_extension,
        name=manifest_name,
        description=manifest_description,
        url=url,
        version=version,
        protocol_version=protocol_version,
        agent_trust=_agent_trust,
        capabilities=_capabilities,
        skills=_skills,
        kind=kind,
        num_history_sessions=num_history_sessions,
        enable_system_message=enable_system_message,
        enable_context_based_history=enable_context_based_history,
        extra_data=extra_metadata or {},
        debug_mode=debug_mode,
        debug_level=debug_level,
        monitoring=monitoring,
        telemetry=telemetry,
        oltp_endpoint=oltp_endpoint,
        oltp_service_name=oltp_service_name,
        documentation_url=documentation_url,
        negotiation=negotiation,
        global_webhook_url=global_webhook_url,
        global_webhook_token=global_webhook_token,
    )

    # Create execution method based on function type
    def _create_run_method():
        """Create the appropriate run method based on function type."""

        def _resolve_params(input_msg: str, **kwargs) -> tuple:
            """Resolve function parameters based on signature analysis.

            Note: Context is managed at session level via context_id in the architecture.
            Each session IS a context, so no separate context parameter needed.

            Args:
                input_msg: The input message to process
                **kwargs: Additional keyword arguments

            Returns:
                Tuple of parameters to pass to the agent function
            """
            if has_context_param:
                session_context = kwargs.get("session_context", {})
                return (input_msg, session_context)
            else:
                return (input_msg,)

        # Async generator function (streaming)
        if inspect.isasyncgenfunction(agent_function):
            logger.debug(f"Creating async generator run method for '{manifest_name}'")

            async def run(input_msg: str, **kwargs):
                params = _resolve_params(input_msg, **kwargs)
                try:
                    gen = agent_function(*params)
                    value = None
                    while True:
                        value = yield await gen.asend(value)
                except StopAsyncIteration:
                    pass

        # Coroutine function (async single/multi result)
        elif inspect.iscoroutinefunction(agent_function):
            logger.debug(f"Creating coroutine run method for '{manifest_name}'")

            async def run(input_msg: str, **kwargs):
                params = _resolve_params(input_msg, **kwargs)
                result = await agent_function(*params)

                # Handle different result types
                if hasattr(result, "__aiter__"):
                    async for chunk in result:
                        yield chunk
                elif hasattr(result, "__iter__") and not isinstance(
                    result, (str, bytes)
                ):
                    for chunk in result:
                        yield chunk
                else:
                    yield result

        # Sync generator function
        elif inspect.isgeneratorfunction(agent_function):
            logger.debug(f"Creating sync generator run method for '{manifest_name}'")

            def run(input_msg: str, **kwargs):
                params = _resolve_params(input_msg, **kwargs)
                yield from agent_function(*params)

        # Regular sync function
        else:
            logger.debug(f"Creating sync function run method for '{manifest_name}'")

            def run(input_msg: str, **kwargs):
                params = _resolve_params(input_msg, **kwargs)
                return agent_function(*params)

        return run

    # Attach run method to manifest
    manifest.run = _create_run_method()
    logger.debug(f"Run method attached to manifest '{manifest_name}'")

    # Attach extra metadata attributes if provided
    if extra_metadata:
        logger.debug(
            f"Attaching extra metadata to manifest '{manifest_name}': {list(extra_metadata.keys())}"
        )
        for key, value in extra_metadata.items():
            setattr(manifest, key, value)

    logger.info(f"Agent manifest '{manifest_name}' created successfully (id={id})")
    return manifest
