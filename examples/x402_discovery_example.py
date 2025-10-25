#!/usr/bin/env python3
"""
X402 Discovery Metadata Example

This example demonstrates how to create payment requirements with rich discovery
metadata that enables AI agents to automatically understand and use your paid APIs.

Following the official Coinbase x402 specification for AI agent discovery.
"""

from bindu.extensions.x402 import X402AgentExtension

# Initialize the x402 extension
x402 = X402AgentExtension(
    amount="10000",  # 0.01 USDC = $0.01
    token="USDC",
    network="base-sepolia",
    required=True,
    pay_to_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
)

# Example 1: Weather API with discovery metadata
weather_requirements = x402.create_payment_requirements(
    resource="/api/weather",
    description="Get real-time weather data including temperature, conditions, and humidity for any location worldwide",
    input_schema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or coordinates (e.g., 'San Francisco' or '37.7749,-122.4194')"
            },
            "units": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "default": "fahrenheit",
                "description": "Temperature units"
            }
        },
        "required": ["location"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "temperature": {
                "type": "number",
                "description": "Current temperature in specified units"
            },
            "conditions": {
                "type": "string",
                "description": "Weather conditions (sunny, cloudy, rainy, etc.)"
            },
            "humidity": {
                "type": "number",
                "description": "Humidity percentage (0-100)"
            },
            "wind_speed": {
                "type": "number",
                "description": "Wind speed in mph or km/h"
            }
        },
        "required": ["temperature", "conditions", "humidity"]
    }
)

# Example 2: Data Analysis API
analysis_requirements = x402.create_payment_requirements(
    resource="/api/analyze",
    description="Analyze datasets and extract insights using advanced ML algorithms",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_url": {
                "type": "string",
                "format": "uri",
                "description": "URL to the dataset (CSV, JSON, or Parquet format)"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["statistical", "predictive", "clustering", "anomaly_detection"],
                "description": "Type of analysis to perform"
            },
            "options": {
                "type": "object",
                "description": "Additional analysis options",
                "properties": {
                    "confidence_level": {
                        "type": "number",
                        "minimum": 0.8,
                        "maximum": 0.99,
                        "default": 0.95
                    }
                }
            }
        },
        "required": ["dataset_url", "analysis_type"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding": {"type": "string"},
                        "confidence": {"type": "number"}
                    }
                }
            },
            "summary": {
                "type": "string",
                "description": "Executive summary of findings"
            },
            "visualizations": {
                "type": "array",
                "items": {"type": "string", "format": "uri"}
            }
        }
    }
)

# Example 3: Simple Quote API (minimal metadata)
quote_requirements = x402.create_payment_requirements(
    resource="/api/quote",
    description="Get an inspiring quote about sunsets",
    input_schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Optional prompt to guide quote selection"
            }
        }
    },
    output_schema={
        "type": "object",
        "properties": {
            "quote": {"type": "string"},
            "author": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"}
        }
    }
)

# Example 4: Image Generation API
image_requirements = x402.create_payment_requirements(
    resource="/api/generate-image",
    description="Generate high-quality images using AI based on text descriptions",
    mime_type="image/png",
    input_schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed description of the image to generate",
                "minLength": 10,
                "maxLength": 1000
            },
            "style": {
                "type": "string",
                "enum": ["realistic", "artistic", "cartoon", "abstract"],
                "default": "realistic"
            },
            "dimensions": {
                "type": "object",
                "properties": {
                    "width": {"type": "integer", "minimum": 256, "maximum": 2048},
                    "height": {"type": "integer", "minimum": 256, "maximum": 2048}
                },
                "default": {"width": 1024, "height": 1024}
            }
        },
        "required": ["prompt"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "image_url": {
                "type": "string",
                "format": "uri",
                "description": "URL to the generated image"
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "generation_time": {"type": "number"},
                    "seed": {"type": "integer"}
                }
            }
        }
    }
)

# Print examples
if __name__ == "__main__":
    import json
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.panel import Panel
    
    console = Console()
    
    examples = [
        ("Weather API", weather_requirements),
        ("Data Analysis API", analysis_requirements),
        ("Quote API", quote_requirements),
        ("Image Generation API", image_requirements)
    ]
    
    for title, req in examples:
        # Convert to dict for display
        req_dict = req.model_dump() if hasattr(req, 'model_dump') else dict(req)
        
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
        console.print(Panel(
            Syntax(json.dumps(req_dict, indent=2), "json", theme="monokai"),
            border_style="cyan"
        ))
    
    console.print("\n[bold green]✓ Discovery metadata enables:[/bold green]")
    console.print("  • AI agents automatically understand your API")
    console.print("  • Better ranking in x402 Bazaar")
    console.print("  • Improved discoverability for developers")
    console.print("  • Type-safe integration with client libraries\n")
