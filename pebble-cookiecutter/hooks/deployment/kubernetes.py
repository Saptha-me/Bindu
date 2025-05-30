#!/usr/bin/env python
"""Kubernetes deployment configuration using Helm charts."""
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


def setup_kubernetes_deployment(project_slug: str) -> None:
    """Set up Helm chart for Kubernetes deployment."""
    # Create the helm directory structure
    chart_dir = os.path.join(os.path.realpath(os.path.curdir), 'helm', project_slug)
    os.makedirs(chart_dir, exist_ok=True)
    os.makedirs(os.path.join(chart_dir, 'templates'), exist_ok=True)
    os.makedirs(os.path.join(chart_dir, 'charts'), exist_ok=True)
    
    # Process and write all template files
    templates_to_process = [
        ('kubernetes/Chart.yaml.tmpl', os.path.join('helm', project_slug, 'Chart.yaml')),
        ('kubernetes/values.yaml.tmpl', os.path.join('helm', project_slug, 'values.yaml')),
        ('kubernetes/deployment.yaml.tmpl', os.path.join('helm', project_slug, 'templates', 'deployment.yaml')),
        ('kubernetes/service.yaml.tmpl', os.path.join('helm', project_slug, 'templates', 'service.yaml')),
        ('kubernetes/_helpers.tpl.tmpl', os.path.join('helm', project_slug, 'templates', '_helpers.tpl')),
        ('kubernetes/NOTES.txt.tmpl', os.path.join('helm', project_slug, 'templates', 'NOTES.txt')),
        ('kubernetes/README.md.tmpl', os.path.join('helm', project_slug, 'README.md')),
    ]
    
    for template_path, output_path in templates_to_process:
        template_content = read_template_file(template_path)
        processed_content = Template(template_content).substitute(project_slug=project_slug)
        write_file(output_path, processed_content)
    
    # Create a helper script for deploying with Helm
    helm_deploy_script_template = read_template_file('kubernetes/helm_deploy.py.tmpl')
    helm_deploy_script = Template(helm_deploy_script_template).substitute(project_slug=project_slug)
    write_file(os.path.join(project_slug, 'helm_deploy.py'), helm_deploy_script)
    
    # Make the deploy script executable
    helm_script_path = os.path.join(os.path.realpath(os.path.curdir), project_slug, 'helm_deploy.py')
    os.chmod(helm_script_path, 0o755)
