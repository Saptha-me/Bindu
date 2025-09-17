"""
Certificate utility functions for file operations and path management.

This module contains reusable utilities for certificate management including
file I/O operations, directory handling, and path resolution.
"""

import os
from typing import Optional

from pebbling.utils.constants import CERTIFICATE_DIR
from pebbling.utils.logging import get_logger

logger = get_logger("pebbling.security.common.cert_utils")


def save_certificate_to_file(cert_content: str, file_path: str) -> bool:
    """Save certificate content to file.

    Args:
        cert_content: Certificate content (PEM format)
        file_path: Full path to save the certificate

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write certificate to file
        with open(file_path, "w") as f:
            f.write(cert_content)

        logger.info(f"Certificate saved to: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save certificate to {file_path}: {e}")
        return False


def get_cert_directory(agent_manifest) -> str:
    """Get certificate directory from agent manifest or use default.

    Args:
        agent_manifest: Agent manifest with security configuration

    Returns:
        Path to certificate directory
    """
    # Check if agent manifest has cert_dir specified
    if (
        hasattr(agent_manifest, "security")
        and hasattr(agent_manifest.security, "cert_dir")
        and agent_manifest.security.cert_dir
    ):
        return agent_manifest.security.cert_dir

    # Check alternative location in security config
    if (
        hasattr(agent_manifest, "security_config")
        and hasattr(agent_manifest.security_config, "cert_dir")
        and agent_manifest.security_config.cert_dir
    ):
        return agent_manifest.security_config.cert_dir

    # Use default examples/certs directory
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "examples", CERTIFICATE_DIR
    )


def get_certificate_path(cert_dir: str, filename: str) -> str:
    """Get full path for a certificate file.

    Args:
        cert_dir: Certificate directory path
        filename: Certificate filename

    Returns:
        Full path to certificate file
    """
    return os.path.join(cert_dir, filename)


def ensure_cert_directory_exists(cert_dir: str) -> bool:
    """Ensure certificate directory exists, create if necessary.

    Args:
        cert_dir: Certificate directory path

    Returns:
        True if directory exists or was created successfully
    """
    try:
        os.makedirs(cert_dir, exist_ok=True)
        logger.debug(f"Certificate directory ensured: {cert_dir}")
        return True
    except Exception as e:
        logger.error(f"Failed to create certificate directory {cert_dir}: {e}")
        return False


def load_certificate_from_file(file_path: str) -> Optional[str]:
    """Load certificate content from file.

    Args:
        file_path: Path to certificate file

    Returns:
        Certificate content if successful, None otherwise
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Certificate file does not exist: {file_path}")
            return None

        with open(file_path, "r") as f:
            content = f.read().strip()

        logger.debug(f"Certificate loaded from: {file_path}")
        return content

    except Exception as e:
        logger.error(f"Failed to load certificate from {file_path}: {e}")
        return None
