# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Observability: AI Agent Tracing & Monitoring.

This package provides automatic instrumentation for AI observability using OpenInference
and OpenTelemetry standards. It enables you to trace, monitor, and debug your AI agents
in production.

## Why Observability Matters

AI agents are complex systems with:
- Multiple LLM calls and tool invocations
- Non-deterministic behavior
- Complex reasoning chains
- Distributed execution across services

Without observability, debugging issues like:
- Why did the agent make this decision?
- Which tools were called and in what order?
- How much did this conversation cost?
- Where are the performance bottlenecks?

...becomes nearly impossible.

## What This Package Does

1. **Auto-Detection**: Automatically detects your AI framework (Agno, LangChain, CrewAI, etc.)
2. **Zero-Config Tracing**: Sets up OpenTelemetry instrumentation with minimal configuration
3. **Rich Context**: Captures LLM prompts, responses, tool calls, and agent reasoning
4. **Standard Format**: Uses OpenInference semantic conventions for AI observability
5. **Flexible Export**: Send traces to Phoenix, Arize, Langfuse, or any OTLP endpoint

## Quick Start

```python
from bindu.observability import setup

# Call once at application startup
setup()

# Your agent code runs as normal, but now with full tracing!
```

## Configuration

Set environment variables to control trace export:

```bash
# Export to Phoenix (local observability UI)
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:6006/v1/traces"

# Export to Arize (production monitoring)
export OTEL_EXPORTER_OTLP_ENDPOINT="https://otlp.arize.com/v1"
export OTEL_EXPORTER_OTLP_HEADERS="space_key=YOUR_KEY,api_key=YOUR_API_KEY"
```

If no endpoint is configured, traces are printed to console for development.

## Supported Frameworks

- **Agent Frameworks**: Agno, CrewAI, LangChain, LlamaIndex, DSPy, Haystack, etc.
- **LLM Providers**: OpenAI, Anthropic, Mistral, Groq, Bedrock, VertexAI, etc.

See `openinference.py` for the complete list.

## Learn More

- OpenInference: https://github.com/Arize-ai/openinference
- Phoenix UI: https://docs.arize.com/phoenix
- OpenTelemetry: https://opentelemetry.io
"""

from .openinference import setup

__all__ = ["setup"]
