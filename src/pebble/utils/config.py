"""
Configuration utilities for the Pebble framework.

This module provides utilities for managing environment variables and configuration.
"""

import os
import pathlib
from typing import Dict, Optional


def get_project_root() -> pathlib.Path:
    """Get the root directory of the project.
    
    Returns:
        pathlib.Path: The root directory
    """
    # Calculate the root directory from the current file
    current_file = pathlib.Path(__file__).resolve()
    return current_file.parent.parent.parent.parent.parent


def get_env_file_path() -> pathlib.Path:
    """Get the path to the .env file.
    
    Returns:
        pathlib.Path: The path to the .env file
    """
    return get_project_root() / ".env"


def ensure_env_file() -> pathlib.Path:
    """Ensure the .env file exists and contains necessary variables.
    
    Returns:
        pathlib.Path: The path to the .env file
    """
    import base64
    import os
    
    env_file = get_env_file_path()
    
    # Create parent directories if they don't exist
    env_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Read existing content if the file exists
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
                except ValueError:
                    continue
    
    # Add missing environment variables
    changed = False
    
    # SECRET_KEY for security operations
    if "SECRET_KEY" not in env_vars:
        env_vars["SECRET_KEY"] = base64.b64encode(os.urandom(42)).decode()
        changed = True
    
    # Write the updated file if changes were made
    if changed or not env_file.exists():
        with open(env_file, "w") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
    
    return env_file


def load_env_vars() -> Dict[str, str]:
    """Load environment variables from the .env file.
    
    Returns:
        Dict[str, str]: Dictionary of environment variables
    """
    try:
        from dotenv import load_dotenv
        
        # Try to load from .env file
        env_file = get_env_file_path()
        if env_file.exists():
            load_dotenv(dotenv_path=env_file)
    except ImportError:
        # If python-dotenv is not installed, just use the existing environment
        pass
    
    # Return a dictionary of environment variables
    return dict(os.environ)
