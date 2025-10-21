"""Skill loader for Claude-style skill bundles.

This module handles loading skills from filesystem directories containing
SKILL.md files and manifest.json files for rich agent advertisement.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Union

from bindu.common.protocol.types import Skill
from bindu.utils.logging import get_logger

logger = get_logger("bindu.penguin.skill_loader")


def _parse_skill_frontmatter(content: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from SKILL.md file.
    
    Args:
        content: Full content of SKILL.md file
        
    Returns:
        Dictionary of frontmatter fields
    """
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(frontmatter_pattern, content, re.DOTALL)
    
    if not match:
        return {}
    
    frontmatter_text = match.group(1)
    frontmatter = {}
    
    # Simple YAML parsing for key: value pairs
    for line in frontmatter_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Handle lists (e.g., allowed-tools: Read, Write, Execute)
            if ',' in value:
                value = [v.strip() for v in value.split(',')]
            
            # Convert kebab-case to snake_case
            key = key.replace('-', '_')
            frontmatter[key] = value
    
    return frontmatter


def load_skill_from_directory(skill_path: Union[str, Path], caller_dir: Path) -> Skill:
    """Load a skill from a directory containing SKILL.md and manifest.json.
    
    Args:
        skill_path: Path to skill directory (relative or absolute)
        caller_dir: Directory of the calling config file for resolving relative paths
        
    Returns:
        Skill dictionary with all metadata and documentation
        
    Raises:
        FileNotFoundError: If skill directory or required files don't exist
        ValueError: If skill files are malformed
    """
    # Resolve path
    if isinstance(skill_path, str):
        skill_path = Path(skill_path)
    
    if not skill_path.is_absolute():
        skill_path = caller_dir / skill_path
    
    skill_path = skill_path.resolve()
    
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_path}")
    
    # Load manifest.json
    manifest_path = skill_path / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.json not found in skill directory: {skill_path}")
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Load SKILL.md
    skill_md_path = skill_path / "SKILL.md"
    documentation_content = None
    
    if skill_md_path.exists():
        with open(skill_md_path, 'r', encoding='utf-8') as f:
            documentation_content = f.read()
        
        # Parse frontmatter for additional metadata
        frontmatter = _parse_skill_frontmatter(documentation_content)
        
        # Merge frontmatter with manifest (manifest takes precedence)
        for key, value in frontmatter.items():
            if key not in manifest:
                manifest[key] = value
    
    # Build Skill object
    skill: Skill = {
        "id": manifest.get("id", manifest["name"]),
        "name": manifest["name"],
        "description": manifest["description"],
        "tags": manifest.get("tags", []),
        "input_modes": manifest.get("input_modes", ["text/plain"]),
        "output_modes": manifest.get("output_modes", ["text/plain"]),
    }
    
    # Add optional fields
    if "examples" in manifest:
        skill["examples"] = manifest["examples"]
    
    if "version" in manifest:
        skill["version"] = manifest["version"]
    
    if "documentation_path" in manifest:
        skill["documentation_path"] = manifest["documentation_path"]
    elif skill_md_path.exists():
        # Store relative path from project root
        skill["documentation_path"] = str(skill_md_path.relative_to(caller_dir.parent))
    
    if documentation_content:
        skill["documentation_content"] = documentation_content
    
    if "capabilities_detail" in manifest:
        skill["capabilities_detail"] = manifest["capabilities_detail"]
    
    if "requirements" in manifest:
        skill["requirements"] = manifest["requirements"]
    
    if "performance" in manifest:
        skill["performance"] = manifest["performance"]
    
    if "allowed_tools" in manifest:
        skill["allowed_tools"] = manifest["allowed_tools"]
    
    logger.info(f"Loaded skill: {skill['name']} v{skill.get('version', 'unknown')} from {skill_path}")
    
    return skill


def load_skill_from_inline(skill_data: Dict[str, Any]) -> Skill:
    """Load a skill from inline configuration (legacy format).
    
    Args:
        skill_data: Dictionary containing skill metadata
        
    Returns:
        Skill dictionary
    """
    # Generate ID if not provided
    skill_id = skill_data.get("id", f"{skill_data['name']}-v{skill_data.get('version', '1.0.0')}")
    
    skill: Skill = {
        "id": skill_id,
        "name": skill_data["name"],
        "description": skill_data["description"],
        "tags": skill_data.get("tags", []),
        "input_modes": skill_data.get("input_modes", ["text/plain"]),
        "output_modes": skill_data.get("output_modes", ["text/plain"]),
    }
    
    # Add optional fields
    if "examples" in skill_data:
        skill["examples"] = skill_data["examples"]
    
    if "version" in skill_data:
        skill["version"] = skill_data["version"]
    
    if "capabilities_detail" in skill_data:
        skill["capabilities_detail"] = skill_data["capabilities_detail"]
    
    if "requirements" in skill_data:
        skill["requirements"] = skill_data["requirements"]
    
    if "performance" in skill_data:
        skill["performance"] = skill_data["performance"]
    
    if "allowed_tools" in skill_data:
        skill["allowed_tools"] = skill_data["allowed_tools"]
    
    logger.debug(f"Loaded inline skill: {skill['name']}")
    
    return skill


def load_skills(
    skills_config: List[Union[str, Dict[str, Any]]], 
    caller_dir: Path
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
                # File-based skill
                skill = load_skill_from_directory(skill_item, caller_dir)
                skills.append(skill)
            elif isinstance(skill_item, dict):
                # Inline skill
                skill = load_skill_from_inline(skill_item)
                skills.append(skill)
            else:
                logger.warning(f"Invalid skill configuration: {skill_item}")
        except Exception as e:
            logger.error(f"Failed to load skill {skill_item}: {e}")
            raise
    
    logger.info(f"Loaded {len(skills)} skill(s)")
    return skills
