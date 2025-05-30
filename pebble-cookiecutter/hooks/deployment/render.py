#!/usr/bin/env python
"""Render.com deployment configuration."""
from __future__ import annotations

import os
from string import Template
from ..utils.file_operations import write_file


def read_template_file(template_path: str) -> str:
    """Read a template file and return its contents."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
    full_path = os.path.join(template_dir, template_path)
    
    with open(full_path, 'r') as file:
        return file.read()


def setup_render_deployment(project_slug: str) -> None:
    """Set up the files needed for Render.com deployment."""
    # render.yaml file for Render deployment
    render_yaml_template = read_template_file('render/render.yaml.tmpl')
    render_yaml_content = Template(render_yaml_template).substitute(project_slug=project_slug)
    write_file('render.yaml', render_yaml_content)
