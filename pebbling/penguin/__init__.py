# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧
"""🤖 Agent Framework: Universal AI Agent Orchestration

The heart of Pebbling - where any AI agent becomes a networked, secure, discoverable entity.
Transform agents from any framework (Agno, CrewAI, LangChain) into production-ready services.

"""

from .pebblify import pebblify
from .manifest import validate_agent_function, create_manifest

__all__ = [
    "pebblify",
    "validate_agent_function", 
    "create_manifest",
]
