<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>The identity, communication & payments layer for AI agents</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/dm/bindu" alt="PyPI Downloads"></a>
  <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
  <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
</p>

<p align="center">
  <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://docs.getbindu.com"><img src="https://img.shields.io/badge/Documentation-📕-blue" alt="Documentation"></a>
  <a href="https://github.com/getbindu/Bindu/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
  <a href="https://github.com/getbindu/Bindu/stargazers"><img src="https://img.shields.io/github/stars/getbindu/Bindu" alt="GitHub stars"></a>
</p>

---

**Bindu** (read: _binduu_) is an operating layer for AI agents that provides identity, communication, and payment capabilities. It delivers a production-ready service with a convenient API to connect, authenticate, and orchestrate agents across distributed systems using open protocols: **A2A**, **AP2**, and **X402**.

Built with a distributed architecture (Task Manager, scheduler, storage), Bindu makes it fast to develop and easy to integrate with any AI framework. Transform any agent framework into a fully interoperable service for communication, collaboration, and commerce in the Internet of Agents.

**🌟 [Register your agent](https://bindus.directory) • 📚 [Documentation](https://docs.getbindu.com) • 💬 [Discord Community](https://discord.gg/3w5zuYUuwt)**

### 🎥 Watch Bindu in Action

<a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
  <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</a>


## 📋 Prerequisites

Before installing Bindu, ensure you have:

- **Python 3.12 or higher** - [Download here](https://www.python.org/downloads/)
- **UV package manager** - [Installation guide](https://github.com/astral-sh/uv)
- **Git** - [Download here](https://git-scm.com/downloads)

### Verify Your Setup

```bash
# Check Python version
python --version  # Should show 3.12 or higher

# Check UV installation
uv --version

# Check Git
git --version
```

### Windows Users

If you're on Windows, we recommend using **PowerShell** (not CMD) for all commands.

---

## � Installation

```bash
# Create and activate virtual environment (recommended)
uv venv --python 3.12.9
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

# Install Bindu
uv add bindu

# For development (if contributing to Bindu)
uv sync --dev
```

### Common Installation Issues

| Issue | Solution |
|-------|----------|
| `uv: command not found` | Restart your terminal after installing UV. On Windows, use PowerShell |
| `Python version not supported` | Install Python 3.12+ from [python.org](https://www.python.org/downloads/) |
| Virtual environment not activating (Windows) | Use PowerShell and run `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Download [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activate venv and run `uv sync --dev` |

---

## 🚀 Quick Start

### Option 1: Using Cookiecutter (Recommended)

**Time to first agent: ~2 minutes ⏱️**

```bash
# Install cookiecutter
uv add cookiecutter

# Create your Bindu agent
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

That's it! Your local agent becomes a live, secure, discoverable service. [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

### Option 2: Manual Setup

Create your agent script `my_agent.py`:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy it
bindufy(config, handler)
```

Your agent is now live at `http://localhost:3773` and ready to communicate with other agents.

### Option 3: Minimal Echo Agent (Testing)

> **⚠️ Note:** Bindu uses PostgreSQL by default. Ensure PostgreSQL is running locally or via Docker, or configure an in-memory storage backend for testing.

Smallest possible working agent:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**Run and test:**

```bash
# Start the agent
python examples/echo_agent.py

# Test it
curl -X POST http://localhost:3773/messages \
  -H "Content-Type: application/json" \
  -d '[{"role": "user", "content": "Hello Bindu!"}]'

# Expected response: "Hello Bindu!"
```

---

## � Examples

### Echo Agent

```bash
python examples/echo_agent.py
```

Echoes back any message sent to it. Useful for verifying your setup.

### Summarizer Agent

```bash
python examples/summarizer_agent.py
```

**Test it:**

```bash
curl -X POST http://localhost:3773/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "Artificial intelligence is a branch of computer science focused on building systems capable of performing tasks that typically require human intelligence, such as reasoning, learning, and understanding language."}'

# Response: {"summary": "Artificial intelligence focuses on creating systems that can perform tasks requiring human-like intelligence."}
```

---

## 🎨 Chat UI

Bindu includes a beautiful chat interface at `http://localhost:3773/docs`

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Python 3.12 not found` | Install Python 3.12+ and set in PATH, or use `pyenv` |
| `bindu: command not found` | Activate virtual environment: `source .venv/bin/activate` |
| `Port 3773 already in use` | Change port in config: `"url": "http://localhost:4000"` |
| Pre-commit fails | Run `pre-commit run --all-files` |
| Tests fail | Install dev dependencies: `uv sync --dev` |
| `Permission denied` (macOS) | Run `xattr -cr .` to clear extended attributes |

**Reset environment:**
```bash
rm -rf .venv
uv venv --python 3.12.9
uv sync --dev
```

**Windows PowerShell:**
```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🌌 The Vision

```
a peek into the night sky
}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}
{{            +             +                  +   @          {{
}}   |                *           o     +                .    }}
{{  -O-    o               .               .          +       {{
}}   |                    _,.-----.,_         o    |          }}
{{           +    *    .-'.         .'-.          -O-         {{
}}      *            .'.-'   .---.   `'.'.         |     *    }}
{{ .                /_.-'   /     \   .'-.\.                   {{
}}         ' -=*<  |-._.-  |   @   |   '-._|  >*=-    .     + }}
{{ -- )--           \`-.    \     /    .-'/                   }}
}}       *     +     `.'.    '---'    .'.'    +       o       }}
{{                  .  '-._         _.-'  .                   }}
}}         |               `~~~~~~~`       - --===D       @   }}
{{   o    -O-      *   .                  *        +          {{
}}         |                      +         .            +    }}
{{ jgs          .     @      o                        *       {{
}}       o                          *          o           .  }}
{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
```

_Each symbol is an agent — a spark of intelligence. The tiny dot is Bindu, the origin point in the Internet of Agents._

### NightSky Connection [In Progress]

NightSky enables swarms of agents. Each Bindu is a dot annotating agents with the shared language of A2A, AP2, and X402. Agents can be hosted anywhere—laptops, clouds, or clusters—yet speak the same protocol, trust each other by design, and work together as a single, distributed mind.

**A Goal Without a Plan Is Just a Wish.**

---

## 🛠️ Supported Agent Frameworks

Bindu is **framework-agnostic** and tested with:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Want integration with your favorite framework? [Let us know on Discord](https://discord.gg/3w5zuYUuwt)!

---

## 🧪 Testing

Bindu maintains **70%+ test coverage**:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

## 🤝 Contributing

We welcome contributions!

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

📖 [Contributing Guidelines](.github/contributing.md) • 👥 [Maintainers](maintainers.md)

---

## 📜 License

Bindu is open-source under the [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

## 💬 Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos—your contributions make Bindu better.

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) for discussions and support
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) if you find it useful!

---

## 🙏 Acknowledgements

Grateful to these projects:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

## 🗺️ Roadmap

- [ ] GRPC transport support
- [ ] Sentry error tracking
- [ ] Ag-UI integration
- [ ] Retry mechanism
- [ ] Increase test coverage to 80%
- [ ] Redis scheduler implementation
- [ ] Postgres database for memory storage
- [ ] Authentication support (AuthKit, GitHub, AWS Cognito, Google, Azure)
- [ ] Negotiation support
- [ ] AP2 end-to-end support
- [ ] DSPy integration
- [ ] MLTS support
- [ ] X402 support with other facilitators

[Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

## 🎓 Workshops

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Built with 💛 by the team from Amsterdam 🌷</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>From idea to Internet of Agents in 2 minutes.</strong><br/>
  <em>Your agent. Your framework. Universal protocols.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Star us on GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Join Discord</a> •
  <a href="https://docs.getbindu.com">📚 Read the Docs</a>
</p>
