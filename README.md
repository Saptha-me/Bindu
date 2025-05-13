<h1 align="center">pebbling 🐧</h1>

<h1 align="center">Agent-to-Agent Communication </h1>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Pebbling-ai/pebble/actions/workflows/release.yml/badge.svg)](https://github.com/Pebbling-ai/pebble/actions/workflows/release.yml)
[![Coverage Status](https://coveralls.io/repos/github/Pebbling-ai/pebble/badge.svg?branch=v0.1.0.5)](https://coveralls.io/github/Pebbling-ai/pebble?branch=v0.1.0.5)
[![PyPI version](https://badge.fury.io/py/pebbling.svg)](https://badge.fury.io/py/pebbling)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/Fr6rcRJa)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.pebbling.ai)

🪨 pebbling is the easiest way to enable seamless, secure communication between autonomous AI agents.

💡 Built on **JSON-RPC 2.0** over **mutual TLS (mTLS)**, pebbling provides a lightweight yet powerful protocol framework for the next generation of collaborative AI systems.

## 🌟 Features

- **Secure by Default** - Built-in mutual TLS authentication and encryption
- **Simple API** - Easy-to-use decorators for defining and invoking agent methods
- **Protocol Flexibility** - JSON-RPC 2.0 core with extensible transport layers
- **Fast and Lightweight** - Minimal dependencies and efficient performance
- **Language Agnostic** - Core protocol works with any language that supports JSON-RPC

## 📦 Installation

```bash
# Using pip
pip install pebbling

# Using uv (recommended)
uv add pebbling
```

## 🚀 Quick Start

### Pebblify an Agent

```python
from pebbling import pebblify

# Define your agent
class MyAgent:
    def say_hello(self):
        return "Hello, Agent!"

# Pebblify your agent
pebblify(MyAgent())

# You're now ready to communicate securely between agents!
```

### Pebblify a [Agno](https://github.com/agno-ai/agno) Agent

```python
from pebbling import pebblify
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    instructions="You are a helpful assistant.",
)

# Pebblify your agent
pebblify(agent)

# You're now ready to communicate securely between agents!
```

## 📖 Documentation

For comprehensive documentation, visit [docs.pebbling.ai](https://docs.pebbling.ai)

## 🧪 Testing

Pebbling is thoroughly tested with a test coverage of over 83%:

```bash
# Run tests with coverage
make test
make coverage
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
make test
```

Please see our [Contributing Guidelines](.github/CONTRIBUTING.md) for more details.

## 📜 License

Pebbling is proudly open-source and licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

## 🎉 Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos — your contributions make Pebbling better.

- Join our [Discord](https://discord.gg/Fr6rcRJa) for discussions and support
- Star the repository if you find it useful!

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Pebbling-ai/pebble&type=Date)](https://star-history.com/#Pebbling-ai/pebble&Date)


Built with ❤️ by the Pebbling team from Amsterdam 🌷.

We’re excited to see what you’ll build with Pebble! Our dream is a world where agents across the internet communicate securely, openly, and effortlessly.

Have questions, ideas, or just want to chat? Join our Discord community— we’d love to hear from you! Together, let’s lay the foundation for the next generation of AI agent collaboration.

Happy Pebbling! 🐧🚀✨
