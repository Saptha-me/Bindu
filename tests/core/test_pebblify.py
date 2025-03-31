"""Tests for the pebblify module."""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from uuid import uuid4

from pebble.core.pebblify import pebblify
from pebble.schemas.models import DeploymentConfig, DeploymentMode


class TestPebblify:
    """Tests for the pebblify function."""
    
    def test_pebblify_local_mode(self, mock_agent):
        """Test pebblify with LOCAL mode."""
        with patch("pebble.adapters.get_adapter_for_agent") as mock_get_adapter:
            with patch("pebble.core.pebblify.create_app") as mock_create_app:
                with patch("pebble.core.pebblify.start_server") as mock_start_server:
                    # Setup mocks
                    mock_adapter = MagicMock()
                    mock_get_adapter.return_value = mock_adapter
                    mock_app = MagicMock()
                    mock_create_app.return_value = mock_app
                    
                    # Call pebblify
                    config = DeploymentConfig(mode=DeploymentMode.LOCAL)
                    result = pebblify(
                        agent=mock_agent,
                        config=config,
                        autostart=False
                    )
                    
                    # Verify result
                    assert result == mock_app
                    mock_get_adapter.assert_called_once()
                    mock_create_app.assert_called_once()
                    mock_start_server.assert_not_called()  # autostart=False
    
    def test_pebblify_local_mode_autostart(self, mock_agent):
        """Test pebblify with LOCAL mode and autostart=True."""
        with patch("pebble.adapters.get_adapter_for_agent") as mock_get_adapter:
            with patch("pebble.core.pebblify.create_app") as mock_create_app:
                with patch("pebble.core.pebblify.start_server") as mock_start_server:
                    # Setup mocks
                    mock_adapter = MagicMock()
                    mock_get_adapter.return_value = mock_adapter
                    mock_app = MagicMock()
                    mock_create_app.return_value = mock_app
                    
                    # Call pebblify
                    config = DeploymentConfig(mode=DeploymentMode.LOCAL)
                    result = pebblify(
                        agent=mock_agent,
                        config=config,
                        autostart=True
                    )
                    
                    # Verify result
                    assert result == [mock_adapter]
                    mock_get_adapter.assert_called_once()
                    mock_create_app.assert_called_once()
                    mock_start_server.assert_called_once()
    
    def test_pebblify_router_mode(self, mock_agent):
        """Test pebblify with REGISTER mode."""
        with patch("pebble.adapters.get_adapter_for_agent") as mock_get_adapter:
            with patch("pebble.core.pebblify.create_app") as mock_create_app:
                with patch("pebble.core.pebblify.start_server") as mock_start_server:
                    with patch("pebble.core.pebblify.register_with_router") as mock_register:
                        # Setup mocks
                        mock_adapter = MagicMock()
                        mock_get_adapter.return_value = mock_adapter
                        mock_app = MagicMock()
                        mock_create_app.return_value = mock_app
                        mock_register.return_value = "https://registered.example.com/agent"
                        
                        # Call pebblify
                        config = DeploymentConfig(
                            mode=DeploymentMode.REGISTER,
                            router_config=MagicMock()
                        )
                        result = pebblify(
                            agent=mock_agent,
                            config=config
                        )
                        
                        # Verify result
                        assert result == "https://registered.example.com/agent"
                        mock_get_adapter.assert_called_once()
                        mock_create_app.assert_called_once()
                        mock_register.assert_called_once()
                        mock_start_server.assert_called_once()
    
    def test_pebblify_docker_mode(self, mock_agent):
        """Test pebblify with DOCKER mode."""
        with patch("pebble.adapters.get_adapter_for_agent") as mock_get_adapter:
            with patch("pebble.core.pebblify.create_docker_deployment") as mock_docker:
                # Setup mocks
                mock_adapter = MagicMock()
                mock_get_adapter.return_value = mock_adapter
                mock_docker.return_value = "/path/to/docker"
                
                # Call pebblify
                config = DeploymentConfig(
                    mode=DeploymentMode.DOCKER,
                    docker_config=MagicMock()
                )
                result = pebblify(
                    agent=mock_agent,
                    config=config
                )
                
                # Verify result
                assert result == "/path/to/docker"
                mock_get_adapter.assert_called_once()
                mock_docker.assert_called_once()