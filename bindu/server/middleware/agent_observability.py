import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from bindu.utils.logging import get_logger
from .agent_health import agent_health_registry

logger = get_logger("bindu.server.middleware.agent_observability")


class AgentExecutionObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        agent_id = "unknown"

        if hasattr(request.app, "manifest") and request.app.manifest:
            try:
                agent_id = request.app.manifest.did_extension.did
            except Exception:
                pass

        success = True

        try:
            response: Response = await call_next(request)
            return response
        except Exception:
            success = False
            raise
        finally:
            latency_ms = (time.time() - start_time) * 1000

            agent_health_registry.record(
                agent_id=agent_id,
                latency=latency_ms,
                success=success,
            )

            logger.debug(
                "agent_execution",
                agent_id=agent_id,
                path=request.url.path,
                latency_ms=round(latency_ms, 2),
                success=success,
            )