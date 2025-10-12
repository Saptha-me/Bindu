<p align="center">
  <img src="assets/bindu-logo.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center"> Bindu 🌻</h1>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Hits](https://hits.sh/github.com/Saptha-me/Bindu.svg?style=flat-square&label=Hits%20%F0%9F%90%A7&extraCount=100&color=dfb317)](https://hits.sh/github.com/Saptha-me/Bindu/)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Saptha-me/Bindu/actions/workflows/release.yml/badge.svg)](https://github.com/Saptha-me/Bindu/actions/workflows/release.yml)
[![Coverage Status](https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.1.0.5)](https://coveralls.io/github/Saptha-me/Bindu?branch=v0.1.0.5)
[![PyPI version](https://badge.fury.io/py/bindu.svg)](https://badge.fury.io/py/bindu)
[![PyPI Downloads](https://img.shields.io/pypi/dm/bindu)](https://pypi.org/project/bindu/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Saptha-me/Bindu/pulls)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/Fr6rcRJa)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.saptha.me)
[![GitHub stars](https://img.shields.io/github/stars/Saptha-me/Bindu)](https://github.com/Saptha-me/Bindu/stargazers)

We imagine world of agents where they can communicate with each other seamlessly.
and Bindu turns your agent into a living server - the dot(Bindu) in the Internet of Agents. 

# The Idea

The integration was the problem and still is the problem in the world.
We built monoliths, then APIs, then microservices, then cloud functions.
Then after the 30th November, 2022, we have arrived the age of LLMs.
Large language models started reasoning, planning, and calling tools.
And suddenly, software wasn’t just executing, it was thinking.

But the problem was still the same.

We do have now the language protocol for communication between agents.A2A, AP2, x402. 

How do we connect them?

Thats why Bindu is here.

Bindu is a python package that helps you turn your agent into a living server that can talk with other agents, microservices in the language of A2A, AP2, x402.


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

Each symbol is an agent - the Bindu, Dot in the Internet of Agents.



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

🌻 Welcome to bindu — powered by the bindu CLI.
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

**Can bindu be deployed locally?**
Yes! bindu supports local development as well as cloud-based deployments.

## Security:
curl --request POST \
  --url https://dev-tlzrol0zsxw40ujx.us.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{"client_id":"GGLemeiKL6MfXD7Hy4L4mtz8WNIhRtkS","client_secret":"zXcdPIQRAM9iHzABZtcfaN_2iICW4pfuoyUChIcVDF5488ejtyKG_U_PyWj9kpJT","audience":"https://dev-tlzrol0zsxw40ujx.us.auth0.com/api/v2/","grant_type":"client_credentials"}' \
  | jq -r '.access_token'


  Standard JSON-RPC (-32700 to -32603)
├─ -32700: Parse error
├─ -32600: Invalid Request
├─ -32601: Method not found
├─ -32602: Invalid params
└─ -32603: Internal error

A2A Official (-32001 to -32007)
├─ -32001: TaskNotFoundError ✅
├─ -32002: TaskNotCancelableError ✅
├─ -32003: PushNotificationNotSupportedError ✅
├─ -32004: UnsupportedOperationError ✅
├─ -32005: ContentTypeNotSupportedError ✅
├─ -32006: InvalidAgentResponseError ✅
└─ -32007: AuthenticatedExtendedCardNotConfiguredError ✅

Bindu Extensions (-32008 to -32099)
├─ -32008: TaskImmutableError (custom)
├─ -32009 to -32013: Authentication errors
└─ -32020 to -32021: Context errors


## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=bindu-ai/pebble&type=Date)](https://star-history.com/#bindu-ai/pebble&Date)


Built with ❤️ by the bindu team from Amsterdam 🌷.

Happy bindu! 🌻🚀✨
