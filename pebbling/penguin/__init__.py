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

from .manifest import create_manifest, validate_agent_function
from .pebblify import pebblify

__all__ = [
    "pebblify",
    "validate_agent_function",
    "create_manifest",
]
