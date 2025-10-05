"""Settings configuration for the Pebbling agent system.

This module defines the configuration settings for the application using pydantic models.
"""

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectSettings(BaseSettings):
    """
    Project-level configuration settings.

    Contains general application settings like environment, debug mode,
    and project metadata.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PROJECT__",
        extra="allow",
    )

    environment: str = Field(default="development", env="ENVIRONMENT")
    name: str = "Pebbling Agent"
    version: str = "0.1.0"

    @computed_field
    @property
    def debug(self) -> bool:
        """Compute debug mode based on environment."""
        return self.environment != "production"

    @computed_field
    @property
    def testing(self) -> bool:
        """Compute testing mode based on environment."""
        return self.environment == "testing"


class UISettings(BaseSettings):
    """Consolidated UI, branding, links, and footer configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="UI__",
        extra="allow",
    )

    # Branding settings
    logo_emoji: str = "🐧"
    default_agent_name: str = "Pebbling Agent"
    protocol_name: str = "Pebbling Protocol"
    protocol_url: str = "https://pebbling.ai"
    powered_by_text: str = "Fueled by"

    # Status and interface text
    status_online_text: str = "Online"
    status_active_text: str = "Active"
    agent_subtitle_default: str = "Agent Information & Capabilities"

    # External links
    docs_url: str = "https://docs.pebbling.ai"
    docs_text: str = "Documentation"
    github_url: str = "https://github.com/Pebbling-ai/pebble"
    github_text: str = "GitHub"
    github_issues_url: str = "https://github.com/Pebbling-ai/pebble/issues"
    github_issues_text: str = "Report Issue"

    # Footer content
    footer_description: str = "Pebbling is a decentralized agent-to-agent communication protocol. <strong>Hibiscus</strong> is our registry and <strong>Imagine</strong> is the multi-orchestrator platform where you can pebblify your agent and be part of the agent economy."
    footer_local_version_text: str = "This is the local version. For production deployment, please follow the"
    footer_copyright_year: str = "2025"
    footer_company: str = "Pebbling AI"
    footer_location: str = "Amsterdam"

    @computed_field
    @property
    def page_subtitles(self) -> dict[str, str]:
        """Page subtitle mappings."""
        return {
            "agent": "Agent Information & Capabilities",
            "chat": "Interactive Chat Interface",
            "storage": "Task History & Storage Management",
            "docs": "API Documentation & Examples",
        }


class Settings(BaseSettings):
    """Main settings class that aggregates all configuration components."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="allow",
    )

    project: ProjectSettings = ProjectSettings()
    ui: UISettings = UISettings()


app_settings = Settings()
