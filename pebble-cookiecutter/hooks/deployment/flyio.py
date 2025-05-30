#!/usr/bin/env python
"""Fly.io deployment configuration and scripts."""
from __future__ import annotations

import os
from pathlib import Path
from string import Template
from ..utils.file_operations import write_file


def read_template_file(template_path: str) -> str:
    """Read a template file and return its contents."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    full_path = os.path.join(template_dir, template_path)
    
    with open(full_path, 'r') as file:
        return file.read()


def setup_flyio_deployment(project_slug: str) -> None:
    """Set up the files needed for Fly.io deployment."""
    # Read and process template files
    
    # fly.toml file for Fly.io deployment
    fly_toml_template = read_template_file('flyio/fly.toml.tmpl')
    fly_toml_content = Template(fly_toml_template).substitute(project_slug=project_slug)
    write_file('fly.toml', fly_toml_content)
    
    # Create a CLI script for deployments
    deploy_script_template = read_template_file('flyio/deploy.py.tmpl')
    deploy_script = deploy_script_template  # No template variables to substitute in this file
    
    write_file(os.path.join(project_slug, 'deploy.py'), deploy_script)
    
    # Make the deploy script executable
    deploy_script_path = os.path.join(os.path.realpath(os.path.curdir), project_slug, 'deploy.py')
    os.chmod(deploy_script_path, 0o755)
