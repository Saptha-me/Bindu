<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<br/>

<p align="center">
  <em>The identity, communication & payments layer for AI agents. Dreaming of a world where agents gossip, argue & collaborate like a real society of their own.</em>
</p>

<br/>

[![GitHub License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Hits](https://hits.sh/github.com/Saptha-me/Bindu.svg)](https://hits.sh/github.com/Saptha-me/Bindu/)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Coverage Status](https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18)](https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18)
[![Tests](https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg)](https://github.com/getbindu/Bindu/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/bindu.svg)](https://pypi.org/project/bindu/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/bindu)](https://pypi.org/project/bindu/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/getbindu/Bindu/pulls)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/3w5zuYUuwt)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.getbindu.com)
[![GitHub stars](https://img.shields.io/github/stars/getbindu/Bindu)](https://github.com/getbindu/Bindu/stargazers)

<br/>

## Demo

Watch a short walkthrough of Bindu in action:

<a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
  <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg"
       alt="Bindu Demo"
       width="640"
       style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</a>


# What is Bindu 🌻

Modern agents can reason, plan, and call tools, but connecting them to each other and to existing systems is still hard. We now have open protocols for this new world: A2A, AP2, and X402. They define how agents talk, trust, and trade yet wiring them together still takes time, code, and complexity.

<b>Bindu solves this.</b>

Bindu is an operating layer that adds auth, payments, observability, distributed execution, and low latency on top of A2A, AP2, and X402, turning your agent into a decentralized, interoperable living server that speaks the language of the open web.

Write your agent in <b>any framework</b> you like, then use Bindu to <code>"Bindu‑fy"</code> it and plug directly into the Internet of Agents.

Bring your agent and a simple config - that's it. We take care of the rest.

<p align="center">
  <img src="assets/agno-simple.png" alt="Bindu" width="640"
       style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

<br/>

## Installation

```bash
# Using uv (recommended)
uv add bindu
```

<br/>

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

## 🐛 Common Installation Issues

### Issue: "uv: command not found"
**Solution:**
- Restart your terminal after installing UV
- On Windows, make sure you used PowerShell for installation

### Issue: "Python version not supported"
**Solution:**
- Install Python 3.12+ from [python.org](https://www.python.org/downloads/)
- Verify with: `python --version`

### Issue: Virtual environment not activating on Windows
**Solution:**
- Use PowerShell (not CMD)
- Run: `.venv\Scripts\activate`
- You should see `(.venv)` at the start of your prompt

### Issue: Installation fails with "Microsoft Visual C++ required"
**Solution:**
- Download Visual C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- Or use: `uv pip install -e .` for core installation only

### Issue: ModuleNotFoundError after installation
**Solution:**
```bash
# Make sure virtual environment is activated
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Reinstall dependencies
uv sync --dev
```

<br/>

## 🚀 Quick Start

### Time to first agent: ~2 minutes ⏱️

On your local machine, navigate to the directory in which you want to
create a project directory, and run the following command:

```bash
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

More details can be found [here](https://docs.getbindu.com/bindu/create-bindu-agent/overview).
<br/>

That's it.
Your local agent becomes a live, secure, discoverable service, ready to talk with other agents anywhere.

### Manual Setup - Create Your First Agent

**Step 1:** Create a configuration file `agent_config.json`:

```json
{
  "author": "raahul@getbindu.com",
  "name": "research_agent",
  "description": "A research assistant agent",
  "deployment": {"url": "http://localhost:3773", "expose": True},
  "skills": ["skills/question-answering", "skills/pdf-processing"]
}
```
Full Detailed Configuration can be found [here](https://docs.getbindu.com).

**Step 2:** Create your agent script `my_agent.py`:

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
    "skills": ["skills/question-answering", "skills/pdf-processing"],
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

That's it! Your agent is now live at `http://localhost:3773` and ready to communicate with other agents.

<br/>

## Minimal Agent Example (Echo Agent) — sanity check

If you want to test Bindu locally without tools or external dependencies, here is the smallest possible working agent:

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
Run:
```
python examples/echo_agent.py
```
Test the agent with any message:
```
curl -X POST http://localhost:3773/messages \
-H "Content-Type: application/json" \
-d '[{"role": "user", "content": "Hello Bindu!"}]'
```
Expected response:
```
"Hello Bindu!"
```
## Summarizer Agent Example

This example shows how to build a more practical Bindu agent that transforms text.
It takes long input from the user and returns a concise summary.

```bash
python examples/summarizer_agent.py
```
Test using cURL:

```bash
curl -X POST http://localhost:3774/messages \
     -H "Content-Type: application/json" \
     -d '[{"role": "user", "content": "Provide a summary of the following text... <long input>"}]'
```
Expected response (example):

```bash
The text is summarized into 2–3 sentences focusing on key points.
```

## 🎨 Chat UI (Optional)

Want a beautiful chat interface for your agent? - It's available as part of the Bindu ecosystem. - https://localhost:3773/docs

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640"
       style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

<br/>

## 🔧 Troubleshooting

Here are some common setup issues and their fixes to help you get up and running quickly:

| Issue | Cause | Solution |
|-------|--------|----------|
| `Python 3.12 not found` | System default Python is lower than 3.12 | Install Python 3.12 and set it in PATH, or use `pyenv` to manage versions |
| `bindu: command not found` or import errors | Virtual environment not activated | Activate venv before running: `.venv/Scripts/activate` (Windows) or `source .venv/bin/activate` (macOS/Linux) |
| `Port 3773 already in use` | Another service is running on that port | Change the `url` field in `config` to a different port, e.g. `"url": "http://localhost:4000"` |
| Pre-commit fails during commit | Code format / lint checks not applied | Run `pre-commit run --all-files` after initial install |
| Tests fail with missing dependencies | Dev packages not installed | Install with: `uv sync --dev` (not only `pip install bindu`) |
| Cookiecutter install error | Cookiecutter not found | Install with `uv add cookiecutter` or `pip install cookiecutter` |

### Additional Tips
- If the agent starts but does not respond, re-create the venv and reinstall dependencies:
```bash
  rm -rf .venv
  uv venv --python 3.12.9
  uv sync --dev
```
- If running on Windows PowerShell, ensure execution policy allows venv activation:
```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
This section is intended to reduce setup friction and help users quickly verify their environment is working before integrating skills, tools, or frameworks.

## The Vision

```bash
a peek into the night sky
}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}
{{            +             +                  +   @          {{
}}   |                *           o     +                .    }}
{{  -O-    o               .               .          +       {{
}}   |                    _,.-----.,_         o    |          }}
{{           +    *    .-'.         .'-.          -O-         {{
}}      *            .'.-'   .---.   `'.'.         |     *    }}
{{ .                /_.-'   /     \   .'-.\                   {{
}}         ' -=*<  |-._.-  |   @   |   '-._|  >*=-    .     + }}
{{ -- )--           \`-.    \     /    .-'/                   {{
}}       *     +     `.'.    '---'    .'.'    +       o       }}
{{                  .  '-._         _.-'  .                   {{
}}         |               `~~~~~~~`       - --===D       @   }}
{{   o    -O-      *   .                  *        +          {{
}}         |                      +         .            +    }}
{{ jgs          .     @      o                        *       {{
}}       o                          *          o           .  }}
{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
```

Each symbol is an agent — a spark of intelligence.
And the single tiny dot is Bindu, the origin point in the Internet of Agents.<br/>

<br/>

# The NightSky Connection [In Progress]

NightSky is the layer that makes swarms of agents.

In this swarm, each Bindu is a dot - annotating agents with the shared language of A2A, AP2, and X402.

Agents can be hosted anywhere on laptops, clouds, or clusters — yet speak the same protocol, trust each other by design,
and work together as a single, distributed mind.

**A Goal Without a Plan Is Just a Wish**.

<br/>

## 🛠️ Supported Agent Frameworks

Bindu is Agent Framework agnostic.

We did test with mainly Agno, CrewAI, LangChain, and LlamaIndex, FastAgent.

Want integration with your favorite framework? Let us know on [Discord](https://discord.gg/3w5zuYUuwt)!

<br/>

## Testing

bindu is thoroughly tested with a test coverage of over 70%:

```bash
# Run tests with coverage
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

<br/>

## Contributing

We welcome contributions! Here's how to get started:

```bash
# Clone the repository
git clone https://github.com/getbindu/Bindu.git
cd Bindu

# Install development dependencies
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev

# Install pre-commit hooks
pre-commit run --all-files
```

Please see our [Contributing Guidelines](.github/contributing.md) for more details.

<br/>

## Maintainers

For more details about maintainers, including how to become a maintainer, see our [maintainers](maintainers.md) file.

<br/>

## License

Bindu is proudly open-source and licensed under the [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

<br/>

## Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos — your contributions make bindu better.

- Join our [Discord](https://discord.gg/3w5zuYUuwt) for discussions and support
- Star the repository if you find it useful!

<br/>

## Acknowledgements

We are grateful to the following projects for the development of bindu:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- The bindu logo : https://openmoji.org/library/emoji-1F33B/
- The Ascii Space Art : https://www.asciiart.eu/space/other#google_vignette

<br/>

## Roadmap

Here's what's next for bindu:

- [ ] GRPC transport support
- [ ] Sentry Error Tracking.
- [ ] Ag-Ui Integration.
- [ ] Retry Mechanism add.
- [ ] Increase Test Coverage to 80%.
- [ ] Redis Scheduler Implementation.
- [ ] Postgres Database Implementation for Memory Storage.
- [ ] Authentication Support AuthKit, GitHub, AWS Cognito, Google, Azure (Microsoft Entra).
- [ ] Negotiation Support.
- [ ] AP2 End to End Support.
- [ ] Dspy Addition.
- [ ] MLTS Support.
- [ ] X402 Support with other facilitators.


Suggest features or contribute by joining our [Discord](https://discord.gg/3w5zuYUuwt)!

<br/>

## Workshops

- [AI Native in Action: Agent Symphony, AI Co-Authors & A Special Book Signing!](https://www.meetup.com/ai-native-amsterdam/events/311066899/?eventOrigin=group_upcoming_events): [Google Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit?slide=id.g36905aa74c1_0_3217#slide=id.g36905aa74c1_0_3217)

#

## Star History

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
