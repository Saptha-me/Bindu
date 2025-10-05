"""Endpoint modules for Pebble server."""

from .a2a_protocol import agent_run_endpoint
from .agent_card import agent_card_endpoint
from .did_endpoints import agent_info_endpoint, did_resolve_endpoint
from .static_files import (
    agent_page_endpoint,
    chat_page_endpoint,
    common_css_endpoint,
    common_js_endpoint,
    docs_endpoint,
    footer_component_endpoint,
    header_component_endpoint,
    layout_js_endpoint,
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
    # Static Files
    "docs_endpoint",
    "agent_page_endpoint",
    "chat_page_endpoint",
    "storage_page_endpoint",
    "common_js_endpoint",
    "common_css_endpoint",
    "layout_js_endpoint",
    "header_component_endpoint",
    "footer_component_endpoint",
]
