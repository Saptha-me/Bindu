# bindu/server/endpoints/health.py
from starlette.responses import JSONResponse
from starlette.requests import Request
import time
import os
from typing import Dict, Any

_start_time = time.time()
APP_VERSION = os.environ.get("BINDU_VERSION", "dev")


async def health_endpoint(app, request: Request) -> JSONResponse:
    """
    Health endpoint intended to be registered with `with_app=True` so the app
    instance is supplied as the first argument.
    """
    uptime = round(time.time() - _start_time, 2)
    payload: Dict[str, Any] = {
        "status": "ok",
        "uptime_seconds": uptime,
        "version": APP_VERSION,
        "ready": True,
    }
    return JSONResponse(payload)
