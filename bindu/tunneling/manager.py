"""Tunnel manager for creating and managing tunnels."""

import secrets
import string
from typing import Optional

from bindu.tunneling.config import TunnelConfig
from bindu.tunneling.tunnel import Tunnel
from bindu.utils.logging import get_logger

logger = get_logger("bindu.tunneling.manager")


class TunnelManager:
    """Manages tunnel creation, lifecycle, and public URL access."""

    def __init__(self):
        """Initialize the tunnel manager."""
        self.active_tunnel: Optional[Tunnel] = None

    def create_tunnel(
        self,
        local_port: int,
        config: Optional[TunnelConfig] = None,
        subdomain: Optional[str] = None,
    ) -> str:
        """
        Create and start a tunnel exposing a local port.

        Args:
            local_port: Local port to expose.
            config: Optional tunnel configuration.
            subdomain: Optional custom subdomain.

        Returns:
            The public URL of the created tunnel.

        Raises:
            ValueError: If the port number is invalid.
            RuntimeError: If a tunnel is already active.
        """

        # Validate port range
        if type(local_port) is not int or not (1 <= local_port <= 65535):
            raise ValueError("local_port must be an integer between 1 and 65535")

        # Prevent multiple active tunnels
        if self.active_tunnel is not None:
            raise RuntimeError(
                "A tunnel is already active. Stop it before creating a new one."
            )

        # Use default config if none provided
        if config is None:
            config = TunnelConfig(enabled=True)

        config.local_port = local_port

        # Determine subdomain
        if subdomain:
            config.subdomain = subdomain
        elif not config.subdomain:
            config.subdomain = self._generate_subdomain()

        logger.info(
            f"Creating tunnel for localhost:{local_port} with subdomain '{config.subdomain}'"
        )

        tunnel = Tunnel(config)

        try:
            public_url = tunnel.start()
            self.active_tunnel = tunnel
            logger.info(f"Tunnel started successfully at {public_url}")
            return public_url

        except Exception:
            logger.exception("Failed to create tunnel during startup")
            raise

    def stop_tunnel(self) -> None:
        """
        Stop the currently active tunnel if one exists.

        Ensures cleanup even if stopping the tunnel raises an exception.
        """

        if self.active_tunnel:
            try:
                self.active_tunnel.stop()
                logger.info("Tunnel stopped")

            except Exception:
                logger.exception("Error while stopping tunnel")

            finally:
                # Always clear active tunnel reference
                self.active_tunnel = None

        else:
            logger.debug("No active tunnel to stop")

    def get_public_url(self) -> Optional[str]:
        """
        Return the public URL of the active tunnel.

        Returns:
            The tunnel's public URL if active, otherwise None.
        """
        if self.active_tunnel:
            return self.active_tunnel.public_url
        return None

    @staticmethod
    def _generate_subdomain_from_did(agent_did: str) -> str:
        """
        Generate a DNS-safe subdomain from an agent DID.

        Converts the DID into a lowercase string and removes or replaces
        characters that are not valid in DNS labels.

        Ensures:
        - Only alphanumeric characters and hyphens remain
        - The label starts with a letter
        - Maximum length is 63 characters
        """

        # Remove DID prefix and normalize separators
        subdomain = agent_did.replace("did:", "").replace(":", "-").lower()

        # Replace unsupported characters
        subdomain = subdomain.replace("_", "-").replace("@", "-at-").replace(".", "-")

        # Remove invalid DNS characters
        subdomain = "".join(c if c.isalnum() or c == "-" else "" for c in subdomain)

        # Ensure it starts with a letter (DNS requirement)
        if subdomain and not subdomain[0].isalpha():
            subdomain = "a" + subdomain

        # DNS labels must be <= 63 characters
        if len(subdomain) > 63:
            subdomain = subdomain[:63]

        # Remove trailing hyphen
        subdomain = subdomain.rstrip("-")

        return subdomain or "agent"

    @staticmethod
    def _generate_subdomain(length: int = 12) -> str:
        """
        Generate a random DNS-safe subdomain.

        Args:
            length: Length of the generated subdomain.

        Returns:
            Random lowercase alphanumeric subdomain.
        """

        alphabet = string.ascii_lowercase + string.digits

        # Ensure the first character is a letter
        subdomain = secrets.choice(string.ascii_lowercase)

        # Remaining characters can include digits
        subdomain += "".join(secrets.choice(alphabet) for _ in range(length - 1))

        return subdomain

    def __enter__(self):
        """Support usage as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure tunnel cleanup when exiting context."""
        self.stop_tunnel()
        return False