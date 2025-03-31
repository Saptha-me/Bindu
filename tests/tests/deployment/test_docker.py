"""Tests for the Docker deployment module."""

import pytest
from unittest.mock import MagicMock, patch
import os
from pathlib import Path

from pebble.deployment.docker import create_docker_deployment
from pebble.schemas.models import DeploymentConfig, DockerConfig


class TestDockerDeployment:
    """Tests for the Docker deployment module."""
    
    def test_create_docker_deployment(self, temp_dir):
        """Test creating Docker deployment artifacts."""
        # Setup
        adapters = [MagicMock(), MagicMock()]
        adapters[0].name = "TestAgent1"
        adapters[1].name = "TestAgent2"
        
        config = DeploymentConfig(
            docker_config=DockerConfig(
                base_image="python:3.10-slim",
                output_dir=str(temp_dir),
                include_requirements=True,
                expose_port=8000,
                environment_vars={
                    "API_KEY": "${API_KEY}"
                }
            )
        )
        
        # Create Docker deployment
        result = create_docker_deployment(adapters, config)
        
        # Verify result is the output directory
        assert result == str(temp_dir)
        
        # Verify files were created
        assert os.path.exists(os.path.join(temp_dir, "Dockerfile"))
        assert os.path.exists(os.path.join(temp_dir, "docker-compose.yml"))
        assert os.path.exists(os.path.join(temp_dir, "requirements.txt"))
        assert os.path.exists(os.path.join(temp_dir, "app.py"))
        assert os.path.exists(os.path.join(temp_dir, "start.sh"))
        
        # Check Dockerfile content
        with open(os.path.join(temp_dir, "Dockerfile"), "r") as f:
            dockerfile = f.read()
            assert "FROM python:3.10-slim" in dockerfile
            assert "COPY requirements.txt" in dockerfile
            assert "EXPOSE 8000" in dockerfile
        
        # Check docker-compose.yml content
        with open(os.path.join(temp_dir, "docker-compose.yml"), "r") as f:
            compose = f.read()
            assert "image: pebble-agent" in compose
            assert "8000:8000" in compose
            assert "API_KEY" in compose