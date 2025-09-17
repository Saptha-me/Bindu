import os
import subprocess
import sys
from pathlib import Path
from importlib.metadata import distributions
from dataclasses import dataclass


from pebbling.utils.logging import get_logger


@dataclass
class AgentFrameworkSpec:
    framework: str
    instrumentation_package: str


logger = get_logger("pebbling.observability.openinference")


# The list works on a first-match basis. For example, users working with frameworks
# like Agno may still have the OpenAI package installed, but we don't want to start
# instrumentation for both packages. To avoid this, agent frameworks are given higher
# priority than LLM provider packages.
SUPPORTED_FRAMEWORKS = [
    AgentFrameworkSpec("agno", "openinference-instrumentation-agno"),
    AgentFrameworkSpec("crewai", "openinference-instrumentation-crewai"),
    AgentFrameworkSpec("litellm", "openinference-instrumentation-litellm"),
    AgentFrameworkSpec("openai", "openinference-instrumentation-openai"),
]

BASE_PACKAGES = [
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp",
]


def setup() -> None:
    installed_packages = {dist.name for dist in distributions()}
    framework_spec = next((spec for spec in SUPPORTED_FRAMEWORKS if spec.framework in installed_packages), None)

    if not framework_spec:
        logger.info(
            "OpenInference setup skipped - no supported agent framework found",
            supported_frameworks=[spec.framework for spec in SUPPORTED_FRAMEWORKS],
        )
        return

    logger.info(
        "Agent framework identified",
        agent_framework=framework_spec.framework,
        instrumentation_package=framework_spec.instrumentation_package,
    )

    required_packages = BASE_PACKAGES + [framework_spec.instrumentation_package]
    missing_packages = [package for package in required_packages if package not in installed_packages]

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
        from opentelemetry.sdk import trace as trace_sdk
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor, SimpleSpanProcessor

        tracer_provider = trace_sdk.TracerProvider()

        otel_endpoint = (
            os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
            or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
            or "http://127.0.0.1:6006/v1/traces"
        )
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
