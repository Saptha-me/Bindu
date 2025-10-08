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
from .did_endpoints import agent_info_endpoint, did_resolve_endpoint
from .static_files import (
    agent_js_endpoint,
    agent_page_endpoint,
    api_js_endpoint,
    chat_js_endpoint,
    chat_page_endpoint,
    common_js_endpoint,
    custom_css_endpoint,
    head_loader_js_endpoint,
    storage_js_endpoint,
    storage_page_endpoint,
)

__all__ = [
    # A2A Protocol
    "agent_run_endpoint",
    # Agent Card
    "agent_card_endpoint",
    # DID Endpoints
    "did_resolve_endpoint",
    "agent_info_endpoint",
    # Static Files & Pages
    "agent_page_endpoint",
    "chat_page_endpoint",
    "storage_page_endpoint",
    # JavaScript files
    "common_js_endpoint",
    "api_js_endpoint",
    "agent_js_endpoint",
    "chat_js_endpoint",
    "storage_js_endpoint",
    "head_loader_js_endpoint",
    # CSS files
    "custom_css_endpoint",
]
