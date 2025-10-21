# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Endpoint modules for Bindu server."""

from .a2a_protocol import agent_run_endpoint
from .agent_card import agent_card_endpoint
from .did_endpoints import did_resolve_endpoint
from .skills import (
    skill_detail_endpoint,
    skill_documentation_endpoint,
    skills_list_endpoint,
)

__all__ = [
    # A2A Protocol
    "agent_run_endpoint",
    # Agent Card
    "agent_card_endpoint",
    # DID Endpoints
    "did_resolve_endpoint",
    # Skills Endpoints
    "skills_list_endpoint",
    "skill_detail_endpoint",
    "skill_documentation_endpoint",
]
