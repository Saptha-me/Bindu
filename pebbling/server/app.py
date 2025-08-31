from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from pebbling.protocol.types import AgentManifest
from pebbling.server.task_manager import TaskManager
from pebbling.server.storage import Storage
from pebbling.server.broker import Broker


@asynccontextmanager
async def default_lifespan(app: FastAPI):
    """Default lifespan manager for Pebble server."""
    yield


def create_app(
    *agents: AgentManifest,
    lifespan=None,
    task_manager: TaskManager | None = None,
    storage: Storage | None = None,
    broker: Broker | None = None,
) -> FastAPI:
    """Create a Pebble FastAPI application with A2A protocol support.
    
    Args:
        *agents: Agent manifests to register with the server
        lifespan: FastAPI lifespan context manager
        task_manager: Optional task manager instance
        storage: Optional storage instance  
        broker: Optional broker instance
        
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="Pebble Server",
        description="A2A-compatible server for Pebble agents",
        version="1.0.0",
        lifespan=lifespan or default_lifespan
    )
    
    # Store components in app state
    app.state.agents = list(agents)
    app.state.task_manager = task_manager
    app.state.storage = storage
    app.state.broker = broker
    
    # Add A2A protocol endpoints
    @app.post("/message/send")
    async def send_message(request: dict):
        """A2A protocol message sending endpoint."""
        if not app.state.task_manager:
            raise RuntimeError("TaskManager not configured")
        async with app.state.task_manager:
            return await app.state.task_manager.send_message(request)
    
    @app.get("/task/{task_id}")
    async def get_task(task_id: str):
        """A2A protocol task retrieval endpoint."""
        if not app.state.task_manager:
            raise RuntimeError("TaskManager not configured")
        request = {"jsonrpc": "2.0", "id": 1, "params": {"id": task_id}}
        async with app.state.task_manager:
            return await app.state.task_manager.get_task(request)
    
    @app.get("/agents")
    async def list_agents():
        """List registered agents."""
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "capabilities": agent.capabilities.model_dump() if agent.capabilities else None
            }
            for agent in app.state.agents
        ]
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "agents": len(app.state.agents)}
    
    return app