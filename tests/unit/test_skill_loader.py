"""Unit tests for skill loader."""

import tempfile
from pathlib import Path

import pytest
import yaml

from bindu.utils.skill_loader import load_skill_from_directory, load_skills


class TestLoadSkillFromDirectory:
    """Tests for load_skill_from_directory function."""

    def test_load_skill_with_minimal_yaml(self, tmp_path):
        """Test loading a skill with minimal required fields."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()

        skill_yaml = {
            "name": "Test Skill",
            "description": "A test skill for unit testing",
        }

        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["name"] == "Test Skill"
        assert skill["description"] == "A test skill for unit testing"
        assert skill["id"] == "Test Skill"  # Defaults to name when id not provided
        assert skill["tags"] == []
        assert skill["input_modes"] == ["text/plain"]
        assert skill["output_modes"] == ["text/plain"]
        assert "documentation_content" in skill
        assert "documentation_path" in skill

    def test_load_skill_with_all_fields(self, tmp_path):
        """Test loading a skill with all optional fields."""
        skill_dir = tmp_path / "full_skill"
        skill_dir.mkdir()

        skill_yaml = {
            "id": "custom-skill-id",
            "name": "Full Skill",
            "description": "A complete skill",
            "version": "2.0.0",
            "tags": ["test", "demo", "full"],
            "input_modes": ["text/plain", "application/json"],
            "output_modes": ["application/json", "text/html"],
            "examples": ["example 1", "example 2", "example 3"],
            "capabilities_detail": {
                "feature_a": {"enabled": True, "level": "advanced"},
                "feature_b": {"enabled": False},
            },
            "requirements": {
                "packages": ["numpy", "pandas"],
                "system": ["ffmpeg"],
                "min_memory_mb": 1024,
            },
            "performance": {
                "avg_processing_time_ms": 500,
                "max_file_size_mb": 100,
                "concurrent_requests": 10,
            },
            "allowed_tools": ["Read", "Write", "Execute", "Network"],
        }

        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert skill["id"] == "custom-skill-id"
        assert skill["name"] == "Full Skill"
        assert skill["version"] == "2.0.0"
        assert skill["tags"] == ["test", "demo", "full"]
        assert skill["input_modes"] == ["text/plain", "application/json"]
        assert skill["output_modes"] == ["application/json", "text/html"]
        assert skill["examples"] == ["example 1", "example 2", "example 3"]
        assert skill["capabilities_detail"]["feature_a"]["enabled"] is True
        assert skill["requirements"]["min_memory_mb"] == 1024
        assert skill["performance"]["avg_processing_time_ms"] == 500
        assert skill["allowed_tools"] == ["Read", "Write", "Execute", "Network"]

    def test_load_skill_with_string_path(self, tmp_path):
        """Test loading a skill when path is provided as string."""
        skill_dir = tmp_path / "string_path_skill"
        skill_dir.mkdir()

        skill_yaml = {"name": "String Path Skill", "description": "Test"}
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        # Pass path as string instead of Path object
        skill = load_skill_from_directory(str(skill_dir), tmp_path)

        assert skill["name"] == "String Path Skill"

    def test_load_skill_with_relative_path(self, tmp_path):
        """Test loading a skill with relative path."""
        skill_dir = tmp_path / "relative_skill"
        skill_dir.mkdir()

        skill_yaml = {"name": "Relative Skill", "description": "Test"}
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        # Use relative path
        skill = load_skill_from_directory("relative_skill", tmp_path)

        assert skill["name"] == "Relative Skill"

    def test_load_skill_with_absolute_path(self, tmp_path):
        """Test loading a skill with absolute path."""
        skill_dir = tmp_path / "absolute_skill"
        skill_dir.mkdir()

        skill_yaml = {"name": "Absolute Skill", "description": "Test"}
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        # Use absolute path
        skill = load_skill_from_directory(skill_dir.resolve(), tmp_path)

        assert skill["name"] == "Absolute Skill"

    def test_load_skill_directory_not_found(self, tmp_path):
        """Test error when skill directory doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Skill directory not found"):
            load_skill_from_directory(tmp_path / "nonexistent", tmp_path)

    def test_load_skill_yaml_not_found(self, tmp_path):
        """Test error when skill.yaml doesn't exist in directory."""
        skill_dir = tmp_path / "no_yaml_skill"
        skill_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="skill.yaml not found"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_invalid_yaml(self, tmp_path):
        """Test error when skill.yaml contains invalid YAML."""
        skill_dir = tmp_path / "invalid_yaml_skill"
        skill_dir.mkdir()

        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_skill_from_directory(skill_dir, tmp_path)

    def test_load_skill_documentation_path_relative(self, tmp_path):
        """Test that documentation_path is relative when possible."""
        # Create nested structure
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "test_skill"
        skill_dir.mkdir()

        skill_yaml = {"name": "Test Skill", "description": "Test"}
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        skill = load_skill_from_directory(skill_dir, config_dir)

        # Should have relative path from config_dir.parent
        assert "documentation_path" in skill
        assert "skill.yaml" in skill["documentation_path"]

    def test_load_skill_documentation_path_absolute_fallback(self, tmp_path):
        """Test that documentation_path falls back to absolute when relative fails."""
        # Create skill outside of caller_dir hierarchy
        with tempfile.TemporaryDirectory() as other_tmp:
            skill_dir = Path(other_tmp) / "external_skill"
            skill_dir.mkdir()

            skill_yaml = {"name": "External Skill", "description": "Test"}
            yaml_path = skill_dir / "skill.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(skill_yaml, f)

            skill = load_skill_from_directory(skill_dir, tmp_path)

            # Should use absolute path when relative fails
            assert "documentation_path" in skill
            assert skill_dir.name in skill["documentation_path"]

    def test_load_skill_documentation_content(self, tmp_path):
        """Test that documentation_content contains the full YAML."""
        skill_dir = tmp_path / "doc_skill"
        skill_dir.mkdir()

        skill_yaml = {
            "name": "Doc Skill",
            "description": "Test documentation",
            "version": "1.0.0",
        }
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        skill = load_skill_from_directory(skill_dir, tmp_path)

        assert "documentation_content" in skill
        assert "Doc Skill" in skill["documentation_content"]
        assert "Test documentation" in skill["documentation_content"]
        assert "1.0.0" in skill["documentation_content"]


class TestLoadSkills:
    """Tests for load_skills function."""

    def test_load_skills_empty_list(self, tmp_path):
        """Test loading with empty skills list."""
        skills = load_skills([], tmp_path)
        assert skills == []

    def test_load_skills_single_skill(self, tmp_path):
        """Test loading a single skill."""
        skill_dir = tmp_path / "skill1"
        skill_dir.mkdir()

        skill_yaml = {"name": "Skill 1", "description": "First skill"}
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        skills = load_skills(["skill1"], tmp_path)

        assert len(skills) == 1
        assert skills[0]["name"] == "Skill 1"

    def test_load_skills_multiple_skills(self, tmp_path):
        """Test loading multiple skills."""
        # Create first skill
        skill1_dir = tmp_path / "skill1"
        skill1_dir.mkdir()
        with open(skill1_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Skill 1", "description": "First"}, f)

        # Create second skill
        skill2_dir = tmp_path / "skill2"
        skill2_dir.mkdir()
        with open(skill2_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Skill 2", "description": "Second"}, f)

        # Create third skill
        skill3_dir = tmp_path / "skill3"
        skill3_dir.mkdir()
        with open(skill3_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Skill 3", "description": "Third"}, f)

        skills = load_skills(["skill1", "skill2", "skill3"], tmp_path)

        assert len(skills) == 3
        assert skills[0]["name"] == "Skill 1"
        assert skills[1]["name"] == "Skill 2"
        assert skills[2]["name"] == "Skill 3"

    def test_load_skills_with_absolute_paths(self, tmp_path):
        """Test loading skills with absolute paths."""
        skill_dir = tmp_path / "abs_skill"
        skill_dir.mkdir()

        skill_yaml = {"name": "Absolute Skill", "description": "Test"}
        yaml_path = skill_dir / "skill.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(skill_yaml, f)

        skills = load_skills([str(skill_dir.resolve())], tmp_path)

        assert len(skills) == 1
        assert skills[0]["name"] == "Absolute Skill"

    def test_load_skills_invalid_config_dict(self, tmp_path):
        """Test that dict configs are logged as warnings but don't crash."""
        # Currently the function logs a warning for dict configs
        # but doesn't actually load them (inline skills not implemented)
        skills_config = [{"name": "Inline Skill", "description": "Not supported"}]

        skills = load_skills(skills_config, tmp_path)

        # Should return empty list since dict configs are not supported
        assert len(skills) == 0

    def test_load_skills_error_propagates(self, tmp_path):
        """Test that errors during loading are propagated."""
        # Try to load non-existent skill
        with pytest.raises(FileNotFoundError):
            load_skills(["nonexistent_skill"], tmp_path)

    def test_load_skills_mixed_valid_paths(self, tmp_path):
        """Test loading skills with mix of relative and absolute paths."""
        # Create relative skill
        rel_skill_dir = tmp_path / "rel_skill"
        rel_skill_dir.mkdir()
        with open(rel_skill_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Relative Skill", "description": "Test"}, f)

        # Create absolute skill
        abs_skill_dir = tmp_path / "abs_skill"
        abs_skill_dir.mkdir()
        with open(abs_skill_dir / "skill.yaml", "w") as f:
            yaml.dump({"name": "Absolute Skill", "description": "Test"}, f)

        skills = load_skills(
            ["rel_skill", str(abs_skill_dir.resolve())],
            tmp_path,
        )

        assert len(skills) == 2
        assert skills[0]["name"] == "Relative Skill"
        assert skills[1]["name"] == "Absolute Skill"

    def test_load_skills_preserves_all_metadata(self, tmp_path):
        """Test that all skill metadata is preserved through load_skills."""
        skill_dir = tmp_path / "full_skill"
        skill_dir.mkdir()

        skill_yaml = {
            "id": "full-skill",
            "name": "Full Skill",
            "description": "Complete skill",
            "version": "3.0.0",
            "tags": ["complete", "test"],
            "examples": ["ex1", "ex2"],
            "capabilities_detail": {"cap": "value"},
            "requirements": {"req": "value"},
            "performance": {"perf": "value"},
            "allowed_tools": ["Tool1", "Tool2"],
        }

        with open(skill_dir / "skill.yaml", "w") as f:
            yaml.dump(skill_yaml, f)

        skills = load_skills(["full_skill"], tmp_path)

        assert len(skills) == 1
        skill = skills[0]
        assert skill["id"] == "full-skill"
        assert skill["version"] == "3.0.0"
        assert skill["tags"] == ["complete", "test"]
        assert skill["examples"] == ["ex1", "ex2"]
        assert "capabilities_detail" in skill
        assert "requirements" in skill
        assert "performance" in skill
        assert "allowed_tools" in skill
