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
from .agent_adapter import AgentAdapter, PebblingMessage, PebblingContext

__all__ = [
    "pebblify",
    "AgentAdapter", 
    "PebblingMessage",
    "PebblingContext",
]
