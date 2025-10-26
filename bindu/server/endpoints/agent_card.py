"""Agent card endpoint for W3C-compliant agent discovery."""

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import Response

from bindu.common.protocol.types import agent_card_ta
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)
from bindu.utils.agent_card_utils import create_agent_card
from bindu.utils.endpoint_utils import handle_endpoint_errors
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import get_client_ip

if TYPE_CHECKING:
    from ..applications import BinduApplication

logger = get_logger("bindu.server.endpoints.agent_card")


@handle_endpoint_errors("agent card")
async def agent_card_endpoint(app: "BinduApplication", request: Request) -> Response:
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
