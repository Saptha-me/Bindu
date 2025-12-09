"""Unit tests for Sentry integration."""

from unittest.mock import patch

from bindu.observability import sentry
from bindu.settings import app_settings


class TestSentryInit:
    """Test Sentry initialization."""

    def test_init_sentry_disabled(self):
        """Test that Sentry doesn't initialize when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            result = sentry.init_sentry()
            assert result is False

    def test_init_sentry_no_dsn(self):
        """Test that Sentry doesn't initialize without DSN."""
        with (
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", ""),
        ):
            result = sentry.init_sentry()
            assert result is False

    def test_init_sentry_success(self):
        """Test successful Sentry initialization."""
        with (
            patch("sentry_sdk.init") as mock_init,
            patch("sentry_sdk.set_tag"),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
            patch.object(app_settings.sentry, "environment", "test"),
            patch.object(app_settings.sentry, "integrations", ["starlette", "asyncio"]),
        ):
            result = sentry.init_sentry()
            assert result is True
            mock_init.assert_called_once()

    def test_init_sentry_with_release(self):
        """Test Sentry initialization with custom release."""
        with (
            patch("sentry_sdk.init") as mock_init,
            patch("sentry_sdk.set_tag"),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
            patch.object(app_settings.sentry, "release", "my-app@1.0.0"),
            patch.object(app_settings.sentry, "integrations", ["starlette"]),
        ):
            result = sentry.init_sentry()
            assert result is True
            # Check that release was passed
            call_kwargs = mock_init.call_args[1]
            assert call_kwargs["release"] == "my-app@1.0.0"

    def test_init_sentry_import_error(self):
        """Test Sentry initialization handles import errors."""
        with (
            patch("sentry_sdk.init", side_effect=ImportError("sentry_sdk not found")),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
        ):
            result = sentry.init_sentry()
            assert result is False

    def test_init_sentry_general_error(self):
        """Test Sentry initialization handles general errors."""
        with (
            patch("sentry_sdk.init", side_effect=Exception("Unexpected error")),
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "dsn", "https://test@sentry.io/123"),
        ):
            result = sentry.init_sentry()
            assert result is False


class TestSentryCapture:
    """Test Sentry capture functions."""

    def test_capture_exception(self):
        """Test capturing exceptions."""
        with (
            patch("sentry_sdk.capture_exception") as mock_capture,
            patch("sentry_sdk.push_scope"),
            patch.object(app_settings.sentry, "enabled", True),
        ):
            error = ValueError("Test error")
            event_id = sentry.capture_exception(
                error, tags={"test": "true"}, extra={"data": "value"}
            )

            mock_capture.assert_called_once_with(error)
            assert event_id is not None

    def test_capture_exception_disabled(self):
        """Test that capture_exception returns None when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            error = ValueError("Test error")
            event_id = sentry.capture_exception(error)
            assert event_id is None

    def test_capture_message(self):
        """Test capturing messages."""
        with (
            patch("sentry_sdk.capture_message") as mock_capture,
            patch("sentry_sdk.push_scope"),
            patch.object(app_settings.sentry, "enabled", True),
        ):
            event_id = sentry.capture_message(
                "Test message", level="warning", tags={"test": "true"}
            )

            mock_capture.assert_called_once_with("Test message", level="warning")
            assert event_id is not None

    def test_capture_message_disabled(self):
        """Test that capture_message returns None when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            event_id = sentry.capture_message("Test message")
            assert event_id is None

    def test_set_user(self):
        """Test setting user context."""
        with (
            patch("sentry_sdk.set_user") as mock_set_user,
            patch.object(app_settings.sentry, "enabled", True),
        ):
            sentry.set_user(user_id="123", email="test@example.com")

            mock_set_user.assert_called_once_with(
                {"id": "123", "email": "test@example.com"}
            )

    def test_set_user_disabled(self):
        """Test that set_user does nothing when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            # Should not raise an error
            sentry.set_user(user_id="123")

    def test_set_context(self):
        """Test setting custom context."""
        with (
            patch("sentry_sdk.set_context") as mock_set_context,
            patch.object(app_settings.sentry, "enabled", True),
        ):
            sentry.set_context("task", {"task_id": "123", "status": "working"})

            mock_set_context.assert_called_once_with(
                "task", {"task_id": "123", "status": "working"}
            )

    def test_set_context_disabled(self):
        """Test that set_context does nothing when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            # Should not raise an error
            sentry.set_context("task", {"task_id": "123"})

    def test_add_breadcrumb(self):
        """Test adding breadcrumbs."""
        with (
            patch("sentry_sdk.add_breadcrumb") as mock_add_breadcrumb,
            patch.object(app_settings.sentry, "enabled", True),
        ):
            sentry.add_breadcrumb(
                message="Task started",
                category="task",
                level="info",
                data={"task_id": "123"},
            )

            mock_add_breadcrumb.assert_called_once_with(
                message="Task started",
                category="task",
                level="info",
                data={"task_id": "123"},
            )

    def test_add_breadcrumb_disabled(self):
        """Test that add_breadcrumb does nothing when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            # Should not raise an error
            sentry.add_breadcrumb("Test breadcrumb")

    def test_start_transaction(self):
        """Test starting a transaction."""
        with (
            patch("sentry_sdk.start_transaction") as mock_start_transaction,
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "enable_tracing", True),
        ):
            _transaction = sentry.start_transaction(name="test_task", op="task")

            mock_start_transaction.assert_called_once_with(name="test_task", op="task")

    def test_start_transaction_disabled(self):
        """Test that start_transaction returns nullcontext when disabled."""
        with patch.object(app_settings.sentry, "enabled", False):
            transaction = sentry.start_transaction(name="test_task")
            # Should return a context manager (nullcontext)
            assert hasattr(transaction, "__enter__")
            assert hasattr(transaction, "__exit__")

    def test_start_transaction_tracing_disabled(self):
        """Test that start_transaction returns nullcontext when tracing disabled."""
        with (
            patch.object(app_settings.sentry, "enabled", True),
            patch.object(app_settings.sentry, "enable_tracing", False),
        ):
            transaction = sentry.start_transaction(name="test_task")
            # Should return a context manager (nullcontext)
            assert hasattr(transaction, "__enter__")
            assert hasattr(transaction, "__exit__")


class TestSentryHooks:
    """Test Sentry before_send hooks."""

    def test_before_send_scrubs_headers(self):
        """Test that before_send scrubs sensitive headers."""
        event = {
            "request": {
                "headers": {
                    "authorization": "Bearer secret_token",
                    "x-api-key": "api_key_123",
                    "cookie": "session=abc123",
                    "content-type": "application/json",
                }
            }
        }

        result = sentry._before_send(event, {})

        assert result is not None
        assert result["request"]["headers"]["authorization"] == "[Filtered]"
        assert result["request"]["headers"]["x-api-key"] == "[Filtered]"
        assert result["request"]["headers"]["cookie"] == "[Filtered]"
        assert result["request"]["headers"]["content-type"] == "application/json"

    def test_before_send_scrubs_data(self):
        """Test that before_send scrubs sensitive data."""
        event = {
            "request": {
                "data": {
                    "password": "secret123",  # pragma: allowlist secret
                    "token": "token_abc",
                    "api_key": "key_xyz",  # pragma: allowlist secret
                    "username": "john_doe",
                }
            }
        }

        result = sentry._before_send(event, {})

        assert result is not None
        assert result["request"]["data"]["password"] == "[Filtered]"
        assert result["request"]["data"]["token"] == "[Filtered]"
        assert result["request"]["data"]["api_key"] == "[Filtered]"
        assert result["request"]["data"]["username"] == "john_doe"

    def test_before_send_transaction_filters(self):
        """Test that before_send_transaction filters health checks."""
        with patch.object(
            app_settings.sentry, "filter_transactions", ["/healthz", "/metrics"]
        ):
            # Health check should be filtered
            event = {"transaction": "/healthz"}
            result = sentry._before_send_transaction(event, {})
            assert result is None

            # Metrics should be filtered
            event = {"transaction": "/metrics"}
            result = sentry._before_send_transaction(event, {})
            assert result is None

            # Normal endpoint should not be filtered
            event = {"transaction": "/api/tasks"}
            result = sentry._before_send_transaction(event, {})
            assert result is not None
            assert result["transaction"] == "/api/tasks"

    def test_before_send_no_request(self):
        """Test that before_send handles events without request."""
        event = {"message": "Test error"}
        result = sentry._before_send(event, {})
        assert result == event

    def test_before_send_transaction_no_transaction(self):
        """Test that before_send_transaction handles events without transaction."""
        event = {"message": "Test"}
        result = sentry._before_send_transaction(event, {})
        assert result == event
