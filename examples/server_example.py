#!/usr/bin/env python3
# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Example Pebbling Server.

Demonstrates how to set up and run a unified server supporting both
JSON-RPC and HTTP protocols with the news reporter agent.
"""

import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager

from pebbling.server.core import get_server
from pebbling.protocol.types import AgentManifest, AgentCapabilities, AgentSkill

# Import your news reporter agent
from example import news_reporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan manager."""
    logger.info("Starting Pebbling Server...")
    
    # Get the server instance
    server = get_server()
    
    # Register the news reporter agent
    try:
        manifest = news_reporter()
        await server.register_agent(manifest)
        logger.info(f"Registered agent: {manifest.name}")
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
    
    logger.info("Server startup complete!")
    logger.info("Available endpoints:")
    logger.info("  JSON-RPC: POST /rpc")
    logger.info("  HTTP REST: GET /agents, POST /runs, etc.")
    logger.info("  Streaming: GET /stream/{task_id}")
    logger.info("  Health: GET /health")
    
    yield
    
    logger.info("Shutting down Pebbling Server...")


def create_app():
    """Create the FastAPI application with lifespan management."""
    from pebbling.server.core import create_app
    
    app = create_app()
    app.router.lifespan_context = lifespan
    return app


def main():
    """Run the server."""
    app = create_app()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
