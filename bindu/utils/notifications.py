"""Push notification delivery service for agent task events."""

from __future__ import annotations

import asyncio
import http.client
import ipaddress
import json
import socket
import ssl
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from bindu.common.protocol.types import PushNotificationConfig
from bindu.utils.logging import get_logger
from bindu.utils.retry import create_retry_decorator

logger = get_logger("bindu.utils.notifications")


# AWS exposes its IPv6 Instance Metadata Service at this address. It sits in
# unique-local (fd00::/8) space rather than link-local, so ``is_link_local``
# alone would not catch it — list it explicitly.
_AWS_IPV6_IMDS = ipaddress.ip_address("fd00:ec2::254")


def _is_cloud_metadata_address(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    """Return True if *ip* is a cloud-provider metadata (IMDS) endpoint.

    Covers the link-local range 169.254.0.0/16 (fe80::/10 for IPv6) used by the
    AWS/GCP/Azure metadata service at 169.254.169.254, plus AWS's IPv6 IMDS
    address. Loopback and ordinary private LAN ranges are intentionally *not*
    blocked — the operator inbox delivers webhooks to http://127.0.0.1 and
    private networks are a legitimate single-tenant deployment target.
    """
    return ip.is_link_local or ip == _AWS_IPV6_IMDS


def _resolve_and_check_ip(hostname: str) -> str:
    """Resolve *hostname* and reject cloud-metadata (IMDS) addresses.

    The hostname is resolved exactly once and the resulting IP is returned so the
    caller can connect directly to it, closing the DNS-rebinding window where a
    second resolution could return a different address (TOCTOU SSRF).

    Only cloud-metadata endpoints are rejected. Loopback and private ranges are
    allowed on purpose (see ``_is_cloud_metadata_address``).

    Args:
        hostname: The hostname to resolve.

    Returns:
        The resolved IP address as a string.

    Raises:
        ValueError: If the hostname cannot be resolved or resolves to a
            cloud-metadata address.
    """
    try:
        resolved = str(socket.getaddrinfo(hostname, None)[0][4][0])
    except socket.gaierror as exc:
        raise ValueError(
            f"Push notification URL hostname could not be resolved: {exc}"
        ) from exc

    if _is_cloud_metadata_address(ipaddress.ip_address(resolved)):
        raise ValueError(
            "Push notification URL resolves to a cloud-metadata address "
            f"({resolved}), which is not an allowed webhook destination."
        )
    return resolved


class NotificationDeliveryError(Exception):
    """Raised when a push notification cannot be delivered."""

    def __init__(self, status: int | None, message: str):
        """Initialize notification delivery error.

        Args:
            status: HTTP status code if available
            message: Error message
        """
        super().__init__(message)
        self.status = status


@dataclass
class NotificationService:
    """Deliver push notification events to configured HTTP endpoints.

    Includes lightweight in-memory delivery metrics for observability.
    Uses unified retry decorator for consistent retry behavior.
    """

    timeout: float = 5.0

    # --- Metrics ---
    total_sent: int = 0
    total_success: int = 0
    total_failures: int = 0

    async def send_event(
        self, config: PushNotificationConfig, event: dict[str, Any]
    ) -> None:
        """Send an event to the configured HTTP webhook.

        The hostname is resolved once here and the resulting IP is passed
        through to the HTTP layer.  This single-resolution approach closes the
        DNS-rebinding window that exists when validation and connection each
        perform independent DNS lookups (TOCTOU SSRF).
        """
        resolved_ip = self.validate_config(config)

        # default=str so values that aren't natively JSON-serializable
        # (most commonly uuid.UUID on artifact.artifact_id, also
        # datetime, Path, etc.) coerce to their string form instead of
        # raising TypeError mid-serialization. Lifecycle events are
        # all-primitive and unaffected; artifact events embed a raw
        # Artifact TypedDict with a UUID inside, which without this
        # would silently drop on the floor at the _notify_artifact
        # exception boundary.
        payload = json.dumps(event, separators=(",", ":"), default=str).encode("utf-8")
        headers = self._build_headers(config)

        # Use unified retry decorator for consistent retry behavior
        await self._post_with_retry(config["url"], resolved_ip, headers, payload, event)

    def validate_config(self, config: PushNotificationConfig) -> str:
        """Validate push notification configuration before use.

        In addition to URL structure checks this method resolves the hostname
        and rejects cloud-metadata (IMDS) addresses to prevent the most damaging
        class of Server-Side Request Forgery (SSRF). Loopback and private LAN
        ranges are intentionally allowed so that the local operator inbox and
        single-tenant deployments keep working; broader host validation belongs
        at the auth-gated webhook-registration layer.

        Returns the resolved IP address so the caller can connect directly to it,
        eliminating the DNS-rebinding race between validation and connection.
        """
        parsed = urlparse(config["url"])
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Push notification URL must use http or https scheme.")
        if not parsed.netloc:
            raise ValueError("Push notification URL must include a network location.")

        # SSRF defence: resolve the hostname and reject cloud-metadata addresses.
        # The returned IP is used directly for the connection so that no second
        # DNS lookup can return a different (metadata) address.
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Push notification URL must include a valid hostname.")

        return _resolve_and_check_ip(hostname)

    @create_retry_decorator("api", max_attempts=3, min_wait=0.5, max_wait=5.0)
    async def _post_with_retry(
        self,
        url: str,
        resolved_ip: str,
        headers: dict[str, str],
        payload: bytes,
        event: dict[str, Any],
    ) -> None:
        """Send POST request with automatic retry via unified retry decorator."""
        # --- Metrics: count total attempts to send ---
        self.total_sent += 1

        try:
            status = await asyncio.to_thread(
                self._post_once, url, resolved_ip, headers, payload
            )
            logger.debug(
                "Delivered push notification",
                event_id=event.get("event_id"),
                task_id=event.get("task_id"),
                status=status,
            )
            self.total_success += 1
        except NotificationDeliveryError as exc:
            # Don't retry 4xx client errors (except 429 rate limit)
            if exc.status is not None and 400 <= exc.status < 500 and exc.status != 429:
                logger.warning(
                    "Dropping push notification due to client error",
                    event_id=event.get("event_id"),
                    task_id=event.get("task_id"),
                    status=exc.status,
                    message=str(exc),
                )
                self.total_failures += 1
                raise

            # For retryable errors, let the decorator handle it
            logger.error(
                "Failed to deliver push notification",
                event_id=event.get("event_id"),
                task_id=event.get("task_id"),
                status=exc.status,
                message=str(exc),
            )
            self.total_failures += 1
            raise

    def _post_once(
        self, url: str, resolved_ip: str, headers: dict[str, str], payload: bytes
    ) -> int:
        """POST *payload* to *url*, connecting directly to *resolved_ip*.

        Bypassing a second DNS lookup closes the DNS-rebinding window: the IP
        has already been validated in validate_config() and we re-use it here so
        that no attacker-controlled DNS TTL change can redirect the connection to
        an internal address between validation and delivery.

        For HTTPS, a raw TCP socket is opened to *resolved_ip* and then wrapped
        with TLS using *hostname* as the SNI server_hostname, so certificate
        validation still uses the original domain name rather than the IP.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        # Set the Host header explicitly so virtual-host routing works correctly
        # even though we are connecting to a raw IP.
        host_header = f"{hostname}:{port}" if parsed.port else hostname

        try:
            if parsed.scheme == "https":
                # Open a plain TCP socket to the pre-validated IP, then wrap it
                # with TLS using the original hostname for SNI and cert validation.
                # This avoids a second DNS lookup while keeping TLS correct.
                ctx = ssl.create_default_context()
                raw_sock = socket.create_connection(
                    (resolved_ip, port), timeout=self.timeout
                )
                tls_sock = ctx.wrap_socket(raw_sock, server_hostname=hostname)
                conn = http.client.HTTPSConnection(
                    resolved_ip, port, timeout=self.timeout, context=ctx
                )
                conn.sock = tls_sock
            else:
                conn = http.client.HTTPConnection(
                    resolved_ip, port, timeout=self.timeout
                )

            request_headers = dict(headers)
            request_headers["Host"] = host_header

            conn.request("POST", path, body=payload, headers=request_headers)
            response = conn.getresponse()
            status = response.status
            if 200 <= status < 300:
                return status

            body = b""
            try:
                body = response.read() or b""
            except OSError:
                body = b""
            message = body.decode("utf-8", errors="ignore").strip()
            raise NotificationDeliveryError(status, message or f"HTTP error {status}")
        except NotificationDeliveryError:
            raise
        except (OSError, http.client.HTTPException) as exc:
            raise NotificationDeliveryError(None, f"Connection error: {exc}") from exc

    def _build_headers(self, config: PushNotificationConfig) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = config.get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def get_metrics(self) -> dict[str, int]:
        """Return delivery metrics for observability."""
        return {
            "total_sent": self.total_sent,
            "total_success": self.total_success,
            "total_failures": self.total_failures,
        }
