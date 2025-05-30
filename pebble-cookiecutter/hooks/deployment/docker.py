#!/usr/bin/env python
"""Docker deployment configuration using Google Kaniko."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from string import Template
from ..utils.file_operations import write_file


def read_template_file(template_path: str) -> str:
    """Read a template file and return its contents."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    full_path = os.path.join(template_dir, template_path)
    
    with open(full_path, 'r') as file:
        return file.read()


def setup_docker_deployment(project_slug: str) -> None:
    """Set up the files needed for Docker deployment with Kaniko."""
    # Copy Dockerfile to project root
    dockerfile_template = read_template_file('docker/Dockerfile.tmpl')
    dockerfile_content = Template(dockerfile_template).substitute(project_slug=project_slug)
    write_file('Dockerfile', dockerfile_content)
    
    # Create kaniko build script
    kaniko_script_template = read_template_file('docker/kaniko_build.py.tmpl')
    kaniko_script = Template(kaniko_script_template).substitute(project_slug=project_slug)
    write_file(os.path.join(project_slug, 'kaniko_build.py'), kaniko_script)
    
    # Make the kaniko script executable
    kaniko_script_path = os.path.join(os.path.realpath(os.path.curdir), project_slug, 'kaniko_build.py')
    os.chmod(kaniko_script_path, 0o755)
    
    # Create a .dockerignore file
    dockerignore_content = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.venv
env/
venv/
ENV/

# IDE files
.idea/
.vscode/
*.swp
*.swo

# Git
.git
.gitignore

# Logs
logs/
*.log

# Docker
.dockerignore
Dockerfile
docker-compose.yml
"""
    write_file('.dockerignore', dockerignore_content)
