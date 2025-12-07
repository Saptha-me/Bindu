"""Skills endpoints for detailed skill documentation and discovery.

These endpoints provide rich skill metadata for orchestrators to make
intelligent agent selection and routing decisions.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import SkillNotFoundError
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)
from bindu.server.applications import BinduApplication
from bindu.utils.request_utils import handle_endpoint_errors
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error
from bindu.utils.skill_utils import find_skill_by_id

logger = get_logger("bindu.server.endpoints.skills")


@handle_endpoint_errors("skills list")
async def skills_list_endpoint(app: BinduApplication, request: Request) -> Response:
    """List all skills available on this agent.

    Returns a summary of all skills with basic metadata for discovery.
    """
    client_ip = get_client_ip(request)
    logger.debug(f"Serving skills list to {client_ip}")

    # Ensure manifest exists
    if app.manifest is None:
        return JSONResponse(
            content={"error": "Agent manifest not configured"}, status_code=500
        )

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


@handle_endpoint_errors("skill detail")
async def skill_detail_endpoint(app: BinduApplication, request: Request) -> Response:
    """Get detailed information about a specific skill.

    Returns full skill metadata including documentation, capabilities,
    requirements, and performance characteristics.
    """
    client_ip = get_client_ip(request)
    skill_id = request.path_params.get("skill_id")

    if not skill_id:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Skill ID not provided", status=404)

    logger.debug(f"Serving skill detail for '{skill_id}' to {client_ip}")

    # Ensure manifest exists
    if app.manifest is None:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Agent manifest not configured", status=500)

    # Find skill in manifest
    skills = app.manifest.skills or []
    skill = find_skill_by_id(skills, skill_id)

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


@handle_endpoint_errors("skill documentation")
async def skill_documentation_endpoint(
    app: BinduApplication, request: Request
) -> Response:
    """Get the full skill.yaml documentation for a specific skill.

    Returns the complete YAML documentation that orchestrators can use
    to understand when and how to use this skill.
    """
    client_ip = get_client_ip(request)
    skill_id = request.path_params.get("skill_id")

    if not skill_id:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Skill ID not provided", status=404)

    logger.debug(f"Serving skill documentation for '{skill_id}' to {client_ip}")

    # Ensure manifest exists
    if app.manifest is None:
        code, message = extract_error_fields(SkillNotFoundError)
        return jsonrpc_error(code, "Agent manifest not configured", status=500)

    # Find skill in manifest
    skills = app.manifest.skills or []
    skill = find_skill_by_id(skills, skill_id)

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
