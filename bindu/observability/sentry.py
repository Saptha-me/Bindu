"""Sentry integration for error tracking and performance monitoring.

This module provides Sentry initialization and configuration for the Bindu framework.
It integrates with FastAPI/Starlette, SQLAlchemy, Redis, and other components to provide
comprehensive error tracking and performance monitoring.

Features:
- Automatic error capture and reporting
- Performance transaction tracking
- Breadcrumb logging for debugging context
- Release tracking for deployment monitoring
- Custom tags and context for filtering
- PII scrubbing for privacy compliance
"""

from __future__ import annotations as _annotations

import socket
from typing import Any

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.observability.sentry")


def init_sentry() -> bool:
    """Initialize Sentry SDK with configuration from settings.

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise
    """
    if not app_settings.sentry.enabled:
        logger.info("Sentry is disabled")
        return False

    if not app_settings.sentry.dsn:
        logger.warning("Sentry is enabled but DSN is not configured")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        # Build integrations list
        integrations: list[Any] = []

        # Core integrations
        if "asyncio" in app_settings.sentry.integrations:
            integrations.append(AsyncioIntegration())

        # Starlette integration (Bindu uses Starlette, not FastAPI)
        # This covers all endpoints in bindu/server/endpoints/
        if "starlette" in app_settings.sentry.integrations:
            integrations.append(
                StarletteIntegration(
                    transaction_style="url",  # Group by URL pattern
                    failed_request_status_codes=[500, 599],  # Only track 5xx as errors
                )
            )

        # Database and cache integrations (both are required dependencies in Bindu)
        if "sqlalchemy" in app_settings.sentry.integrations:
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            integrations.append(SqlalchemyIntegration())

        if "redis" in app_settings.sentry.integrations:
            from sentry_sdk.integrations.redis import RedisIntegration

            integrations.append(RedisIntegration())

        # Determine release version
        release = app_settings.sentry.release
        if not release:
            try:
                from bindu._version import __version__

                release = f"bindu@{__version__}"
            except ImportError:
                release = f"bindu@{app_settings.project.version}"

        # Determine server name
        server_name = app_settings.sentry.server_name
        if not server_name:
            try:
                server_name = socket.gethostname()
            except Exception:
                server_name = "unknown"

        # Build default tags
        default_tags = {
            "environment": app_settings.sentry.environment,
            "server_name": server_name,
            **app_settings.sentry.default_tags,
        }

        # Initialize Sentry SDK
        sentry_sdk.init(
            dsn=app_settings.sentry.dsn,
            environment=app_settings.sentry.environment,
            release=release,
            server_name=server_name,
            integrations=integrations,
            traces_sample_rate=app_settings.sentry.traces_sample_rate,
            profiles_sample_rate=app_settings.sentry.profiles_sample_rate,
            enable_tracing=app_settings.sentry.enable_tracing,
            send_default_pii=app_settings.sentry.send_default_pii,
            max_breadcrumbs=app_settings.sentry.max_breadcrumbs,
            attach_stacktrace=app_settings.sentry.attach_stacktrace,
            debug=app_settings.sentry.debug,
            before_send=_before_send,
            before_send_transaction=_before_send_transaction,
            ignore_errors=app_settings.sentry.ignore_errors,
        )

        # Set default tags
        for key, value in default_tags.items():
            sentry_sdk.set_tag(key, value)

        logger.info(
            "Sentry initialized",
            environment=app_settings.sentry.environment,
            release=release,
            traces_sample_rate=app_settings.sentry.traces_sample_rate,
        )

        return True

    except ImportError as e:
        logger.error("Failed to import Sentry SDK", error=str(e))
        return False
    except Exception as e:
        logger.error("Failed to initialize Sentry", error=str(e))
        return False


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Filter and modify events before sending to Sentry.

    This hook is called before every error event is sent to Sentry.
    Use it to:
    - Scrub sensitive data (passwords, tokens, etc.)
    - Filter out noise (expected errors, health checks, etc.)
    - Add custom context or tags

    Args:
        event: The error event dictionary
        hint: Additional context about the event

    Returns:
        Modified event dict, or None to drop the event
    """
    # Scrub sensitive data from request headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "x-api-key", "cookie", "x-auth-token"]

        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[Filtered]"

    # Scrub sensitive data from request data
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            sensitive_keys = ["password", "token", "secret", "api_key", "private_key"]
            for key in sensitive_keys:
                if key in data:
                    data[key] = "[Filtered]"

    return event


def _before_send_transaction(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any] | None:
    """Filter transactions before sending to Sentry.

    This hook is called before every performance transaction is sent to Sentry.
    Use it to filter out noise like health checks, metrics endpoints, etc.

    Args:
        event: The transaction event dictionary
        hint: Additional context about the event

    Returns:
        Modified event dict, or None to drop the transaction
    """
    # Filter out health check and metrics transactions
    if "transaction" in event:
        transaction_name = event["transaction"]

        # Check if transaction matches any filter pattern
        for pattern in app_settings.sentry.filter_transactions:
            if pattern in transaction_name:
                return None  # Drop this transaction

    return event


def capture_exception(error: Exception, **kwargs: Any) -> str | None:
    """Manually capture an exception and send to Sentry.

    Args:
        error: The exception to capture
        **kwargs: Additional context (tags, extra data, etc.)

    Returns:
        Event ID if captured, None otherwise
    """
    if not app_settings.sentry.enabled:
        return None

    try:
        import sentry_sdk

        # Extract tags and extra data
        tags = kwargs.pop("tags", {})
        extra = kwargs.pop("extra", {})

        # Set context
        with sentry_sdk.push_scope() as scope:
            for key, value in tags.items():
                scope.set_tag(key, value)

            for key, value in extra.items():
                scope.set_extra(key, value)

            # Capture exception
            event_id = sentry_sdk.capture_exception(error)
            logger.debug("Exception captured by Sentry", event_id=event_id)
            return event_id

    except Exception as e:
        logger.error("Failed to capture exception in Sentry", error=str(e))
        return None


def capture_message(message: str, level: str = "info", **kwargs: Any) -> str | None:
    """Manually capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        **kwargs: Additional context (tags, extra data, etc.)

    Returns:
        Event ID if captured, None otherwise
    """
    if not app_settings.sentry.enabled:
        return None

    try:
        import sentry_sdk

        # Extract tags and extra data
        tags = kwargs.pop("tags", {})
        extra = kwargs.pop("extra", {})

        # Set context
        with sentry_sdk.push_scope() as scope:
            for key, value in tags.items():
                scope.set_tag(key, value)

            for key, value in extra.items():
                scope.set_extra(key, value)

            # Capture message
            event_id = sentry_sdk.capture_message(message, level=level)
            logger.debug("Message captured by Sentry", event_id=event_id, level=level)
            return event_id

    except Exception as e:
        logger.error("Failed to capture message in Sentry", error=str(e))
        return None


def set_user(user_id: str | None = None, **kwargs: Any) -> None:
    """Set user context for Sentry events.

    Args:
        user_id: User identifier
        **kwargs: Additional user data (email, username, ip_address, etc.)
    """
    if not app_settings.sentry.enabled:
        return

    try:
        import sentry_sdk

        user_data = {"id": user_id, **kwargs}
        sentry_sdk.set_user(user_data)

    except Exception as e:
        logger.error("Failed to set user context in Sentry", error=str(e))


def set_context(name: str, data: dict[str, Any]) -> None:
    """Set custom context for Sentry events.

    Args:
        name: Context name (e.g., "task", "agent", "conversation")
        data: Context data dictionary
    """
    if not app_settings.sentry.enabled:
        return

    try:
        import sentry_sdk

        sentry_sdk.set_context(name, data)

    except Exception as e:
        logger.error("Failed to set context in Sentry", error=str(e))


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """Add a breadcrumb for debugging context.

    Breadcrumbs are a trail of events that happened before an error.
    They help understand what led to the error.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category (e.g., "http", "db", "auth")
        level: Severity level (debug, info, warning, error, fatal)
        data: Additional data dictionary
    """
    if not app_settings.sentry.enabled:
        return

    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )

    except Exception as e:
        logger.error("Failed to add breadcrumb in Sentry", error=str(e))


def start_transaction(name: str, op: str = "task") -> Any:
    """Start a performance transaction.

    Args:
        name: Transaction name
        op: Operation type (e.g., "task", "http.server", "db.query")

    Returns:
        Transaction context manager
    """
    if not app_settings.sentry.enabled or not app_settings.sentry.enable_tracing:
        # Return a no-op context manager
        from contextlib import nullcontext

        return nullcontext()

    try:
        import sentry_sdk

        return sentry_sdk.start_transaction(name=name, op=op)

    except Exception as e:
        logger.error("Failed to start transaction in Sentry", error=str(e))
        from contextlib import nullcontext

        return nullcontext()
