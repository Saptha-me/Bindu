# X402 Discovery Metadata Enhancement

## Overview

Enhanced `X402AgentExtension.create_payment_requirements()` to support **AI agent discovery metadata** following the official [Coinbase x402 specification](https://docs.cdp.coinbase.com/x402/quickstart-for-sellers).

## What Changed

### Added Parameter: `input_schema`

```python
def create_payment_requirements(
    self,
    resource: str,
    description: str = "",
    mime_type: str = "application/json",
    scheme: str = "exact",
    max_timeout_seconds: Optional[int] = None,
    input_schema: Optional[Dict[str, Any]] = None,  # ← NEW
    output_schema: Optional[Any] = None,
    pay_to_address: Optional[str] = None,
    **kwargs: Any,
) -> PaymentRequirements:
```

## Why This Matters

### For AI Agents
- **Automatic API understanding**: AI agents can parse JSON schemas to understand how to call your API
- **Type safety**: Schemas define expected types, formats, and constraints
- **Self-documentation**: No need for separate API documentation

### For Discovery
- **x402 Bazaar integration**: Better ranking in service discovery
- **Search optimization**: Agents can find services matching their needs
- **Interoperability**: Standard schema format works across all x402 clients

### For Developers
- **Clear contracts**: Input/output schemas define API behavior
- **Validation**: Clients can validate requests before payment
- **Better DX**: Rich metadata improves developer experience

## Usage Examples

### Basic Example: Weather API

```python
from bindu.extensions.x402 import X402AgentExtension

x402 = X402AgentExtension(
    amount="10000",  # $0.01 USDC
    token="USDC",
    network="base-sepolia",
    pay_to_address="0x..."
)

requirements = x402.create_payment_requirements(
    resource="/api/weather",
    description="Get real-time weather data for any location",
    input_schema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name or coordinates"
            },
            "units": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "default": "fahrenheit"
            }
        },
        "required": ["location"]
    },
    output_schema={
        "type": "object",
        "properties": {
            "temperature": {"type": "number"},
            "conditions": {"type": "string"},
            "humidity": {"type": "number"}
        }
    }
)
```

### Advanced Example: Data Analysis API

```python
requirements = x402.create_payment_requirements(
    resource="/api/analyze",
    description="Analyze datasets using ML algorithms",
    input_schema={
        "type": "object",
        "properties": {
            "dataset_url": {
                "type": "string",
                "format": "uri",
                "description": "URL to CSV, JSON, or Parquet dataset"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["statistical", "predictive", "clustering"],
                "description": "Type of analysis to perform"
            },
            "options": {
                "type": "object",
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
            "summary": {"type": "string"},
            "visualizations": {
                "type": "array",
                "items": {"type": "string", "format": "uri"}
            }
        }
    }
)
```

## JSON Schema Best Practices

### 1. Use Descriptive Properties
```json
{
  "location": {
    "type": "string",
    "description": "City name or coordinates (e.g., 'San Francisco' or '37.7749,-122.4194')"
  }
}
```

### 2. Define Constraints
```json
{
  "confidence_level": {
    "type": "number",
    "minimum": 0.8,
    "maximum": 0.99,
    "default": 0.95
  }
}
```

### 3. Use Enums for Fixed Values
```json
{
  "units": {
    "type": "string",
    "enum": ["celsius", "fahrenheit"],
    "default": "fahrenheit"
  }
}
```

### 4. Specify Required Fields
```json
{
  "type": "object",
  "properties": { ... },
  "required": ["location", "dataset_url"]
}
```

### 5. Use Format Hints
```json
{
  "timestamp": {"type": "string", "format": "date-time"},
  "url": {"type": "string", "format": "uri"},
  "email": {"type": "string", "format": "email"}
}
```

## Integration with Agent Configuration

### In `agent_config.json`:

```json
{
  "name": "weather-agent",
  "execution_cost": {
    "amount": "10000",
    "token": "USDC",
    "network": "base-sepolia",
    "pay_to_address": "0x..."
  },
  "skills": [
    {
      "name": "get_weather",
      "description": "Get weather data",
      "input_schema": {
        "type": "object",
        "properties": {
          "location": {"type": "string"}
        }
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "temperature": {"type": "number"}
        }
      }
    }
  ]
}
```

### In Agent Code:

```python
from bindu.penguin import bindufy

@bindufy(config_path="agent_config.json")
def weather_agent(location: str) -> dict:
    """Get weather data for a location."""
    # Agent automatically creates payment requirements
    # with input_schema and output_schema from config
    return {
        "temperature": 72,
        "conditions": "sunny",
        "humidity": 45
    }
```

## Comparison with Official x402

### Official x402 (Express.js)
```javascript
app.use(paymentMiddleware(
  "0xYourAddress",
  {
    "GET /weather": {
      price: "$0.001",
      network: "base-sepolia",
      config: {
        description: "Get weather data",
        inputSchema: { /* JSON schema */ },
        outputSchema: { /* JSON schema */ }
      }
    }
  }
));
```

### Bindu x402 (Python)
```python
x402 = X402AgentExtension(
    amount="1000",
    network="base-sepolia",
    pay_to_address="0xYourAddress"
)

requirements = x402.create_payment_requirements(
    resource="/weather",
    description="Get weather data",
    input_schema={ /* JSON schema */ },
    output_schema={ /* JSON schema */ }
)
```

**Result**: Same functionality, adapted for A2A Protocol!

## Testing

Run the example:
```bash
python examples/x402_discovery_example.py
```

See comprehensive examples with:
- Weather API
- Data Analysis API
- Quote API
- Image Generation API

## References

- [Official x402 Docs](https://docs.cdp.coinbase.com/x402/welcome)
- [x402 Quickstart for Sellers](https://docs.cdp.coinbase.com/x402/quickstart-for-sellers)
- [x402 Bazaar Documentation](https://docs.cdp.coinbase.com/x402/bazaar)
- [JSON Schema Specification](https://json-schema.org/)
- [Bindu x402 Plan](./x402-plan.md)

## Next Steps

1. ✅ **Enhanced discovery metadata** - DONE
2. 🔄 **Create Python client library** - Similar to `x402-axios` for automatic payment handling
3. 🔄 **Add facilitator configuration** - Align with official endpoints
4. 🔄 **Implement x402 Bazaar integration** - Service discovery and listing
5. 🔄 **Add validation layer** - Validate requests against input schemas

---

**Status**: ✅ Complete - Discovery metadata now fully supported!
