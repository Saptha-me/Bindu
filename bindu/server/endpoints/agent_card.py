"""Agent card endpoint for W3C-compliant agent discovery."""

from __future__ import annotations

from time import time
from uuid import UUID

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import AgentCard, agent_card_ta
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)
from bindu.server.applications import BinduApplication
from bindu.utils.request_utils import handle_endpoint_errors
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import get_client_ip

logger = get_logger("bindu.server.endpoints.agent_card")


def create_agent_card(app: BinduApplication) -> AgentCard:
    """Create agent card from application manifest.

    Args:
        app: BinduApplication instance

    Returns:
        AgentCard instance

    Note:
        Excludes skill documentation_content from agent card to reduce payload size.
        Full documentation is available via /agent/skills/{skill_id}/documentation
    """
    # Minimize skills to just id, name, and documentation_path (URL) - full details via dedicated endpoint
    minimal_skills = []
    for skill in app.manifest.skills:
        minimal_skills.append(
            {
                "id": skill["id"],
                "name": skill["name"],
                "documentation_path": f"{app.url}/agent/skills/{skill['id']}",
            }
        )

    # Ensure id is UUID type (convert from string if needed)
    agent_id = (
        app.manifest.id if isinstance(app.manifest.id, UUID) else UUID(app.manifest.id)
    )

    # Convert capabilities to serializable format
    # Extensions need to be converted from class instances to AgentExtension dicts
    capabilities = dict(app.manifest.capabilities)
    if "extensions" in capabilities:
        serializable_extensions = []
        for ext in capabilities["extensions"]:
            # Check if it's a DIDAgentExtension instance
            if hasattr(ext, "did") and hasattr(ext, "author"):
                serializable_extensions.append(
                    {
                        "uri": f"did:{ext.did}"
                        if not ext.did.startswith("did:")
                        else ext.did,
                        "description": f"DID-based identity for {ext.agent_name or 'agent'}",
                        "required": False,
                        "params": {
                            "author": ext.author,
                            "agent_name": ext.agent_name,
                            "agent_id": ext.agent_id,
                        },
                    }
                )
            elif isinstance(ext, dict):
                # Already in correct format
                serializable_extensions.append(ext)
            else:
                # Try to convert other extension types
                logger.warning(f"Unknown extension type: {type(ext)}, skipping")
        capabilities["extensions"] = serializable_extensions

    return AgentCard(
        id=agent_id,
        name=app.manifest.name,
        description=app.manifest.description or "An AI agent exposed as an A2A agent.",
        url=app.url,
        version=app.version,
        protocol_version="0.2.5",
        skills=minimal_skills,
        capabilities=capabilities,
        kind=app.manifest.kind,
        num_history_sessions=app.manifest.num_history_sessions,
        extra_data=app.manifest.extra_data
        or {"created": int(time()), "server_info": "bindu Agent Server"},
        debug_mode=app.manifest.debug_mode,
        debug_level=app.manifest.debug_level,
        monitoring=app.manifest.monitoring,
        telemetry=app.manifest.telemetry,
        agent_trust=app.manifest.agent_trust,
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
    )


@handle_endpoint_errors("agent card")
async def agent_card_endpoint(app: BinduApplication, request: Request) -> Response:
    """Serve the agent card JSON schema.

    This endpoint provides W3C-compliant agent discovery information.
    """
    client_ip = get_client_ip(request)

    # Lazy initialization of agent card schema
    if app._agent_card_json_schema is None:
        logger.debug("Generating agent card schema")
        agent_card = create_agent_card(app)
        app._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)

    logger.debug(f"Serving agent card to {client_ip}")
    resp = Response(content=app._agent_card_json_schema, media_type="application/json")
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp
