"""Static file serving endpoints."""

from pathlib import Path
from typing import Callable, Optional

from starlette.requests import Request
from starlette.responses import FileResponse, Response

from bindu.common.protocol.types import InternalError, TaskNotFoundError
from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, jsonrpc_error

logger = get_logger("bindu.server.endpoints.static_files")


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
            code, message = extract_error_fields(TaskNotFoundError)
            return jsonrpc_error(code, message, f"File not found: {file_path.name}", status=404)
        
        logger.debug(f"Serving static file: {file_path.name} to {request.client.host}")
        return FileResponse(file_path, media_type=media_type)
        
    except Exception as e:
        logger.error(f"Error serving static file {file_path}: {e}", exc_info=True)
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), status=500)


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
# HTML Pages
agent_page_endpoint = _create_static_endpoint("agent.html", app_settings.network.media_types[".html"])
agent_page_endpoint.__doc__ = "Serve the agent information page."

chat_page_endpoint = _create_static_endpoint("chat.html", app_settings.network.media_types[".html"])
chat_page_endpoint.__doc__ = "Serve the chat interface page."

storage_page_endpoint = _create_static_endpoint("storage.html", app_settings.network.media_types[".html"])
storage_page_endpoint.__doc__ = "Serve the storage management page."

# JavaScript Files
common_js_endpoint = _create_static_endpoint("js/common.js", app_settings.network.media_types[".js"])
common_js_endpoint.__doc__ = "Serve the common JavaScript file."

api_js_endpoint = _create_static_endpoint("js/api.js", app_settings.network.media_types[".js"])
api_js_endpoint.__doc__ = "Serve the API JavaScript file."

agent_js_endpoint = _create_static_endpoint("js/agent.js", app_settings.network.media_types[".js"])
agent_js_endpoint.__doc__ = "Serve the agent page JavaScript file."

chat_js_endpoint = _create_static_endpoint("js/chat.js", app_settings.network.media_types[".js"])
chat_js_endpoint.__doc__ = "Serve the chat JavaScript file."

storage_js_endpoint = _create_static_endpoint("js/storage.js", app_settings.network.media_types[".js"])
storage_js_endpoint.__doc__ = "Serve the storage JavaScript file."

head_loader_js_endpoint = _create_static_endpoint("js/head-loader.js", app_settings.network.media_types[".js"])
head_loader_js_endpoint.__doc__ = "Serve the head loader JavaScript file."

# CSS Files
custom_css_endpoint = _create_static_endpoint("css/custom.css", app_settings.network.media_types[".css"])
custom_css_endpoint.__doc__ = "Serve the custom CSS file."
