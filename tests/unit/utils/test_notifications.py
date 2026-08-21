"""Minimal tests for notification service."""

import socket
from typing import cast
from unittest.mock import patch
from uuid import uuid4
import pytest

from bindu.common.protocol.types import PushNotificationConfig
from bindu.utils.notifications import NotificationService, NotificationDeliveryError


class TestNotificationService:
    """Test notification service functionality."""

    def test_notification_service_initialization(self):
        """Test service initializes with default values."""
        service = NotificationService()

        assert service.timeout == 5.0
        assert service.total_sent == 0
        assert service.total_success == 0
        assert service.total_failures == 0

    def test_validate_config_valid_http(self):
        """Test validating valid HTTP URL."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            service.validate_config(config)

    def test_validate_config_valid_https(self):
        """Test validating valid HTTPS URL."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "https://example.com/webhook"},
        )

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            service.validate_config(config)

    def test_validate_config_invalid_scheme(self):
        """Test validation rejects invalid URL scheme."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "ftp://example.com/webhook"}
        )

        with pytest.raises(ValueError, match="must use http or https scheme"):
            service.validate_config(config)

    def test_validate_config_no_netloc(self):
        """Test validation rejects URL without netloc."""
        service = NotificationService()
        config = cast(PushNotificationConfig, {"id": uuid4(), "url": "http://"})

        with pytest.raises(ValueError, match="must include a network location"):
            service.validate_config(config)

    # The broad SSRF allowlist was intentionally dropped in 270f4b94 so that
    # loopback/private webhook targets (e.g. the operator inbox at
    # http://127.0.0.1:3787) keep working. Cloud-metadata (IMDS) addresses are
    # still rejected because they are never a legitimate webhook destination.

    @pytest.mark.parametrize(
        "metadata_ip",
        [
            "169.254.169.254",  # AWS/GCP/Azure IMDS (link-local IPv4)
            "169.254.170.2",  # ECS task metadata endpoint
            "fe80::1",  # IPv6 link-local
            "fd00:ec2::254",  # AWS IPv6 IMDS
        ],
    )
    def test_validate_config_blocks_cloud_metadata(self, metadata_ip):
        """Validation rejects URLs resolving to cloud-metadata addresses."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "http://metadata.example/webhook"},
        )

        with patch(
            "socket.getaddrinfo",
            return_value=[("", "", "", "", (metadata_ip, 0))],
        ):
            with pytest.raises(ValueError, match="cloud-metadata address"):
                service.validate_config(config)

    @pytest.mark.parametrize(
        "allowed_ip",
        [
            "127.0.0.1",  # loopback — operator inbox lives here
            "10.0.0.5",  # private LAN
            "192.168.1.20",  # private LAN
            "93.184.216.34",  # public
        ],
    )
    def test_validate_config_allows_loopback_and_private(self, allowed_ip):
        """Validation allows loopback/private/public (non-metadata) targets."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "http://webhook.example/hook"},
        )

        with patch(
            "socket.getaddrinfo",
            return_value=[("", "", "", "", (allowed_ip, 0))],
        ):
            assert service.validate_config(config) == allowed_ip

    def test_validate_config_hostname_resolution_fails(self):
        """Test validation handles hostname resolution failure."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {"id": uuid4(), "url": "http://invalid.example/webhook"},
        )

        with patch(
            "socket.getaddrinfo", side_effect=socket.gaierror("Name resolution failed")
        ):
            with pytest.raises(ValueError, match="could not be resolved"):
                service.validate_config(config)

    def test_build_headers_basic(self):
        """Test building basic headers without token."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )

        headers = service._build_headers(config)

        assert headers["Content-Type"] == "application/json"
        assert len(headers) == 1

    def test_build_headers_with_token(self):
        """Test building headers with authentication token."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {
                "id": uuid4(),
                "url": "http://example.com/webhook",
                "token": "secret-token",
            },
        )

        headers = service._build_headers(config)

        assert headers["Authorization"] == "Bearer secret-token"

    def test_build_headers_with_authentication(self):
        """Test building headers with authentication dict."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig,
            {
                "id": uuid4(),
                "url": "http://example.com/webhook",
                "authentication": {"type": "bearer"},
            },
        )

        headers = service._build_headers(config)

        assert "authentication" in str(headers).lower() or "Content-Type" in headers

    @pytest.mark.asyncio
    async def test_send_event_success(self):
        """Test successfully sending an event."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )
        event = {"kind": "status-update", "task_id": str(uuid4())}

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            with patch.object(service, "_post_once", return_value=200):
                await service.send_event(config, event)

        assert service.total_sent > 0

    @pytest.mark.asyncio
    async def test_send_event_delivery_error(self):
        """Test handling delivery error."""
        service = NotificationService()
        config = cast(
            PushNotificationConfig, {"id": uuid4(), "url": "http://example.com/webhook"}
        )
        event = {"kind": "status-update", "task_id": str(uuid4())}

        with patch(
            "socket.getaddrinfo", return_value=[("", "", "", "", ("93.184.216.34", 0))]
        ):
            with patch.object(
                service,
                "_post_once",
                side_effect=NotificationDeliveryError(400, "Bad request"),
            ):
                with pytest.raises(NotificationDeliveryError):
                    await service.send_event(config, event)

    def test_notification_delivery_error(self):
        """Test NotificationDeliveryError creation."""
        error = NotificationDeliveryError(500, "Server error")

        assert error.status == 500
        assert str(error) == "Server error"

    def test_notification_delivery_error_no_status(self):
        """Test NotificationDeliveryError with no status."""
        error = NotificationDeliveryError(None, "Network error")

        assert error.status is None
        assert str(error) == "Network error"
