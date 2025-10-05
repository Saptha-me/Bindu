"""Static file serving endpoints."""

from pathlib import Path
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import FileResponse, Response

if TYPE_CHECKING:
    from ..applications import PebbleApplication


async def docs_endpoint(request: Request) -> Response:
    """Serve the documentation interface."""
    docs_path = Path(__file__).parent.parent / "static" / "docs.html"
    return FileResponse(docs_path, media_type="text/html")


async def agent_page_endpoint(request: Request) -> Response:
    """Serve the agent information page."""
    agent_path = Path(__file__).parent.parent / "static" / "agent.html"
    return FileResponse(agent_path, media_type="text/html")


async def chat_page_endpoint(request: Request) -> Response:
    """Serve the chat interface page."""
    chat_path = Path(__file__).parent.parent / "static" / "chat.html"
    return FileResponse(chat_path, media_type="text/html")


async def storage_page_endpoint(request: Request) -> Response:
    """Serve the storage management page."""
    storage_path = Path(__file__).parent.parent / "static" / "storage.html"
    return FileResponse(storage_path, media_type="text/html")


async def common_js_endpoint(request: Request) -> Response:
    """Serve the common JavaScript file."""
    js_path = Path(__file__).parent.parent / "static" / "common.js"
    return FileResponse(js_path, media_type="application/javascript")


async def common_css_endpoint(request: Request) -> Response:
    """Serve the common CSS file."""
    css_path = Path(__file__).parent.parent / "static" / "common.css"
    return FileResponse(css_path, media_type="text/css")


async def layout_js_endpoint(request: Request) -> Response:
    """Serve the layout JavaScript file."""
    js_path = Path(__file__).parent.parent / "static" / "components" / "layout.js"
    return FileResponse(js_path, media_type="application/javascript")


async def header_component_endpoint(request: Request) -> Response:
    """Serve the header component."""
    header_path = Path(__file__).parent.parent / "static" / "components" / "header.html"
    return FileResponse(header_path, media_type="text/html")


async def footer_component_endpoint(request: Request) -> Response:
    """Serve the footer component."""
    footer_path = Path(__file__).parent.parent / "static" / "components" / "footer.html"
    return FileResponse(footer_path, media_type="text/html")
