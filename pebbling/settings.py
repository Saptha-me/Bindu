"""Settings configuration for the Pebbling agent system.

This module defines the configuration settings for the application using pydantic models.
"""

import os
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


class BrandingSettings(BaseSettings):
    """Branding and UI configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BRANDING__",
        extra="allow",
    )

    logo_emoji: str = "🐧"
    default_agent_name: str = "Pebbling Agent"
    protocol_name: str = "Pebbling Protocol"
    protocol_url: str = "https://pebbling.ai"
    powered_by_text: str = "Fueled by"


class LinksSettings(BaseSettings):
    """External links configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LINKS__",
        extra="allow",
    )

    docs_url: str = "https://docs.pebbling.ai"
    docs_text: str = "Documentation"
    github_url: str = "https://github.com/Pebbling-ai/pebble"
    github_text: str = "GitHub"
    github_issues_url: str = "https://github.com/Pebbling-ai/pebble/issues"
    github_issues_text: str = "Report Issue"


class UISettings(BaseSettings):
    """UI text and status configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="UI__",
        extra="allow",
    )

    status_online_text: str = "Online"
    status_active_text: str = "Active"
    agent_subtitle_default: str = "Agent Information & Capabilities"

    @computed_field
    @property
    def page_subtitles(self) -> dict[str, str]:
        """Page subtitle mappings."""
        return {
            'agent': 'Agent Information & Capabilities',
            'chat': 'Interactive Chat Interface',
            'storage': 'Task History & Storage Management',
            'docs': 'API Documentation & Examples'
        }


class FooterSettings(BaseSettings):
    """Footer content configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FOOTER__",
        extra="allow",
    )

    description: str = "Pebbling is a decentralized agent-to-agent communication protocol. <strong>Hibiscus</strong> is our registry and <strong>Imagine</strong> is the multi-orchestrator platform where you can pebblify your agent and be part of the agent economy."
    local_version_text: str = "This is the local version. For production deployment, please follow the"
    copyright_year: str = "2025"
    company: str = "Pebbling AI"
    location: str = "Amsterdam"


class Settings(BaseSettings):
    """Main settings class that aggregates all configuration components."""

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="allow",
    )

    project: ProjectSettings = ProjectSettings()
    branding: BrandingSettings = BrandingSettings()
    links: LinksSettings = LinksSettings()
    ui: UISettings = UISettings()
    footer: FooterSettings = FooterSettings()


app_settings = Settings()
