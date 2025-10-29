"""Agent card utilities for W3C-compliant agent discovery."""

from __future__ import annotations

from time import time
from uuid import UUID

from bindu.common.protocol.types import AgentCard


def create_agent_card(app: BinduApplication) -> AgentCard:
    """Create agent card from application manifest.

    Args:
        app: BinduApplication instance

    Returns:
        AgentCard instance

    Note:
        Excludes skill documentation_content from agent card to reduce payload size.
        Full documentation is available via /agent/skills/{skill_id}/documentation
    """
    # Minimize skills to just id, name, and documentation_path (URL) - full details via dedicated endpoint
    minimal_skills = []
    for skill in app.manifest.skills:
        minimal_skills.append(
            {
                "id": skill["id"],
                "name": skill["name"],
                "documentation_path": f"{app.url}/agent/skills/{skill['id']}",
            }
        )

    # Ensure id is UUID type (convert from string if needed)
    agent_id = (
        app.manifest.id if isinstance(app.manifest.id, UUID) else UUID(app.manifest.id)
    )

    return AgentCard(
        id=agent_id,
        name=app.manifest.name,
        description=app.manifest.description or "An AI agent exposed as an A2A agent.",
        url=app.url,
        version=app.version,
        protocol_version="0.2.5",
        skills=minimal_skills,
        capabilities=app.manifest.capabilities,
        kind=app.manifest.kind,
        num_history_sessions=app.manifest.num_history_sessions,
        extra_data=app.manifest.extra_data
        or {"created": int(time()), "server_info": "bindu Agent Server"},
        debug_mode=app.manifest.debug_mode,
        debug_level=app.manifest.debug_level,
        monitoring=app.manifest.monitoring,
        telemetry=app.manifest.telemetry,
        agent_trust=app.manifest.agent_trust,
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
    )
