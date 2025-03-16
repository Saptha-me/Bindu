from typing import Any, Union, Optional, Set
from urllib.parse import quote

from fastapi import FastAPI, Request, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from rich import box
from rich.panel import Panel
import console

from .router import get_router
from ..settings.settings import PebbleSettings
from ..core.agent import BaseAgent
from ..core.cognitive_agent import CognitiveAgent

from agno.agent import Agent as agnoAgent
from smolagents import CodeAgent as smolAgent
from crewai import Agent as crewaiAgent


class PebbleServer:
    def __init__(
        self,
        agent: Optional[Union[agnoAgent, smolAgent, crewaiAgent, BaseAgent, CognitiveAgent]] = None,
    ): 
        if not agent:
            raise ValueError("We only support pebble agents (BaseAgent, CognitiveAgent), Agno, SmolAgents and CrewAI agents. See documentation for details.")

        self.agent = agent
        self.settings = PebbleSettings()
        self.endpoints_created: Set[str] = set()
        self.app = FastAPI(
            title=self.settings.title,
            description=self.settings.description,
            version=self.settings.version,
            docs_url="/docs"
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

        self.router = APIRouter(prefix="/v1")
        self.router.include_router(
            get_router(self.agent)
        )

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        return self.api_app

    def serve_app(
        self,
        host: str = "localhost",
        port: int = 8000,
        **kwargs: Any,
    ):
        import uvicorn
        import console

        endpoint = quote(f"{host}:{port}")

        panel = Panel(
            f"[bold green]Playground URL:[/bold green] [link={url}]{url}[/link]",
            title="Agent Playground",
            expand=False,
            border_style="cyan",
            box=box.HEAVY,
            padding=(2, 2),
        )
        console.print(panel)

        uvicorn.run(app=self.app, host=host, port=port, reload=reload, **kwargs)


import json
import time
import redis
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import APIRouter
from rich import box
from rich.panel import Panel
from functools import lru_cache
from typing import Any, Union, Dict, Optional


from agentbase.settings import AgentbaseSettings
from agentbase.ecosystem.tools.common.tool_store import ToolStore
from agentbase.api.routers.tools_router import tools_router  # Import the router

@lru_cache(maxsize=1)
def get_settings() -> AgentbaseSettings:
    return AgentbaseSettings()

class RedisManager:
    def __init__(self, **config):
        self.redis_client = redis.Redis(**config)
        self.prefix = config.get('prefix', 'agentbase:')
        
    def check_rate_limit(self, client_id: str, limit: int = 60, window: int = 60) -> bool:
        """Sliding window rate limiting"""
        now = time.time()
        key = f"{self.prefix}ratelimit:{client_id}"
        
        # Remove old requests
        self.redis_client.zremrangebyscore(key, 0, now - window)
        
        # Check current window
        if self.redis_client.zcard(key) >= limit:
            return False
            
        # Add request
        pipeline = self.redis_client.pipeline()
        pipeline.zadd(key, {str(now): now})
        pipeline.expire(key, window)
        pipeline.execute()
        return True
        
    def get_cache(self, key: str) -> Optional[Dict]:
        cached = self.redis_client.get(f"{self.prefix}cache:{key}")
        return json.loads(cached) if cached else None
        
    def set_cache(self, key: str, data: Dict, ttl: int = 300):
        self.redis_client.setex(
            f"{self.prefix}cache:{key}",
            ttl,
            json.dumps(data)
        )
        
    def clear_cache_pattern(self, pattern: str):
        pattern = f"{self.prefix}cache:{pattern}"
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)

class AgentbaseAPIServer:
    def __init__(self,
                 connection_string: str,
                 redis_host: str,
                 redis_port: int):
        self.settings = get_settings()

        # Initialize Redis
        redis_config = self.settings.redis_config.dict()
        redis_config.update({
            'host': redis_host,
            'port': redis_port
        })
        self.redis_manager = RedisManager(**redis_config)

        # Initialize ToolStore
        self.tool_store = ToolStore(
            connection_string=connection_string
        )

        # Rate Limiting
        self.rate_limit = {
            "requests": 60,  # per minute
            "window": 60    # seconds
        }

        # Cache TTL
        self.cache_ttl = 300  # 5 minutes

        # Initialize FastAPI
        self.app = FastAPI(
            title=self.settings.projectsettings.name,
            description=self.settings.projectsettings.description,
            docs_url="/docs"
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

        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3773"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        # Initialize tool routers
        self.setup_tool_routers()

    def setup_tool_routers(self):
        # Tools router
        tools_router.redis_manager = self.redis_manager
        tools_router.tool_store = self.tool_store  # Pass ToolStore instance
        tools_router.rate_limit = self.rate_limit
        tools_router.cache_ttl = self.cache_ttl
        self.app.include_router(tools_router)

    def get_app(self) -> FastAPI:
        return self.app

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)

