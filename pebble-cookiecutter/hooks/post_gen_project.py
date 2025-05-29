#!/usr/bin/env python
"""
Post-generation script for cookiecutter template.
This script sets up deployment-specific files based on the selected platform.
"""
from __future__ import annotations

import os
import sys

# Add the hooks directory to the Python path so we can import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import deployment modules
# from deployment.flyio import setup_flyio_deployment
# from deployment.render import setup_render_deployment
# from deployment.kubernetes import setup_kubernetes_deployment
# from deployment.docker import setup_docker_deployment


# def setup_deployment_files():
#     """Set up deployment-specific files based on the selected platform."""
#     deployment_platform = "{{cookiecutter.deployment_platform}}"
#     project_slug = "{{cookiecutter.project_slug}}"
    
#     # Platform-specific files
#     if deployment_platform == "fly.io":
#         setup_flyio_deployment(project_slug)
#     elif deployment_platform == "render":
#         setup_render_deployment(project_slug)
#     elif deployment_platform == "kubernetes":
#         setup_kubernetes_deployment(project_slug)
#     elif deployment_platform == "docker":
#         setup_docker_deployment(project_slug)


if __name__ == "__main__":
    # Set up deployment files based on the selected platform
    # setup_deployment_files()
    
    print("Project generated successfully!")
