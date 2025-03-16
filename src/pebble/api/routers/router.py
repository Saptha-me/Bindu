import orjson
from dataclasses import asdict
from io import BytesIO
from typing import Generator, List, Optional, Union, cast

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from agno.agent import Agent as agnoAgent
from smolagents import CodeAgent as smolAgent
from crewai import Agent as crewaiAgent

from pebble import settings
from .agent_router import create_agent_router
from .cognitive_router import create_cognitive_router

def get_router(
    agent: Optional[Union[agnoAgent, smolAgent, crewaiAgent]] = None, workflows: Optional[List] = None
) -> APIRouter:
    router = APIRouter(prefix="/pebble", tags=["Pebble"])

    # Include the agent router
    agent_router = create_agent_router()
    router.include_router(agent_router)
    
    # Include the cognitive router
    cognitive_router = create_cognitive_router()
    router.include_router(cognitive_router)

    @router.get("/status")
    def status():
        return {"status": "available", "api_version": "1.0.0"}

    return router
