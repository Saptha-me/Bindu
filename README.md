<p align="center">
  <img src="assets/bindu-logo.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center"> Bindu 🌻</h1>

<p align="center">
  <em>“We imagine a world of agents where they can communicate with each other seamlessly.<br/>
  And Bindu turns your agent into a living server , the dot (Bindu) in the Internet of Agents.”</em>
</p>

<br/>

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Hits](https://hits.sh/github.com/Saptha-me/Bindu.svg?style=flat-square&label=Hits%20%F0%9F%90%A7&extraCount=100&color=dfb317)](https://hits.sh/github.com/Saptha-me/Bindu/)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Saptha-me/Bindu/actions/workflows/release.yml/badge.svg)](https://github.com/Saptha-me/Bindu/actions/workflows/release.yml)
[![Coverage Status](https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.1.0.5)](https://coveralls.io/github/Saptha-me/Bindu?branch=v0.1.0.5)
[![PyPI version](https://badge.fury.io/py/bindu.svg)](https://badge.fury.io/py/bindu)
[![PyPI Downloads](https://img.shields.io/pypi/dm/bindu)](https://pypi.org/project/bindu/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Saptha-me/Bindu/pulls)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/3w5zuYUuwt)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.saptha.me)
[![GitHub stars](https://img.shields.io/github/stars/Saptha-me/Bindu)](https://github.com/Saptha-me/Bindu/stargazers)


# 🌌 The Idea

Integration was the problem.
And even today, it still is.

We built monoliths, then <b>APIs</b>, then <b>microservices</b>, then <b>cloud functions</b>.<br/>
Each step made systems faster, smaller, and more distributed.

Then, on <b>30th November 2022</b>, something changed.<br/>
We entered the age of <b>Large Language Models</b>.<br/>
Software began reasoning, planning, and calling tools.<br/>
Suddenly, our code didn’t just execute, it <b>thought</b>.

But the old problem stayed the same.<br/>
<b>Connection.</b>

Now we have the language protocols for this new world:<br/>
[A2A](https://github.com/a2aproject/A2A), [AP2](https://github.com/google-agentic-commerce/AP2), and [X402](https://github.com/coinbase/x402) — ways for agents to talk, trust, and trade.<br/>

Yet, connecting them still takes time, code, and complexity.

That’s why <b>Bindu exists.</b>

<b>Bindu</b> is a Python package that turns your agent into a <b>living server</b>.One that can speak the language of <b>A2A, AP2, and X402</b>,
And communicate with other agents and microservices across the open web.

Just write your agent in any framework you like, then use <b>Bindu</b>.
it will <b>Bindu-fy</b> your agent so that it can instantly join the Internet of Agents.


## Installation

```bash
# Using uv (recommended)
uv add bindu
```


## 🚀 Quick Start

### Quick Start with Cookiecutter Template

The fastest way to get started with bindu is using our cookiecutter template:

```bash
# Create a new bindu project
uv tool run cookiecutter cookiecutter-bindu/
```

That’s it.
Your local agent becomes a live, secure, discoverable service, ready to talk with other agents anywhere.

### Manual Setup - Create Your First Agent

**Step 1:** Create a configuration file `agent_config.json`:

```json
{
  "author": "your.email@example.com",
  "name": "my_first_agent",
  "description": "A simple agent that answers questions",
  "version": "1.0.0",
  "deployment": {
    "url": "http://localhost:8030",
    "expose": true
  }
}
```
Full Detailed Configuration can be found [here](https://docs.saptha.me).

**Step 2:** Create your agent script `my_agent.py`:

```python
from bindu import bindufy

from agno.agent import Agent
from agno.models.openai import OpenAIChat

from bindu.penguin.bindufy import bindufy


# Load configuration
def load_config(config_path: str):
    """Load configuration from JSON with defaults."""
    full_path = os.path.join(config_path)
    with open(full_path, "r") as f:
        return json.load(f)


simple_config = load_config("simple_agent_config.json")
simple_agent = Agent(
    instructions="Provide helpful responses to user messages",
    model=OpenAIChat(id="gpt-4o"),
)

def simple_handler(messages: list[dict[str, str]]) -> Any:
    result = simple_agent.run(input=messages)
    return result

bindufy(simple_agent, simple_config, simple_handler)
```

That's it! Your agent is now live at `http://localhost:8030` and ready to communicate with other agents.


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



# The Saptha.me Connection

Saptha.me is the layer that makes swarms of agents.

In this swarm, each Bindu is a dot - annotating agents with the shared language of A2A, AP2, and X402.

Agents can be hosted anywhere — on laptops, clouds, or clusters — yet speak the same protocol, trust each other by design,
and work together as a single, distributed mind.

Saptha gives them the seven layers of connection — mind, memory, trust, task, identity, value, and flow —
that’s why it’s called Saptha.me.
(Saptha, meaning “seven”; me, the self-aware network.)



## 🛠️ Supported Agent Frameworks

Bindu is Agent Framework agnostic.

We did test with mainly Agno, CrewAI, LangChain, and LlamaIndex, FastAgent.

Want integration with your favorite framework? Let us know on [Discord](https://discord.gg/Fr6rcRJa)!


## Testing

bindu is thoroughly tested with a test coverage of over 70%:

```bash
# Run tests with coverage
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# Clone the repository
git clone https://github.com/Saptha-me/Bindu.git
cd Bindu

# Install development dependencies
uv sync --dev

# Install pre-commit hooks
pre-commit run --all-files
```

Please see our [Contributing Guidelines](.github/CONTRIBUTING.md) for more details.

## Maintainers

For more details about maintainership, including how to become a maintainer, see our [MAINTAINERS.md](MAINTAINERS.md) file.

## License

Bindu is proudly open-source and licensed under the [MIT License](https://choosealicense.com/licenses/mit/).


## Community

We 💛 contributions! Whether you're fixing bugs, improving documentation, or building demos — your contributions make bindu better.

- Join our [Discord](https://discord.gg/3w5zuYUuwt) for discussions and support
- Star the repository if you find it useful!

## Roadmap

Here's what's next for bindu:

- [ ] GRPC transport support
- [ ] Static Webpage Beautification.
- [ ] Increase Test Coverage to 80%.
- [ ] Redis Scheduler Implementation.
- [ ] Postgres Database Implementation for Memory Storage.
- [ ] Authentication Support AuthKit, GitHub, AWS Cognito, Google, Azure (Microsoft Entra).
- [ ] Negotiation Support.
- [ ] AP2 End to End Support.
- [ ] X402 Support with other facilitators.


Suggest features or contribute by joining our [Discord](https://discord.gg/3w5zuYUuwt)!


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Saptha-me/Bindu&type=Date)](https://www.star-history.com/#Saptha-me/Bindu&Date)


Built with ❤️ by the team from Amsterdam 🌷.

Happy Bindu! 🌻🚀✨
