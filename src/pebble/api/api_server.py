from typing import Any, Union, Optional, Set
from urllib.parse import quote

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rich import box
from rich.panel import Panel
from rich import console

from .routers.router import get_router
from ..settings.settings import pebbleSettings
from ..core.agent import BaseAgent
from ..core.cognitive_agent import CognitiveAgent

from agno.agent import Agent as agnoAgent
from smolagents import CodeAgent as smolAgent
from crewai import Agent as crewaiAgent

def get_settings():
    """Get application settings.
    
    Returns:
        pebbleSettings: Application settings
    """
    return pebbleSettings()




class PebbleServer:
    def __init__(self,
                 connection_string: str = None,
                 redis_host: str = None,
                 redis_port: int = None):
        # For simplified usage in example scripts
        self.settings = get_settings()
        
        # Create a simple FastAPI app
        self.app = FastAPI(
            title="Pebble Agent API",
            description="API for interacting with deployed agents",
            docs_url="/docs"
        )

        # Rate Limiting
        self.rate_limit = {
            "requests": 60,  # per minute
            "window": 60    # seconds
        }

        # Cache TTL
        self.cache_ttl = 300  # 5 minutes

        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": str(exc.detail)},
            )

        async def general_exception_handler(request: Request, call_next):
            try:
                return await call_next(request)
            except Exception as e:
                return JSONResponse(
                    status_code=e.status_code if hasattr(e, "status_code") else 500,
                    content={"detail": str(e)},
                )

        self.app.middleware("http")(general_exception_handler)

        # Nothing more to initialize

    def setup_tool_routers(self):
        """Set up API routers for the app.
        This is a placeholder method that can be extended later.
        """
        # For a simplified version, we don't need specific tool routers
        router = get_router()
        self.app.include_router(router)

    def get_app(self) -> FastAPI:
        return self.app

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)

