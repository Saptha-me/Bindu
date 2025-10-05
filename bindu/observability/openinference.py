import os
import subprocess
import sys
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import Path

from packaging import version

from pebbling.utils.logging import get_logger


@dataclass
class AgentFrameworkSpec:
    framework: str
    instrumentation_package: str
    min_version: str


logger = get_logger("pebbling.observability.openinference")


# The list works on a first-match basis. For example, users working with frameworks
# like Agno may still have the OpenAI package installed, but we don't want to start
# instrumentation for both packages. To avoid this, agent frameworks are given higher
# priority than LLM provider packages.
SUPPORTED_FRAMEWORKS = [
    AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "1.5.2"),
    AgentFrameworkSpec("crewai", "openinference-instrumentation-crewai", "0.41.1"),
    AgentFrameworkSpec("litellm", "openinference-instrumentation-litellm", "1.43.0"),
    AgentFrameworkSpec("openai", "openinference-instrumentation-openai", "1.69.0"),
]

BASE_PACKAGES = [
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp",
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

    required_packages = BASE_PACKAGES + [framework_spec.instrumentation_package]
    missing_packages = [package for package in required_packages if package not in installed_distributions]

    if missing_packages:
        logger.info("Installing the following packages", packages=", ".join(missing_packages))
        # Currently we only try to search if user has uv installed or not
        # In case uv is present use it to install the packages, if not
        # fallback to use the environment's pip
        current_directory = Path.cwd()
        use_uv = (current_directory / "uv.lock").exists() or (current_directory / "pyproject.toml").exists()

        if use_uv:
            cmd = ["uv", "add"] + missing_packages
            package_manager = "uv"
        else:
            cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
            package_manager = "pip"

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
            logger.info("Successfully installed the packages", package_manager=package_manager)
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to install the packages", package_manager=package_manager, error=str(exc))
            return
        except subprocess.TimeoutExpired:
            logger.error("Package installation timed out", package_manager=package_manager)
            return
    else:
        logger.info("All required packages are installed")

    logger.info("Starting OpenInference instrumentation setup", framework=framework_spec.framework)

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

        tracer_provider = trace_sdk.TracerProvider()

        otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        if otel_endpoint:
            tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(otel_endpoint)))
            logger.info("Configured OTLP exporter", endpoint=otel_endpoint)
        else:
            tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            logger.info("Using console exporter - no OTLP endpoint configured")

        match framework_spec.framework:
            case "agno":
                from openinference.instrumentation.agno import AgnoInstrumentor

                AgnoInstrumentor().instrument(tracer_provider=tracer_provider)
            case "crewai":
                from openinference.instrumentation.crewai import CrewAIInstrumentor

                CrewAIInstrumentor().instrument(tracer_provider=tracer_provider)
            case "openai":
                from openinference.instrumentation.openai import OpenAIInstrumentor

                OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
            case "litellm":
                from openinference.instrumentation.litellm import LiteLLMInstrumentor

                LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info("OpenInference setup completed successfully", framework=framework_spec.framework)
    except ImportError as e:
        logger.error(
            "OpenInference setup failed - instrumentation packages not available",
            framework=framework_spec.framework,
            error=str(e),
        )
