"""Agent card endpoint for W3C-compliant agent discovery."""

import logging
from time import time
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import AgentCard, agent_card_ta
from bindu.server.utils.request_utils import get_client_ip

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = logging.getLogger("bindu.server.endpoints.agent_card")


def _create_agent_card(app: "BinduApplication") -> AgentCard:
    """Create agent card from application manifest.
    
    Args:
        app: BinduApplication instance
        
    Returns:
        AgentCard instance
    """
    return AgentCard(
        id=app.manifest.id,
        name=app.manifest.name,
        description=app.manifest.description or "An AI agent exposed as an Pebble agent.",
        url=app.url,
        version=app.version,
        protocol_version="0.2.5",
        skills=app.manifest.skills,
        capabilities=app.manifest.capabilities,
        kind=app.manifest.kind,
        num_history_sessions=app.manifest.num_history_sessions,
        extra_data=app.manifest.extra_data or {"created": int(time()), "server_info": "bindu Agent Server"},
        debug_mode=app.manifest.debug_mode,
        debug_level=app.manifest.debug_level,
        monitoring=app.manifest.monitoring,
        telemetry=app.manifest.telemetry,
        agent_trust=app.manifest.agent_trust,
    )


async def agent_card_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Serve the agent card JSON schema.
    
    This endpoint provides W3C-compliant agent discovery information.
    """
    client_ip = get_client_ip(request)
    
    try:
        # Lazy initialization of agent card schema
        if app._agent_card_json_schema is None:
            logger.debug("Generating agent card schema")
            agent_card = _create_agent_card(app)
            app._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)
        
        logger.debug(f"Serving agent card to {client_ip}")
        return Response(content=app._agent_card_json_schema, media_type="application/json")
        
    except Exception as e:
        logger.error(f"Error serving agent card to {client_ip}: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )
