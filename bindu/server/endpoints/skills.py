"""Skills endpoints for detailed skill documentation and discovery.

These endpoints provide rich skill metadata for orchestrators to make
intelligent agent selection and routing decisions.
"""

from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import InternalError, SkillNotFoundError
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from bindu.server.applications import BinduApplication

logger = get_logger("bindu.server.endpoints.skills")


async def skills_list_endpoint(app: "BinduApplication", request: Request) -> Response:
    """List all skills available on this agent.

    Returns a summary of all skills with basic metadata for discovery.

    GET /agent/skills

    Response:
    {
        "skills": [
            {
                "id": "skill-id",
                "name": "skill-name",
                "description": "...",
                "version": "1.0.0",
                "tags": ["tag1", "tag2"]
            }
        ]
    }
    """
    client_ip = get_client_ip(request)

    try:
        logger.debug(f"Serving skills list to {client_ip}")

        # Get skills from manifest
        skills = app.manifest.skills or []

        # Build summary response
        skills_summary = []
        for skill in skills:
            skill_summary = {
                "id": skill.get("id"),
                "name": skill.get("name"),
                "description": skill.get("description"),
                "version": skill.get("version", "unknown"),
                "tags": skill.get("tags", []),
                "input_modes": skill.get("input_modes", []),
                "output_modes": skill.get("output_modes", []),
            }

            # Add optional fields if present
            if "examples" in skill:
                skill_summary["examples"] = skill["examples"]

            if "documentation_path" in skill:
                skill_summary["documentation_path"] = skill["documentation_path"]

            skills_summary.append(skill_summary)

        response_data = {"skills": skills_summary, "total": len(skills_summary)}

        resp = JSONResponse(content=response_data)
        if x402_is_requested(request):
            resp = x402_add_header(resp)
        return resp

    except Exception as e:
        logger.error(f"Error serving skills list to {client_ip}: {e}", exc_info=True)
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), status=500)


async def skill_detail_endpoint(app: "BinduApplication", request: Request) -> Response:
    """Get detailed information about a specific skill.

    Returns full skill metadata including documentation, capabilities,
    requirements, and performance characteristics.

    GET /agent/skills/{skill_id}

    Response:
    {
        "id": "skill-id",
        "name": "skill-name",
        "description": "...",
        "version": "1.0.0",
        "tags": ["tag1", "tag2"],
        "examples": ["example1", "example2"],
        "input_modes": ["text/plain"],
        "output_modes": ["application/json"],
        "documentation_path": "path/to/SKILL.md",
        "capabilities_detail": {...},
        "requirements": {...},
        "performance": {...},
        "allowed_tools": ["Read", "Write"]
    }
    """
    client_ip = get_client_ip(request)

    # Extract skill_id from path
    path_parts = request.url.path.split("/")
    if len(path_parts) < 4:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Skill ID not provided", status=404)

    skill_id = path_parts[-1]

    try:
        logger.debug(f"Serving skill detail for '{skill_id}' to {client_ip}")

        # Find skill in manifest
        skills = app.manifest.skills or []
        skill = None

        for s in skills:
            if s.get("id") == skill_id or s.get("name") == skill_id:
                skill = s
                break

        if not skill:
            logger.warning(f"Skill not found: {skill_id}")
            code, message = extract_error_fields(SkillNotFoundError)
            return jsonrpc_error(code, f"Skill not found: {skill_id}", status=404)

        # Return full skill data (excluding documentation_content for size)
        skill_detail = dict(skill)

        # Remove documentation_content from response (too large)
        # Clients should use /agent/skills/{skill_id}/documentation for that
        if "documentation_content" in skill_detail:
            skill_detail["has_documentation"] = True
            del skill_detail["documentation_content"]
        else:
            skill_detail["has_documentation"] = False

        resp = JSONResponse(content=skill_detail)
        if x402_is_requested(request):
            resp = x402_add_header(resp)
        return resp

    except Exception as e:
        logger.error(f"Error serving skill detail to {client_ip}: {e}", exc_info=True)
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), status=500)


async def skill_documentation_endpoint(
    app: "BinduApplication", request: Request
) -> Response:
    """Get the full skill.yaml documentation for a specific skill.

    Returns the complete YAML documentation that orchestrators can use
    to understand when and how to use this skill.

    GET /agent/skills/{skill_id}/documentation

    Response (application/yaml):
    ```yaml
    id: skill-id
    name: skill-name
    description: ...
    documentation:
      overview: ...
    ```
    """
    client_ip = get_client_ip(request)

    # Extract skill_id from path
    path_parts = request.url.path.split("/")
    if len(path_parts) < 5:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Skill ID not provided", status=404)

    skill_id = path_parts[-2]  # Second to last because last is "documentation"

    try:
        logger.debug(f"Serving skill documentation for '{skill_id}' to {client_ip}")

        # Find skill in manifest
        skills = app.manifest.skills or []
        skill = None

        for s in skills:
            if s.get("id") == skill_id or s.get("name") == skill_id:
                skill = s
                break

        if not skill:
            logger.warning(f"Skill not found: {skill_id}")
            code, message = extract_error_fields(SkillNotFoundError)
            return jsonrpc_error(code, f"Skill not found: {skill_id}", status=404)

        # Get documentation content
        documentation = skill.get("documentation_content")

        if not documentation:
            logger.warning(f"No documentation available for skill: {skill_id}")
            code, message = extract_error_fields(SkillNotFoundError)
            return jsonrpc_error(
                code, f"No documentation available for skill: {skill_id}", status=404
            )

        # Return as YAML
        resp = Response(content=documentation, media_type="application/yaml")
        if x402_is_requested(request):
            resp = x402_add_header(resp)
        return resp

    except Exception as e:
        logger.error(
            f"Error serving skill documentation to {client_ip}: {e}", exc_info=True
        )
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), status=500)
