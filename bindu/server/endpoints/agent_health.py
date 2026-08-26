from starlette.requests import Request
from starlette.responses import JSONResponse

from bindu.server.middleware.agent_health import agent_health_registry


async def agent_health_endpoint(app, request: Request):
    return JSONResponse(
        {
            "agents": agent_health_registry.get_stats()
        }
    )