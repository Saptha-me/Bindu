# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""OpenInference instrumentation setup for AI observability.

This module automatically detects installed AI frameworks and sets up
OpenTelemetry instrumentation for tracing and observability.

Supported frameworks are prioritized (agent frameworks before LLM providers)
to avoid double instrumentation when frameworks use other frameworks internally.
"""

from __future__ import annotations

import importlib
import sys
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

from packaging import version

from bindu.common.models import AgentFrameworkSpec
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.observability.openinference")

# Priority order matters: agent frameworks before LLM providers
# to avoid double instrumentation (e.g., Agno uses OpenAI internally)
# Reference: https://github.com/Arize-ai/openinference?tab=readme-ov-file#python
SUPPORTED_FRAMEWORKS = [
    # Agent Frameworks (Higher Priority)
    AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "1.5.2"),
    AgentFrameworkSpec("crewai", "openinference-instrumentation-crewai", "0.41.1"),
    AgentFrameworkSpec("langchain", "openinference-instrumentation-langchain", "0.1.0"),
    AgentFrameworkSpec(
        "llama-index", "openinference-instrumentation-llama-index", "0.1.0"
    ),
    AgentFrameworkSpec("dspy", "openinference-instrumentation-dspy", "2.0.0"),
    AgentFrameworkSpec("haystack", "openinference-instrumentation-haystack", "2.0.0"),
    AgentFrameworkSpec(
        "instructor", "openinference-instrumentation-instructor", "1.0.0"
    ),
    AgentFrameworkSpec(
        "pydantic-ai", "openinference-instrumentation-pydantic-ai", "0.1.0"
    ),
    AgentFrameworkSpec(
        "autogen", "openinference-instrumentation-autogen-agentchat", "0.4.0"
    ),
    AgentFrameworkSpec(
        "smolagents", "openinference-instrumentation-smolagents", "1.0.0"
    ),
    # LLM Providers (Lower Priority)
    AgentFrameworkSpec("litellm", "openinference-instrumentation-litellm", "1.43.0"),
    AgentFrameworkSpec("openai", "openinference-instrumentation-openai", "1.69.0"),
    AgentFrameworkSpec("anthropic", "openinference-instrumentation-anthropic", "0.1.0"),
    AgentFrameworkSpec("mistralai", "openinference-instrumentation-mistralai", "1.0.0"),
    AgentFrameworkSpec("groq", "openinference-instrumentation-groq", "0.1.0"),
    AgentFrameworkSpec("bedrock", "openinference-instrumentation-bedrock", "0.1.0"),
    AgentFrameworkSpec("vertexai", "openinference-instrumentation-vertexai", "1.0.0"),
    AgentFrameworkSpec(
        "google-genai", "openinference-instrumentation-google-genai", "0.1.0"
    ),
]


def _get_package_manager() -> tuple[list[str], str]:
    """Detect available package manager and return install command prefix.

    Returns:
        Tuple of (command_prefix, package_manager_name)
    """
    current_directory = Path.cwd()
    has_uv = (current_directory / "uv.lock").exists() or (
        current_directory / "pyproject.toml"
    ).exists()

    if has_uv:
        return ["uv", "add"], "uv"
    return [sys.executable, "-m", "pip", "install"], "pip"


def _instrument_framework(framework: str, tracer_provider: Any) -> None:
    """Dynamically import and instrument a framework.

    Args:
        framework: Name of the framework to instrument
        tracer_provider: OpenTelemetry tracer provider instance
    """
    if framework not in app_settings.observability.instrumentor_map:
        logger.warning(f"No instrumentor mapping found for framework: {framework}")
        return

    module_path, class_name = app_settings.observability.instrumentor_map[framework]

    try:
        module = importlib.import_module(module_path)
        instrumentor_class = getattr(module, class_name)
        instrumentor_class().instrument(tracer_provider=tracer_provider)
        logger.info(f"Successfully instrumented {framework} using {class_name}")
    except (ImportError, AttributeError) as e:
        logger.error(
            f"Failed to instrument {framework}",
            module=module_path,
            class_name=class_name,
            error=str(e),
        )


def _detect_framework(installed_dists: dict[str, Any]) -> AgentFrameworkSpec | None:
    """Detect the first matching supported framework from installed packages.

    Args:
        installed_dists: Dictionary of installed package distributions

    Returns:
        AgentFrameworkSpec if found, None otherwise
    """
    return next(
        (spec for spec in SUPPORTED_FRAMEWORKS if spec.framework in installed_dists),
        None,
    )


def _validate_framework_version(
    framework_spec: AgentFrameworkSpec, installed_version: str
) -> bool:
    """Validate that installed framework version meets minimum requirements.

    Args:
        framework_spec: Framework specification with minimum version
        installed_version: Currently installed version

    Returns:
        True if version is valid, False otherwise
    """
    return version.parse(installed_version) >= version.parse(framework_spec.min_version)


def _check_missing_packages(
    framework_spec: AgentFrameworkSpec, installed_dists: dict[str, Any]
) -> list[str]:
    """Check for missing OpenTelemetry packages.

    Args:
        framework_spec: Framework specification
        installed_dists: Dictionary of installed package distributions

    Returns:
        List of missing package names
    """
    required_packages = app_settings.observability.base_packages + [
        framework_spec.instrumentation_package
    ]
    return [pkg for pkg in required_packages if pkg not in installed_dists]


class _LoggingSpanExporter:
    """Wrapper exporter that logs when spans are exported."""

    def __init__(self, exporter: Any, endpoint: str, verbose: bool = False):
        self._exporter = exporter
        self._endpoint = endpoint
        self._span_count = 0
        self._verbose = verbose

    def export(self, spans: Any) -> Any:
        """Export spans and log the operation."""
        from opentelemetry.sdk.trace.export import SpanExportResult

        result = self._exporter.export(spans)
        self._span_count += len(spans)

        if self._verbose:
            if result == SpanExportResult.SUCCESS:
                logger.info(
                    f"Successfully exported {len(spans)} span(s) to OTLP endpoint",
                    endpoint=self._endpoint,
                    total_exported=self._span_count,
                )
            else:
                logger.error(
                    f"Failed to export {len(spans)} span(s) to OTLP endpoint",
                    endpoint=self._endpoint,
                    reason=result.name,
                )

        return result

    def shutdown(self) -> Any:
        """Shutdown the underlying exporter."""
        return self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> Any:
        """Force flush the underlying exporter."""
        return self._exporter.force_flush(timeout_millis)


def _setup_tracer_provider(
    oltp_endpoint: str | None = None,
    oltp_service_name: str | None = None,
    verbose_logging: bool = False,
    service_version: str = "1.0.0",
    deployment_environment: str = "production",
    batch_max_queue_size: int = 2048,
    batch_schedule_delay_millis: int = 5000,
    batch_max_export_batch_size: int = 512,
    batch_export_timeout_millis: int = 30000,
) -> Any:
    """Set up and configure OpenTelemetry tracer provider.

    Args:
        oltp_endpoint: OTLP endpoint URL
        oltp_service_name: Service name for traces
        verbose_logging: Enable verbose telemetry logging
        service_version: Service version for traces
        deployment_environment: Deployment environment
        batch_max_queue_size: Max queue size for batch processor
        batch_schedule_delay_millis: Schedule delay for batch processor
        batch_max_export_batch_size: Max export batch size
        batch_export_timeout_millis: Export timeout in milliseconds

    Returns:
        Configured TracerProvider instance
    """
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk import trace as trace_sdk
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    # Create resource with service metadata for better trace organization
    resource_attrs = {
        SERVICE_NAME: oltp_service_name or "bindu-agent",
        SERVICE_VERSION: service_version,
        "deployment.environment": deployment_environment,
    }

    resource = Resource.create(resource_attrs)
    tracer_provider = trace_sdk.TracerProvider(resource=resource)

    # Use provided endpoint or fall back to console
    if oltp_endpoint:
        # Create OTLP exporter with logging wrapper
        otlp_exporter = OTLPSpanExporter(endpoint=oltp_endpoint)
        logging_exporter = _LoggingSpanExporter(
            otlp_exporter, oltp_endpoint, verbose_logging
        )

        # Use batch processor configuration from parameters
        batch_config = {
            "max_queue_size": batch_max_queue_size,
            "schedule_delay_millis": batch_schedule_delay_millis,
            "max_export_batch_size": batch_max_export_batch_size,
            "export_timeout_millis": batch_export_timeout_millis,
        }
        # Type ignore: _LoggingSpanExporter implements SpanExporter protocol
        processor = BatchSpanProcessor(logging_exporter, **batch_config)  # type: ignore[arg-type]
        if verbose_logging:
            logger.info(
                "Configured OTLP exporter with batch processing",
                endpoint=oltp_endpoint,
                max_queue_size=batch_max_queue_size,
                schedule_delay_millis=batch_schedule_delay_millis,
                max_export_batch_size=batch_max_export_batch_size,
                export_timeout_millis=batch_export_timeout_millis,
            )

        tracer_provider.add_span_processor(processor)
    else:
        tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        if verbose_logging:
            logger.info("Using console exporter - no OTLP endpoint configured")

    # Set as global tracer provider so all tracers use it
    trace.set_tracer_provider(tracer_provider)
    if verbose_logging:
        logger.info(
            "Global tracer provider configured",
            service_name=resource_attrs[SERVICE_NAME],
            environment=resource_attrs["deployment.environment"],
        )

    return tracer_provider


def setup(
    oltp_endpoint: str | None = None,
    oltp_service_name: str | None = None,
    verbose_logging: bool = False,
    service_version: str = "1.0.0",
    deployment_environment: str = "production",
    batch_max_queue_size: int = 2048,
    batch_schedule_delay_millis: int = 5000,
    batch_max_export_batch_size: int = 512,
    batch_export_timeout_millis: int = 30000,
) -> None:
    """Set up OpenInference instrumentation for AI observability.

    This function:
    1. Sets up OpenTelemetry tracer provider (always)
    2. Optionally instruments AI frameworks if available

    Args:
        oltp_endpoint: OTLP endpoint URL for sending traces
        oltp_service_name: Service name for identifying traces
        verbose_logging: Enable verbose telemetry logging
        service_version: Service version for traces
        deployment_environment: Deployment environment
        batch_max_queue_size: Max queue size for batch processor
        batch_schedule_delay_millis: Schedule delay for batch processor
        batch_max_export_batch_size: Max export batch size
        batch_export_timeout_millis: Export timeout in milliseconds
    """
    # ALWAYS setup tracer provider first (for Bindu framework tracing)
    tracer_provider = _setup_tracer_provider(
        oltp_endpoint=oltp_endpoint,
        oltp_service_name=oltp_service_name,
        verbose_logging=verbose_logging,
        service_version=service_version,
        deployment_environment=deployment_environment,
        batch_max_queue_size=batch_max_queue_size,
        batch_schedule_delay_millis=batch_schedule_delay_millis,
        batch_max_export_batch_size=batch_max_export_batch_size,
        batch_export_timeout_millis=batch_export_timeout_millis,
    )

    # Step 1: Detect installed framework for optional instrumentation
    installed_dists = {dist.name: dist for dist in distributions()}
    framework_spec = _detect_framework(installed_dists)

    if not framework_spec:
        if verbose_logging:
            logger.info(
                "OpenInference framework instrumentation skipped - no supported agent framework found",
                supported_frameworks=[spec.framework for spec in SUPPORTED_FRAMEWORKS],
            )
        return

    # Step 2: Validate framework version
    installed_version = installed_dists[framework_spec.framework].version

    if not _validate_framework_version(framework_spec, installed_version):
        if verbose_logging:
            logger.warning(
                "OpenInference framework instrumentation skipped - framework version below minimum",
                framework=framework_spec.framework,
                installed_version=installed_version,
                required_version=framework_spec.min_version,
            )
        return

    if verbose_logging:
        logger.info(
            "Agent framework detected",
            framework=framework_spec.framework,
            version=installed_version,
            instrumentation_package=framework_spec.instrumentation_package,
        )

    # Step 3: Check for missing packages
    missing_packages = _check_missing_packages(framework_spec, installed_dists)

    if missing_packages:
        cmd_prefix, package_manager = _get_package_manager()
        install_cmd = " ".join(cmd_prefix + missing_packages)

        logger.warning(
            "Missing OpenInference packages - auto-installation disabled for safety",
            packages=", ".join(missing_packages),
            install_command=install_cmd,
        )
        if verbose_logging:
            logger.info(
                "Bindu framework tracing is active, but LLM-level tracing requires instrumentation packages"
            )
        return

    if verbose_logging:
        logger.info("All required packages installed")

    # Step 4: Setup framework instrumentation
    if verbose_logging:
        logger.info(
            "Starting OpenInference framework instrumentation",
            framework=framework_spec.framework,
        )

    try:
        _instrument_framework(framework_spec.framework, tracer_provider)
        if verbose_logging:
            logger.info(
                "OpenInference framework instrumentation completed successfully",
                framework=framework_spec.framework,
            )
    except ImportError as e:
        logger.error(
            "OpenInference framework instrumentation failed - instrumentation packages unavailable",
            framework=framework_spec.framework,
            error=str(e),
        )
