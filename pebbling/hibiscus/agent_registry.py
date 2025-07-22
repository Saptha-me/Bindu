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
Agent registry integration module for registering Pebbling agents with Hibiscus registry.

This module handles agent registration with external registries, primarily Hibiscus,
allowing agents to be discovered and accessed by other systems.
"""

import asyncio
from typing import Any

from pydantic.types import SecretStr

from pebbling.hibiscus.registry import HibiscusClient
from pebbling.protocol.types import AgentManifest
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.hibiscus.agent_registry")

def register_with_registry(
    agent_manifest: AgentManifest,
    agent_registry_pat_token: SecretStr,
    agent_registry: str = "hibiscus",
    agent_registry_url: str = "http://localhost:19191",
    **kwargs: Any
):
    if agent_registry == "hibiscus":
        logger.info(f"Registering agent with Hibiscus at {agent_registry_url}")
        hibiscus_client: HibiscusClient = HibiscusClient(
            hibiscus_url=agent_registry_url,
            pat_token=agent_registry_pat_token
        )
        try:
            asyncio.run(hibiscus_client.register_agent(
                agent_manifest=agent_manifest,
                **kwargs
            ))
            if agent_manifest.did:
                logger.info(f"Agent registered with DID: {agent_manifest.did}")
        except Exception as e:
            logger.error(f"Failed to register agent with Hibiscus: {str(e)}")
    elif agent_registry == "custom":
        logger.info("Using custom agent registry")
        raise ValueError("Custom agent registry not implemented yet")
    else:
        logger.error(f"Unknown agent registry: {agent_registry}")
        raise ValueError(f"Unknown agent registry: {agent_registry}")