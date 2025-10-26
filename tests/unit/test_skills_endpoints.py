"""Unit tests for skills endpoints."""

import json
from types import SimpleNamespace
from typing import cast

import pytest

from bindu.server.applications import BinduApplication
from bindu.server.endpoints.skills import (
    skill_detail_endpoint,
    skill_documentation_endpoint,
    skills_list_endpoint,
)
from bindu.settings import app_settings


def _make_request(
    method: str = "GET",
    path: str = "/",
    headers: dict | None = None,
) -> object:
    """Create a minimal mock request object."""
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    # Extract path params from path (e.g., /agent/skills/skill-1 -> skill_id=skill-1)
    path_params = {}
    path_parts = path.strip("/").split("/")
    if len(path_parts) >= 3 and path_parts[0] == "agent" and path_parts[1] == "skills":
        if len(path_parts) == 3:
            # /agent/skills/{skill_id}
            path_params["skill_id"] = path_parts[2]
        elif len(path_parts) == 4 and path_parts[3] == "documentation":
            # /agent/skills/{skill_id}/documentation
            path_params["skill_id"] = path_parts[2]

    # Mock request with minimal required attributes
    request = SimpleNamespace(
        url=SimpleNamespace(path=path),
        headers=headers or {},
        client=SimpleNamespace(host="127.0.0.1"),
        path_params=path_params,
    )
    # Add raw headers for x402 extension check
    request._headers = raw_headers  # type: ignore
    return request


def _make_app_with_skills(skills: list) -> object:
    """Create a minimal mock app with skills."""
    manifest = SimpleNamespace(skills=skills)
    return SimpleNamespace(manifest=manifest)


@pytest.mark.asyncio
async def test_skills_list_endpoint_empty():
    """Test skills list endpoint with no skills."""
    app = _make_app_with_skills([])
    request = _make_request(path="/agent/skills")

    response = await skills_list_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["skills"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_skills_list_endpoint_with_skills():
    """Test skills list endpoint with multiple skills."""
    skills = [
        {
            "id": "skill-1",
            "name": "Test Skill 1",
            "description": "First test skill",
            "version": "1.0.0",
            "tags": ["test", "demo"],
            "input_modes": ["text/plain"],
            "output_modes": ["application/json"],
        },
        {
            "id": "skill-2",
            "name": "Test Skill 2",
            "description": "Second test skill",
            "tags": ["test"],
            "input_modes": ["text/plain"],
            "output_modes": ["text/plain"],
            "examples": ["example 1", "example 2"],
            "documentation_path": "skills/skill2/skill.yaml",
        },
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills")

    response = await skills_list_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["total"] == 2
    assert len(data["skills"]) == 2

    # Check first skill
    skill1 = data["skills"][0]
    assert skill1["id"] == "skill-1"
    assert skill1["name"] == "Test Skill 1"
    assert skill1["version"] == "1.0.0"
    assert skill1["tags"] == ["test", "demo"]

    # Check second skill with optional fields
    skill2 = data["skills"][1]
    assert skill2["id"] == "skill-2"
    assert skill2["version"] == "unknown"  # Default when not provided
    assert skill2["examples"] == ["example 1", "example 2"]
    assert skill2["documentation_path"] == "skills/skill2/skill.yaml"


@pytest.mark.asyncio
async def test_skills_list_endpoint_with_x402_header():
    """Test skills list endpoint echoes x402 extension header."""
    app = _make_app_with_skills([])
    request = _make_request(
        path="/agent/skills",
        headers={"X-A2A-Extensions": app_settings.x402.extension_uri},
    )

    response = await skills_list_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    assert response.headers.get("X-A2A-Extensions") == app_settings.x402.extension_uri


@pytest.mark.asyncio
async def test_skill_detail_endpoint_missing_skill_id():
    """Test skill detail endpoint with missing skill ID in path."""
    app = _make_app_with_skills([])
    request = _make_request(path="/agent/skills")  # Too short path

    response = await skill_detail_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 404
    data = json.loads(response.body)
    assert data["error"]["code"] == -32030  # SkillNotFoundError code
    assert "Skill ID not provided" in data["error"]["message"]


@pytest.mark.asyncio
async def test_skill_detail_endpoint_skill_not_found():
    """Test skill detail endpoint with non-existent skill ID."""
    skills = [
        {
            "id": "skill-1",
            "name": "Test Skill",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills/nonexistent")

    response = await skill_detail_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 404
    data = json.loads(response.body)
    assert data["error"]["code"] == -32030
    assert "Skill not found: nonexistent" in data["error"]["message"]


@pytest.mark.asyncio
async def test_skill_detail_endpoint_found_by_id():
    """Test skill detail endpoint finds skill by ID."""
    skills = [
        {
            "id": "test-skill",
            "name": "Test Skill",
            "description": "A test skill",
            "version": "2.0.0",
            "tags": ["test"],
            "input_modes": ["text/plain"],
            "output_modes": ["application/json"],
            "capabilities_detail": {"feature": "enabled"},
            "requirements": {"memory": "512MB"},
            "performance": {"avg_time": 100},
            "allowed_tools": ["Read", "Write"],
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills/test-skill")

    response = await skill_detail_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["id"] == "test-skill"
    assert data["name"] == "Test Skill"
    assert data["version"] == "2.0.0"
    assert data["capabilities_detail"] == {"feature": "enabled"}
    assert data["requirements"] == {"memory": "512MB"}
    assert data["performance"] == {"avg_time": 100}
    assert data["allowed_tools"] == ["Read", "Write"]
    assert data["has_documentation"] is False


@pytest.mark.asyncio
async def test_skill_detail_endpoint_found_by_name():
    """Test skill detail endpoint finds skill by name."""
    skills = [
        {
            "id": "skill-id",
            "name": "My Skill",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills/My Skill")

    response = await skill_detail_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert data["id"] == "skill-id"
    assert data["name"] == "My Skill"


@pytest.mark.asyncio
async def test_skill_detail_endpoint_removes_documentation_content():
    """Test skill detail endpoint removes large documentation_content field."""
    skills = [
        {
            "id": "skill-1",
            "name": "Test",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
            "documentation_content": "Very long YAML content here...",
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills/skill-1")

    response = await skill_detail_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    data = json.loads(response.body)
    assert "documentation_content" not in data
    assert data["has_documentation"] is True


@pytest.mark.asyncio
async def test_skill_detail_endpoint_with_x402_header():
    """Test skill detail endpoint echoes x402 extension header."""
    skills = [
        {
            "id": "skill-1",
            "name": "Test",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(
        path="/agent/skills/skill-1",
        headers={"X-A2A-Extensions": app_settings.x402.extension_uri},
    )

    response = await skill_detail_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    assert response.headers.get("X-A2A-Extensions") == app_settings.x402.extension_uri


@pytest.mark.asyncio
async def test_skill_documentation_endpoint_missing_skill_id():
    """Test documentation endpoint with missing skill ID in path."""
    app = _make_app_with_skills([])
    request = _make_request(path="/agent/skills/doc")  # Too short

    response = await skill_documentation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 404
    data = json.loads(response.body)
    assert data["error"]["code"] == -32030


@pytest.mark.asyncio
async def test_skill_documentation_endpoint_skill_not_found():
    """Test documentation endpoint with non-existent skill."""
    app = _make_app_with_skills([])
    request = _make_request(path="/agent/skills/nonexistent/documentation")

    response = await skill_documentation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 404
    data = json.loads(response.body)
    assert "Skill not found: nonexistent" in data["error"]["message"]


@pytest.mark.asyncio
async def test_skill_documentation_endpoint_no_documentation():
    """Test documentation endpoint when skill has no documentation."""
    skills = [
        {
            "id": "skill-1",
            "name": "Test",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills/skill-1/documentation")

    response = await skill_documentation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 404
    data = json.loads(response.body)
    assert "No documentation available" in data["error"]["message"]


@pytest.mark.asyncio
async def test_skill_documentation_endpoint_success():
    """Test documentation endpoint returns YAML content."""
    yaml_content = """id: test-skill
name: Test Skill
description: A test skill
documentation:
  overview: This is a test skill
"""
    skills = [
        {
            "id": "test-skill",
            "name": "Test",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
            "documentation_content": yaml_content,
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(path="/agent/skills/test-skill/documentation")

    response = await skill_documentation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    assert response.media_type == "application/yaml"
    assert response.body.decode() == yaml_content


@pytest.mark.asyncio
async def test_skill_documentation_endpoint_with_x402_header():
    """Test documentation endpoint echoes x402 extension header."""
    skills = [
        {
            "id": "skill-1",
            "name": "Test",
            "description": "Test",
            "tags": [],
            "input_modes": [],
            "output_modes": [],
            "documentation_content": "test: yaml",
        }
    ]
    app = _make_app_with_skills(skills)
    request = _make_request(
        path="/agent/skills/skill-1/documentation",
        headers={"X-A2A-Extensions": app_settings.x402.extension_uri},
    )

    response = await skill_documentation_endpoint(cast(BinduApplication, app), request)  # type: ignore

    assert response.status_code == 200
    assert response.headers.get("X-A2A-Extensions") == app_settings.x402.extension_uri
