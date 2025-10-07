"""Static file serving endpoints."""

import logging
from pathlib import Path
from typing import Callable, Optional

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from bindu.utils.constants import MEDIA_TYPES

logger = logging.getLogger("bindu.server.endpoints.static_files")


def _serve_static_file(
    file_path: Path, 
    media_type: str, 
    request: Request
) -> Response:
    """Serve a static file with error handling and logging.
    
    Args:
        file_path: Path to the file to serve
        media_type: MIME type of the file
        request: Starlette request object
        
    Returns:
        FileResponse or JSONResponse with error
    """
    try:
        if not file_path.exists():
            logger.warning(f"Static file not found: {file_path} (requested by {request.client.host})")
            return JSONResponse(
                content={"error": "File not found", "path": str(file_path.name)},
                status_code=404
            )
        
        logger.debug(f"Serving static file: {file_path.name} to {request.client.host}")
        return FileResponse(file_path, media_type=media_type)
        
    except Exception as e:
        logger.error(f"Error serving static file {file_path}: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Internal server error"},
            status_code=500
        )


def _create_static_endpoint(relative_path: str, media_type: str) -> Callable:
    """Create a static file endpoint handler.
    
    Args:
        relative_path: Relative path to the file from static directory
        media_type: MIME type of the file
        
    Returns:
        Async endpoint function
    """
    async def endpoint(request: Request, static_dir: Optional[Path] = None) -> Response:
        file_path = static_dir / relative_path
        return _serve_static_file(file_path, media_type, request)
    
    return endpoint


# Create all static file endpoints using the factory
docs_endpoint = _create_static_endpoint("docs.html", MEDIA_TYPES[".html"])
docs_endpoint.__doc__ = "Serve the documentation interface."

agent_page_endpoint = _create_static_endpoint("agent.html", MEDIA_TYPES[".html"])
agent_page_endpoint.__doc__ = "Serve the agent information page."

chat_page_endpoint = _create_static_endpoint("chat.html", MEDIA_TYPES[".html"])
chat_page_endpoint.__doc__ = "Serve the chat interface page."

storage_page_endpoint = _create_static_endpoint("storage.html", MEDIA_TYPES[".html"])
storage_page_endpoint.__doc__ = "Serve the storage management page."

common_js_endpoint = _create_static_endpoint("common.js", MEDIA_TYPES[".js"])
common_js_endpoint.__doc__ = "Serve the common JavaScript file."

common_css_endpoint = _create_static_endpoint("common.css", MEDIA_TYPES[".css"])
common_css_endpoint.__doc__ = "Serve the common CSS file."

layout_js_endpoint = _create_static_endpoint("components/layout.js", MEDIA_TYPES[".js"])
layout_js_endpoint.__doc__ = "Serve the layout JavaScript file."

header_component_endpoint = _create_static_endpoint("components/header.html", MEDIA_TYPES[".html"])
header_component_endpoint.__doc__ = "Serve the header component."

footer_component_endpoint = _create_static_endpoint("components/footer.html", MEDIA_TYPES[".html"])
footer_component_endpoint.__doc__ = "Serve the footer component."
