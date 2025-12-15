"""Skill loader for Claude-style skill bundles.

This module handles loading skills from filesystem directories containing
skill.yaml files for rich agent advertisement.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Union, cast

from bindu.common.protocol.types import Skill
from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.skill_loader")


def load_skill_from_directory(skill_path: Union[str, Path], caller_dir: Path) -> Skill:
    """Load a skill from a directory containing skill.yaml.

    Args:
        skill_path: Path to skill directory (relative or absolute)
        caller_dir: Directory of the calling config file for resolving relative paths

    Returns:
        Skill dictionary with all metadata and documentation

    Raises:
        FileNotFoundError: If skill directory or skill.yaml doesn't exist
        ValueError: If skill.yaml is malformed
    """
    # Resolve path
    if isinstance(skill_path, str):
        skill_path = Path(skill_path)

    if not skill_path.is_absolute():
        skill_path = caller_dir / skill_path

    skill_path = skill_path.resolve()

    if not skill_path.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_path}")

    # Load skill.yaml
    yaml_path = skill_path / "skill.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"skill.yaml not found in skill directory: {skill_path}"
        )

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            skill_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {yaml_path}: {e}")

    # Build Skill object from YAML data - start with required fields
    skill: Dict[str, Any] = {
        "id": skill_data.get("id", skill_data["name"]),
        "name": skill_data["name"],
        "description": skill_data["description"],
        "tags": skill_data.get("tags", []),
        "input_modes": skill_data.get("input_modes", ["text/plain"]),
        "output_modes": skill_data.get("output_modes", ["text/plain"]),
    }

    # Add all optional fields from YAML if present
    optional_fields = [
        "version",
        "author",
        "examples",
        "capabilities_detail",
        "requirements",
        "performance",
        "allowed_tools",
        "documentation",
        "assessment",
    ]

    for field in optional_fields:
        if field in skill_data:
            skill[field] = skill_data[field]

    # Store relative path to YAML file
    try:
        skill["documentation_path"] = str(yaml_path.relative_to(caller_dir.parent))
    except ValueError:
        # If relative path fails, use absolute
        skill["documentation_path"] = str(yaml_path)

    # Store raw YAML content as documentation
    with open(yaml_path, "r", encoding="utf-8") as f:
        skill["documentation_content"] = f.read()

    logger.info(
        f"Loaded skill: {skill['name']} v{skill.get('version', 'unknown')} from {skill_path}"
    )

    return cast(Skill, skill)


def load_skills(
    skills_config: List[Union[str, Dict[str, Any]]], caller_dir: Path
) -> List[Skill]:
    """Load skills from configuration.

    Supports both:
    1. File-based skills: ["path/to/skill/dir"]
    2. Inline skills: [{"name": "...", "description": "..."}]

    Args:
        skills_config: List of skill paths or inline skill dictionaries
        caller_dir: Directory of the calling config file

    Returns:
        List of loaded Skill objects
    """
    skills: List[Skill] = []

    for skill_item in skills_config:
        try:
            if isinstance(skill_item, str):
                skill = load_skill_from_directory(skill_item, caller_dir)
                skills.append(skill)
            else:
                logger.warning(f"Invalid skill configuration: {skill_item}")
        except Exception as e:
            logger.error(f"Failed to load skill {skill_item}: {e}")
            raise

    logger.info(f"Loaded {len(skills)} skill(s)")
    return skills
