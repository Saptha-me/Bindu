"""Version information for Bindu."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_version() -> str:
    """Get the current version of Bindu.

    Returns version from git tags if available, otherwise falls back to
    the version file generated during build, or a default version.

    Returns:
        Version string (e.g., "0.3.14" or "0.3.14.dev5+g1234567")
    """
    # Try to get version from _version.py (generated during build)
    try:
        from bindu._version import __version__

        return __version__
    except ImportError:
        pass

    # Try to get version from git tags (for development)
    try:
        repo_root = Path(__file__).parent.parent
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            # Clean up git describe output (e.g., "v0.3.14-5-g1234567" -> "0.3.14.dev5+g1234567")
            if version.startswith("v"):
                version = version[1:]
            return version
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass

    # Fallback version
    return "0.3.14"


__version__ = get_version()
