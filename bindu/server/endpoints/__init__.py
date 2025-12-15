# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Endpoint modules for Bindu server."""

from .a2a_protocol import agent_run_endpoint
from .agent_card import agent_card_endpoint
from .did_endpoints import did_resolve_endpoint
from .negotiation import negotiation_endpoint
from .payment_sessions import (
    payment_capture_endpoint,
    payment_status_endpoint,
    start_payment_session_endpoint,
)
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
    "did_info_endpoint",
    # Negotiation
    "negotiation_endpoint",
    # Payment Sessions
    "start_payment_session_endpoint",
    "payment_capture_endpoint",
    "payment_status_endpoint",
    # Skills Endpoints
    "skills_list_endpoint",
    "skill_detail_endpoint",
    "skill_documentation_endpoint",
]
