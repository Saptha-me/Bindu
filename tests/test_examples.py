"""Tests for the example scripts."""

import pytest
import sys
import os
import importlib.util
from unittest.mock import patch, MagicMock

from pathlib import Path


class TestExamples:
    """Tests for the example scripts."""
    
    def _import_module(self, script_path):
        """Import a Python module from a file path."""
        module_name = os.path.basename(script_path).replace(".py", "")
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    
    def test_deploy_local_example(self):
        """Test the deploy_local_server.py example."""
        with patch("pebble.pebblify") as mock_pebblify:
            with patch("agno.agent.Agent") as mock_agent_class:
                with patch("agno.models.openai.OpenAIChat") as mock_model:
                    # Setup mocks
                    mock_agent = MagicMock()
                    mock_agent.name = "Local Web Search Agent"
                    mock_agent_class.return_value = mock_agent
                    
                    # Import and run the example
                    examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
                    script_path = os.path.join(examples_dir, "deploy_local_server.py")
                    
                    # Skip if file doesn't exist
                    if not os.path.exists(script_path):
                        pytest.skip(f"Example file {script_path} not found")
                    
                    # Run the main function
                    module = self._import_module(script_path)
                    with patch.object(module, "__name__", "__main__"):
                        module.main()
                    
                    # Verify pebblify was called
                    mock_pebblify.assert_called_once()
                    args, kwargs = mock_pebblify.call_args
                    assert kwargs["agent"] == mock_agent
                    assert kwargs["name"] == "WebSearchAgent"
                    assert kwargs["autostart"] is True
    
    def test_deploy_with_docker_example(self):
        """Test the deploy_with_docker.py example."""
        with patch("pebble.pebblify") as mock_pebblify:
            with patch("agno.agent.Agent") as mock_agent_class:
                # Setup mocks
                mock_agent = MagicMock()
                mock_agent_class.return_value = mock_agent
                mock_pebblify.return_value = "/path/to/docker"
                
                # Import and run the example
                examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
                script_path = os.path.join(examples_dir, "deploy_with_docker.py")
                
                # Skip if file doesn't exist
                if not os.path.exists(script_path):
                    pytest.skip(f"Example file {script_path} not found")
                
                # Run the main function
                module = self._import_module(script_path)
                with patch.object(module, "__name__", "__main__"):
                    module.main()
                
                # Verify pebblify was called with Docker mode
                mock_pebblify.assert_called_once()
                args, kwargs = mock_pebblify.call_args
                assert kwargs["agent"] == mock_agent
                assert kwargs["config"].mode == DeploymentMode.DOCKER