"""Skill utilities for skill lookup and management."""

from typing import Any

from bindu.common.protocol.types import Skill


def find_skill_by_id(
    skills: list[Skill] | list[dict[str, Any]], skill_id: str
) -> Skill | dict[str, Any] | None:
    """Find skill by id or name.

    Args:
        skills: List of skill dictionaries or Skill TypedDicts
        skill_id: Skill ID or name to search for

    Returns:
        Skill dictionary if found, None otherwise
    """
    return next(
        (s for s in skills if s.get("id") == skill_id or s.get("name") == skill_id),
        None,
    )
