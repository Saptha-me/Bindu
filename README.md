<h1 align="center">pebbling ![Pebbling Logo](assets/pebbling-logo.svg)</h1>
<img src="./banner.jpg" alt="Pebbling Banner" width="800">
<h1 align="center">Agent-to-Agent Communication </h1>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Hits](https://hits.sh/github.com/Pebbling-ai/pebble.svg?style=flat-square&label=Hits%20%F0%9F%90%A7&extraCount=100&color=dfb317)](https://hits.sh/github.com/Pebbling-ai/pebble/)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Pebbling-ai/pebble/actions/workflows/release.yml/badge.svg)](https://github.com/Pebbling-ai/pebble/actions/workflows/release.yml)
[![Coverage Status](https://coveralls.io/repos/github/Pebbling-ai/pebble/badge.svg?branch=v0.1.0.5)](https://coveralls.io/github/Pebbling-ai/pebble?branch=v0.1.0.5)
[![PyPI version](https://badge.fury.io/py/pebbling.svg)](https://badge.fury.io/py/pebbling)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pebbling)](https://pypi.org/project/pebbling/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Pebbling-ai/pebble/pulls)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/Fr6rcRJa)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.pebbling.ai)
[![GitHub stars](https://img.shields.io/github/stars/Pebbling-ai/pebble)](https://github.com/Pebbling-ai/pebble/stargazers)

✨ Imagine a world where AI agents collaborate effortlessly and securely—no passport 🚫, no boundaries 🌐.

That’s Pebbling 🐧.An open source, secured protocol for agent-to-agent communication.

🚀 Powered by Decentralised Identifiers (DIDs) 🔑, secured conversations with mutual TLS (mTLS) 🔒, and a lightweight yet powerful communication protocol built on JSON-RPC 2.0 ⚡️—Pebbling is paving the way for the next generation of collaborative AI systems. 🌟🤖


## 🌟 Features

Pebbling helps your AI agents talk to each other seamlessly:

🔒 **Super Secure** - Your agents exchange secrets safely (with built-in mTLS)

🧩 **Plug-and-Play** - Just decorate your agent and it's ready to communicate

⚡ **Lightning Fast** - Quick connections without the weight

🌐 **Works Everywhere** - Connect any agents, regardless of their programming language

🔄 **Reliable Communication** - Messages always arrive correctly and in order


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

## 🛠️ Supported Agent Frameworks

Pebbling is tested and integrated with popular agent frameworks:

- ✅ [Agno](https://github.com/agno-ai/agno)
- 🔜 CrewAI (Coming soon)
- 🔜 AutoGen (Coming soon)
- 🔜 LangChain (Coming soon)
- 🔜 LlamaIndex (Coming soon)

Want integration with your favorite framework? Let us know on [Discord](https://discord.gg/Fr6rcRJa)!

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

## 👥 Maintainers

For more details about maintainership, including how to become a maintainer, see our [MAINTAINERS.md](MAINTAINERS.md) file.

## 📜 License

Pebbling is proudly open-source and licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

## 💻 Example Use Cases

Pebbling is ideal for:

- **Multi-Agent Collaboration**: Enable efficient, secure teamwork between LLM-driven agents.
- **Decentralized Autonomous Systems**: Build reliable decentralized AI networks.
- **Secure Agent Ecosystems**: Create ecosystems where agents from different providers interact seamlessly.
- **Distributed AI Workflows**: Coordinate agents across distributed computing environments.

## 🎉 Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos — your contributions make Pebbling better.

- Join our [Discord](https://discord.gg/Fr6rcRJa) for discussions and support
- Star the repository if you find it useful!

## 🚧 Roadmap

Here's what's next for pebbling:

- [ ] GRPC transport support
- [ ] Integration with [Hibiscus](https://github.com/Pebbling-ai/hibiscus) (DiD - Decentralized Identifiers, mTLS)
- [ ] Detailed tutorials and guides
- [ ] Expanded multi-framework support

Suggest features or contribute by joining our [Discord](https://discord.gg/Fr6rcRJa)!

## 📋 FAQ

**Can Pebble be deployed locally?**
Yes! Pebble supports local development as well as cloud-based deployments.

**Does Pebble support other languages besides Python?**
Absolutely! Any language that can implement JSON-RPC and mTLS is compatible.

**How scalable is Pebble?**
Pebble's minimal dependencies and protocol simplicity ensure scalability across complex agent ecosystems.

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Pebbling-ai/pebble&type=Date)](https://star-history.com/#Pebbling-ai/pebble&Date)


Built with ❤️ by the Pebbling team from Amsterdam 🌷.

We’re excited to see what you’ll build with Pebble! Our dream is a world where agents across the internet communicate securely, openly, and effortlessly.

Have questions, ideas, or just want to chat? Join our Discord community— we’d love to hear from you! Together, let’s lay the foundation for the next generation of AI agent collaboration.

Happy Pebbling! 🐧🚀✨
