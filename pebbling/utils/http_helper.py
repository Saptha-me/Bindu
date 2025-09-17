#
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""HTTP utility functions for Pebbling services."""

import os
from typing import Any, Dict, Optional, Union

import httpx
from pydantic import SecretStr


async def make_api_request(
    url: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    api_key: Optional[SecretStr] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Make an API request and handle common response patterns.

    Args:
        url: The API endpoint URL
        method: HTTP method (GET, POST, etc.)
        payload: JSON payload for the request
        api_key: Optional API key for authentication
        headers: Optional additional headers
        timeout: Request timeout in seconds

    Returns:
        Dictionary with success flag and data or error message
    """
    # Prepare headers
    request_headers = {"accept": "application/json", "Content-Type": "application/json"}

    # Add custom headers
    if headers:
        request_headers.update(headers)

    # Add API key if provided
    if api_key:
        request_headers["X-API-Key"] = api_key.get_secret_value()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=request_headers)
            elif method.upper() == "POST":
                response = await client.post(url, headers=request_headers, json=payload)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=request_headers, json=payload)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=request_headers)
            else:
                return {"success": False, "error": f"Unsupported HTTP method: {method}"}

            # Handle response
            if response.status_code in (200, 201):
                return {"success": True, "data": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code,
                }

    except httpx.TimeoutException:
        return {"success": False, "error": f"Request timed out after {timeout} seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def make_multipart_request(
    url: str,
    files: Dict[str, Union[str, tuple]],
    form_data: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Make a multipart form data request (useful for file uploads).

    Args:
        url: The API endpoint URL
        files: Dictionary of files to upload. Format:
               - {"field_name": "file_path"} or
               - {"field_name": ("filename", content, "content_type")}
        form_data: Additional form fields
        headers: Optional additional headers (don't include Content-Type for multipart)
        timeout: Request timeout in seconds

    Returns:
        Dictionary with success flag and data or error message
    """
    # Prepare headers (don't set Content-Type, httpx will set it for multipart)
    request_headers = {"accept": "application/json"}

    # Add custom headers
    if headers:
        request_headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Prepare files for upload
            upload_files = {}

            for field_name, file_info in files.items():
                if isinstance(file_info, str):
                    # Simple file path
                    if not os.path.exists(file_info):
                        return {"success": False, "error": f"File not found: {file_info}"}

                    with open(file_info, "rb") as f:
                        filename = os.path.basename(file_info)
                        upload_files[field_name] = (filename, f.read(), "application/octet-stream")
                else:
                    # Tuple format (filename, content, content_type)
                    upload_files[field_name] = file_info

            # Prepare form data
            data = form_data or {}

            response = await client.post(url, files=upload_files, data=data, headers=request_headers)

            # Handle response
            if response.status_code in (200, 201):
                try:
                    return {"success": True, "data": response.json()}
                except:
                    # If response is not JSON, return text
                    return {"success": True, "data": {"message": response.text}}
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code,
                }

    except httpx.TimeoutException:
        return {"success": False, "error": f"Request timed out after {timeout} seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}
