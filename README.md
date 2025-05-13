<h1 align="center">pebbling 🐧</h1>

<h1 align="center">Agent-to-Agent Communication </h1>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Pebbling-ai/pebble/actions/workflows/release.yml/badge.svg)](https://github.com/Pebbling-ai/pebble/actions/workflows/release.yml)
[![Coverage Status](https://coveralls.io/repos/github/Pebbling-ai/pebble/badge.svg?branch=main)](https://coveralls.io/github/Pebbling-ai/pebble?branch=main)
[![PyPI version](https://badge.fury.io/py/pebbling.svg)](https://badge.fury.io/py/pebbling)
[![Discord](https://img.shields.io/discord/bgwYGs7t?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/bgwYGs7t)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.pebbling.ai)

🪨 pebbling is the easiest way to enable seamless, secure communication between autonomous AI agents.

💡 Built on **JSON-RPC 2.0** over **mutual TLS (mTLS)**, pebbling provides a lightweight yet powerful protocol framework for the next generation of collaborative AI systems.

## 🌟 Features

- **Secure by Default** - Built-in mutual TLS authentication and encryption
- **Simple API** - Easy-to-use decorators for defining and invoking agent methods
- **Protocol Flexibility** - JSON-RPC 2.0 core with extensible transport layers
- **Fast and Lightweight** - Minimal dependencies and efficient performance
- **Language Agnostic** - Core protocol works with any language that supports JSON-RPC
- **Highly Testable** - >80% test coverage with comprehensive integration tests

## 📦 Installation

```bash
# Using pip
pip install pebbling

# Using uv (recommended)
uv pip install pebbling
```

## 🚀 Quick Start

### Creating a Server

```python
from pebbling.server import pebblify

# Define your agent's API
@pebblify
class CalculatorAgent:
    def add(self, a: int, b: int) -> int:
        return a + b
        
    def multiply(self, a: int, b: int) -> int:
        return a * b

# Start the server
if __name__ == "__main__":
    calculator = CalculatorAgent()
    calculator.serve(host="0.0.0.0", port=8000)
```

### Connecting to a Server

```python
from pebbling.client import PebblingClient

# Connect to the calculator agent
client = PebblingClient("localhost", 8000)

# Call methods
result1 = client.call("add", {"a": 5, "b": 3})
print(f"5 + 3 = {result1}")  # Output: 5 + 3 = 8

result2 = client.call("multiply", {"a": 5, "b": 3})
print(f"5 * 3 = {result2}")  # Output: 5 * 3 = 15
```

## 📖 Documentation

For comprehensive documentation, visit [docs.pebbling.ai](https://docs.pebbling.ai)

## 🧪 Testing

Pebbling is thoroughly tested with a test coverage of over 83%:

```bash
# Run tests with coverage
pytest --cov=pebbling --cov-report=term-missing
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# Clone the repository
git clone https://github.com/Pebbling-ai/pebble.git
cd pebble

# Install development dependencies
uv sync --dev

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

Please see our [Contributing Guidelines](.github/CONTRIBUTING.md) for more details.

## 📄 License

Pebbling is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📢 Community

- Join our [Discord](https://discord.gg/bgwYGs7t) for discussions and support
- Follow us on [Twitter](https://twitter.com/pebblingai) for updates
- Star the repository if you find it useful!

---

Built with ❤️ by the Pebbling team
