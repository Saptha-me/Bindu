<p align="center">
  <img src="assets/bindu-logo.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center">bindu: Agent-to-Agent Communication </h1>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Hits](https://hits.sh/github.com/bindu-ai/pebble.svg?style=flat-square&label=Hits%20%F0%9F%90%A7&extraCount=100&color=dfb317)](https://hits.sh/github.com/bindu-ai/pebble/)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/bindu-ai/pebble/actions/workflows/release.yml/badge.svg)](https://github.com/bindu-ai/pebble/actions/workflows/release.yml)
[![Coverage Status](https://coveralls.io/repos/github/bindu-ai/pebble/badge.svg?branch=v0.1.0.5)](https://coveralls.io/github/bindu-ai/pebble?branch=v0.1.0.5)
[![PyPI version](https://badge.fury.io/py/bindu.svg)](https://badge.fury.io/py/bindu)
[![PyPI Downloads](https://img.shields.io/pypi/dm/bindu)](https://pypi.org/project/bindu/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/bindu-ai/pebble/pulls)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/Fr6rcRJa)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.bindu.ai)
[![GitHub stars](https://img.shields.io/github/stars/bindu-ai/pebble)](https://github.com/bindu-ai/pebble/stargazers)

✨ Imagine a world where AI agents collaborate effortlessly and securely—no passport 🚫, no boundaries 🌐.

That’s bindu 🌻.An open source, secured protocol for agent-to-agent communication.

🚀 Powered by Decentralised Identifiers (DIDs) 🔑, secured conversations with mutual TLS (mTLS) 🔒, and a lightweight yet powerful communication protocol built on JSON-RPC 2.0 ⚡️—bindu is paving the way for the next generation of collaborative AI systems. 🌟🤖


## 🌟 Features

bindu helps your AI agents talk to each other seamlessly:

🔒 **Super Secure** - Your agents exchange secrets safely (with built-in mTLS)

🧩 **Plug-and-Play** - Just decorate your agent and it's ready to communicate

⚡ **Lightning Fast** - Quick connections without the weight

🌐 **Works Everywhere** - Connect any agents, regardless of their programming language

🔄 **Reliable Communication** - Messages always arrive correctly and in order


## 📦 Installation

```bash
# Using pip
pip install bindu

# Using uv (recommended)
uv add bindu
```

## 🚀 Quick Start

### 🍪 Quick Start with Cookiecutter Template

The fastest way to get started with bindu is using our cookiecutter template:

```bash
# Create a new bindu project
uv tool run cookiecutter cookiecutter-bindu/
```

Follow the interactive prompts:
```
[1/4] name (pebble_project): my_weather_agent
[2/4] description (): A weather forecasting agent
[3/4] bindu_email (): your.email@example.com
[4/4] Select agent_framework
  1 - none
  2 - agno
  3 - crew
  4 - langchain
  Choose from [1/2/3/4] (1): 2
```

After project creation:
```bash
🎉 Project created successfully!

🌻 Welcome to bindu — powered by the Pebble CLI.
Next steps:
  1️⃣  cd 'my_weather_agent'
  2️⃣  Set it up using uv: 📦
      uv sync
  3️⃣  Run your agent locally: 💻
      PYTHONPATH=src python3 -m my_weather_agent
      or
      python3 src/<filename.py>
  4️⃣  Deploy your agent: 🚀
      pebble launch

🤖 Selected agent framework: agno
Need help? See README.md for details. ✨
```

**Setup and run your agent:**
```bash
# Navigate to your project
cd my_weather_agent

# Create virtual environment
uv venv --python 3.12.9
source .venv/bin/activate

# Install dependencies
uv sync

# Run your agent
uv run src/pebble_agent.py
```

Your agent will start with full bindu capabilities:
- ✅ Automatic DID identity generation
- ✅ Security setup with mTLS certificates
- ✅ Agent manifest creation
- ✅ Local server running on http://localhost:8030
- ✅ OpenInference observability integration

> 📂 **Template Repository**: [cookiecutter-bindu](https://github.com/bindu-ai/cookiecutter-bindu)

### Manual Setup - bindufy an Agent

```python
from bindu import bindufy

@bindufy(name="My Agent", description="A simple agent", version="1.0.0")
def my_agent(message: str) -> str:
    return "Hello, Agent!"

# You're now ready to communicate securely between agents!
```

### bindufy a [Agno](https://github.com/agno-ai/agno) Agent

```python
from bindu import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat

@bindufy(name="Agno Agent", description="A helpful assistant", version="1.0.0")
def agno_agent(message: str) -> str:
    agent = Agent(
        model=OpenAIChat(id="gpt-4o"),
        instructions="You are a helpful assistant.",
    )
    result = agent.run(message)
    return result.to_dict()["content"]

# You're now ready to communicate securely between agents!
```

## 🎥 Agent in Action
<img src="./pebble-cli.gif" alt="Agent Demo" width="640">

## 📊 Interactive Diagrams

<table>
<tr>
<td>

**🔄 Sequence Diagram**
[![View Interactive Diagram](https://img.shields.io/badge/View%20Interactive%20Diagram-📊-blue?style=for-the-badge)](https://www.mermaidchart.com/app/projects/818fccf7-4d32-4f82-8a5f-006808d90e34/diagrams/89f06b06-fe7c-4c8f-ab91-20eb0146fc0f/version/v0.1/edit)

Open the interactive version of this sequence diagram in MermaidChart

</td>
<td>

**🏗️ Orchestration Diagram**
[![View Interactive Diagram](https://img.shields.io/badge/View%20Interactive%20Diagram-📊-green?style=for-the-badge)](https://www.mermaidchart.com/app/projects/818fccf7-4d32-4f82-8a5f-006808d90e34/diagrams/143c8f38-3810-4404-898c-cceb59b39670/version/v0.1/edit)

Open the interactive version of this orchestration diagram in MermaidChart

</td>
</tr>
</table>

## 🛠️ Supported Agent Frameworks

bindu is tested and integrated with popular agent frameworks:

- ✅ [Agno](https://github.com/agno-ai/agno)
- 🔜 CrewAI (Coming soon)
- 🔜 AutoGen (Coming soon)
- 🔜 LangChain (Coming soon)
- 🔜 LlamaIndex (Coming soon)

Want integration with your favorite framework? Let us know on [Discord](https://discord.gg/Fr6rcRJa)!

## 📖 Documentation

For comprehensive documentation, visit [docs.bindu.ai](https://docs.bindu.ai)

## 🧪 Testing

bindu is thoroughly tested with a test coverage of over 83%:

```bash
# Run tests with coverage
make test
make coverage
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# Clone the repository
git clone https://github.com/bindu-ai/pebble.git
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

bindu is proudly open-source and licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

## 💻 Example Use Cases

bindu is ideal for:

- **Multi-Agent Collaboration**: Enable efficient, secure teamwork between LLM-driven agents.
- **Decentralized Autonomous Systems**: Build reliable decentralized AI networks.
- **Secure Agent Ecosystems**: Create ecosystems where agents from different providers interact seamlessly.
- **Distributed AI Workflows**: Coordinate agents across distributed computing environments.

## 🎉 Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos — your contributions make bindu better.

- Join our [Discord](https://discord.gg/Fr6rcRJa) for discussions and support
- Star the repository if you find it useful!

## 🚧 Roadmap

Here's what's next for bindu:

- [ ] GRPC transport support
- [ ] Integration with [Hibiscus](https://github.com/bindu-ai/hibiscus) (DiD - Decentralized Identifiers, mTLS)
- [ ] Detailed tutorials and guides
- [ ] Expanded multi-framework support

Suggest features or contribute by joining our [Discord](https://discord.gg/Fr6rcRJa)!

## FAQ

**Can Pebble be deployed locally?**
Yes! Pebble supports local development as well as cloud-based deployments.

**Does Pebble support other languages besides Python?**
Absolutely! Any language that can implement JSON-RPC and mTLS is compatible.

**How scalable is Pebble?**
Pebble's minimal dependencies and protocol simplicity ensure scalability across complex agent ecosystems.

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=bindu-ai/pebble&type=Date)](https://star-history.com/#bindu-ai/pebble&Date)


Built with ❤️ by the bindu team from Amsterdam 🌷.

We’re excited to see what you’ll build with Pebble! Our dream is a world where agents across the internet communicate securely, openly, and effortlessly.

Have questions, ideas, or just want to chat? Join our Discord community— we’d love to hear from you! Together, let’s lay the foundation for the next generation of AI agent collaboration.

Happy bindu! 🌻🚀✨
