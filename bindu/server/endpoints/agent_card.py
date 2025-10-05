"""Agent card endpoint for W3C-compliant agent discovery."""

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import AgentCard, agent_card_ta

if TYPE_CHECKING:
    from ..applications import PebbleApplication


async def agent_card_endpoint(app: "PebbleApplication", request: Request) -> Response:
    """Serve the agent card JSON schema.
    
    This endpoint provides W3C-compliant agent discovery information.
    """
    if app._agent_card_json_schema is None:
        from time import time

        # Create a complete AgentCard with all required fields
        agent_card = AgentCard(
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
        app._agent_card_json_schema = agent_card_ta.dump_json(agent_card, by_alias=True)
    
    return Response(content=app._agent_card_json_schema, media_type="application/json")
