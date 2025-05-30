#!/usr/bin/env python
"""File operation utilities for project generation."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

PROJECT_DIRECTORY = os.path.realpath(os.path.curdir)


def remove_file(filepath: str) -> None:
    """Remove a file from the project directory."""
    os.remove(os.path.join(PROJECT_DIRECTORY, filepath))


def remove_dir(filepath: str) -> None:
    """Remove a directory from the project directory."""
    shutil.rmtree(os.path.join(PROJECT_DIRECTORY, filepath))


def move_file(filepath: str, target: str) -> None:
    """Move a file within the project directory."""
    os.rename(os.path.join(PROJECT_DIRECTORY, filepath), os.path.join(PROJECT_DIRECTORY, target))


def move_dir(src: str, target: str) -> None:
    """Move a directory within the project directory."""
    shutil.move(os.path.join(PROJECT_DIRECTORY, src), os.path.join(PROJECT_DIRECTORY, target))


def write_file(filepath: str, content: str) -> None:
    """Write content to a file in the project directory."""
    full_path = os.path.join(PROJECT_DIRECTORY, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w') as f:
        f.write(content)
