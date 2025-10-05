# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

from __future__ import annotations

import os
import sys
from importlib.metadata import distributions

from packaging import version

from bindu.utils.logging import get_logger
from bindu.common.models import AgentFrameworkSpec
from bindu.utils.constants import OPENINFERENCE_INSTRUMENTOR_MAP, OPENTELEMETRY_BASE_PACKAGES
from typing import Type, Any


logger = get_logger("bindu.observability.openinference")


def _get_package_manager() -> tuple[list[str], str]:
    """Detect available package manager and return install command prefix."""
    from pathlib import Path
    
    current_directory = Path.cwd()
    use_uv = (current_directory / "uv.lock").exists() or (current_directory / "pyproject.toml").exists()
    
    if use_uv:
        return ["uv", "add"], "uv"
    return [sys.executable, "-m", "pip", "install"], "pip"


def _instrument_framework(framework: str, tracer_provider: Any) -> None:
    """Dynamically import and instrument a framework.
    
    Args:
        framework: Name of the framework to instrument
        tracer_provider: OpenTelemetry tracer provider instance
    
    Raises:
        ImportError: If instrumentor module or class not found
    """
    if framework not in OPENINFERENCE_INSTRUMENTOR_MAP:
        logger.warn(f"No instrumentor mapping found for framework: {framework}")
        return
    
    module_path, class_name = OPENINFERENCE_INSTRUMENTOR_MAP[framework]
    
    try:
        # Dynamic import of instrumentor module
        import importlib
        module = importlib.import_module(module_path)
        instrumentor_class = getattr(module, class_name)
        
        # Instantiate and instrument
        instrumentor_class().instrument(tracer_provider=tracer_provider)
        logger.info(f"Successfully instrumented {framework} using {class_name}")
    except (ImportError, AttributeError) as e:
        logger.error(
            f"Failed to instrument {framework}",
            module=module_path,
            class_name=class_name,
            error=str(e)
        )


# The list works on a first-match basis. For example, users working with frameworks
# like Agno may still have the OpenAI package installed, but we don't want to start
# instrumentation for both packages. To avoid this, agent frameworks are given higher
# priority than LLM provider packages.
# https://github.com/Arize-ai/openinference?tab=readme-ov-file#python

# Priority order matters: agent frameworks before LLM providers
# to avoid double instrumentation (e.g., Agno uses OpenAI internally)
SUPPORTED_FRAMEWORKS = [
    # Agent Frameworks (Higher Priority)
    AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "1.5.2"),
    AgentFrameworkSpec("crewai", "openinference-instrumentation-crewai", "0.41.1"),
    AgentFrameworkSpec("langchain", "openinference-instrumentation-langchain", "0.1.0"),
    AgentFrameworkSpec("llama-index", "openinference-instrumentation-llama-index", "0.1.0"),
    AgentFrameworkSpec("dspy", "openinference-instrumentation-dspy", "2.0.0"),
    AgentFrameworkSpec("haystack", "openinference-instrumentation-haystack", "2.0.0"),
    AgentFrameworkSpec("instructor", "openinference-instrumentation-instructor", "1.0.0"),
    AgentFrameworkSpec("pydantic-ai", "openinference-instrumentation-pydantic-ai", "0.1.0"),
    AgentFrameworkSpec("autogen", "openinference-instrumentation-autogen-agentchat", "0.4.0"),
    AgentFrameworkSpec("smolagents", "openinference-instrumentation-smolagents", "1.0.0"),
    
    # LLM Providers (Lower Priority)
    AgentFrameworkSpec("litellm", "openinference-instrumentation-litellm", "1.43.0"),
    AgentFrameworkSpec("openai", "openinference-instrumentation-openai", "1.69.0"),
    AgentFrameworkSpec("anthropic", "openinference-instrumentation-anthropic", "0.1.0"),
    AgentFrameworkSpec("mistralai", "openinference-instrumentation-mistralai", "1.0.0"),
    AgentFrameworkSpec("groq", "openinference-instrumentation-groq", "0.1.0"),
    AgentFrameworkSpec("bedrock", "openinference-instrumentation-bedrock", "0.1.0"),
    AgentFrameworkSpec("vertexai", "openinference-instrumentation-vertexai", "1.0.0"),
    AgentFrameworkSpec("google-genai", "openinference-instrumentation-google-genai", "0.1.0"),
]



def setup() -> None:
    installed_distributions = {dist.name: dist for dist in distributions()}
    framework_spec = next((spec for spec in SUPPORTED_FRAMEWORKS if spec.framework in installed_distributions), None)

    if not framework_spec:
        logger.info(
            "OpenInference setup skipped - no supported agent framework found",
            supported_frameworks=[spec.framework for spec in SUPPORTED_FRAMEWORKS],
        )
        return

    framework_dist = installed_distributions[framework_spec.framework]
    installed_version = framework_dist.version

    if version.parse(installed_version) < version.parse(framework_spec.min_version):
        logger.warn(
            "OpenInference setup skipped - agent framework package is below the supported package version",
            agent_framework=framework_spec.framework,
            installed_version=installed_version,
            required_version=framework_spec.min_version,
        )
        return

    logger.info(
        "Agent framework identified",
        agent_framework=framework_spec.framework,
        instrumentation_package=framework_spec.instrumentation_package,
        version=installed_version,
    )

    required_packages = OPENTELEMETRY_BASE_PACKAGES + [framework_spec.instrumentation_package]
    missing_packages = [package for package in required_packages if package not in installed_distributions]

    if missing_packages:
        cmd_prefix, package_manager = _get_package_manager()
        cmd = cmd_prefix + missing_packages
        
        logger.warn(
            "Missing OpenInference packages detected",
            packages=", ".join(missing_packages),
            install_command=" ".join(cmd),
        )
        logger.warn(
            "Auto-installation disabled for safety. Please install manually:",
            command=" ".join(cmd)
        )
        return
        
        # OPTIONAL: Enable auto-install with environment variable
        # if os.getenv("BINDU_AUTO_INSTALL_OBSERVABILITY") == "true":
        #     logger.info("Auto-installing packages", packages=", ".join(missing_packages))
        #     try:
        #         subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
        #         logger.info("Successfully installed packages", package_manager=package_manager)
        #     except subprocess.CalledProcessError as exc:
        #         logger.error("Failed to install packages", package_manager=package_manager, error=str(exc))
        #         return
        #     except subprocess.TimeoutExpired:
        #         logger.error("Package installation timed out", package_manager=package_manager)
        #         return
    else:
        logger.info("All required packages are installed")

    logger.info("Starting OpenInference instrumentation setup", framework=framework_spec.framework)

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        tracer_provider = trace_sdk.TracerProvider()

        otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if otel_endpoint:
            tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(otel_endpoint)))
            logger.info("Configured OTLP exporter", endpoint=otel_endpoint)
        else:
            tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            logger.info("Using console exporter - no OTLP endpoint configured")

        _instrument_framework(framework_spec.framework, tracer_provider)

        logger.info("OpenInference setup completed successfully", framework=framework_spec.framework)
    except ImportError as e:
        logger.error(
            "OpenInference setup failed - instrumentation packages not available",
            framework=framework_spec.framework,
            error=str(e),
        )
