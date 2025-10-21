<p align="center">
  <img src="assets/light.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center"> Bindu 🌻</h1>

<p align="center">
  <em>“We imagine a world of agents where they can communicate with each other seamlessly.<br/>
  And Bindu turns your agent into a living server , the dot (Bindu) in the Internet of Agents.”</em>
</p>

<br/>

[![GitHub License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Hits](https://hits.sh/github.com/Saptha-me/Bindu.svg)](https://hits.sh/github.com/Saptha-me/Bindu/)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/Saptha-me/Bindu/actions/workflows/release.yml/badge.svg)](https://github.com/Saptha-me/Bindu/actions/workflows/release.yml)
[![PyPI version](https://badge.fury.io/py/bindu.svg?icon=si%3Apython&icon_color=%23fffc41)](https://badge.fury.io/py/bindu)
[![PyPI Downloads](https://img.shields.io/pypi/dm/bindu)](https://pypi.org/project/bindu/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/Saptha-me/Bindu/pulls)
[![Join Discord](https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white)](https://discord.gg/3w5zuYUuwt)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.saptha.me)
[![GitHub stars](https://img.shields.io/github/stars/Saptha-me/Bindu)](https://github.com/Saptha-me/Bindu/stargazers)

<br/>

# The Idea

Integration was the problem.
And even today, it still is.

We built monoliths, then <b>APIs</b>, then <b>microservices</b>, then <b>cloud functions</b>.<br/>
Each step made systems faster, smaller, and more distributed.

Then, on <b>30th November 2022</b>, something changed.<br/>
We entered the age of <b>Large Language Models</b>.<br/>
Software began reasoning, planning, and calling tools.<br/>
Suddenly, our code didn’t just execute, it started <b>thinking</b>.

But the old problem stayed the same.<br/>

<b>Connection.</b>

Now we have the language protocols for this new world:<br/>
[A2A](https://github.com/a2aproject/A2A), [AP2](https://github.com/google-agentic-commerce/AP2), and [X402](https://github.com/coinbase/x402), how the agents talk, trust, and trade.<br/>

Yet, connecting them still takes time, code, and complexity.

That’s why <b>Bindu exists.</b>

<b>Bindu</b> is a wrapper that turns your agent into a A2A, AP2, and X402 schema-compliant <b>living server</b>,
And communicate with other agents and microservices across the open web.

Just write your agent in any framework you like, then use <b>Bindu</b>.
it will <b>Bindu-fy</b> your agent so that it can instantly join the Internet of Agents.

<br/>

## Installation

```bash
# Using uv (recommended)
uv add bindu
```

<br/>

## 🚀 Quick Start

### Quick Start with Cookiecutter Template

The fastest way to get started with bindu is using our cookiecutter template:

```bash
# Create a new bindu project
uv tool run cookiecutter cookiecutter-bindu/
```

<br/>

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

<br/>

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

# The Saptha.me Connection [In Progress]

Saptha.me is the layer that makes swarms of agents.

In this swarm, each Bindu is a dot - annotating agents with the shared language of A2A, AP2, and X402.

Agents can be hosted anywhere — on laptops, clouds, or clusters — yet speak the same protocol, trust each other by design,
and work together as a single, distributed mind.

**A Goal Without a Plan Is Just a Wish**.
So Saptha.me takes care <b>Research, Plan and Implement</b>.

Saptha.me gives them the seven layers of connection — mind, memory, trust, task, identity, value, and flow —
that’s why it’s called Saptha.me.
(Saptha, meaning “seven”; me, the self-aware network.)

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
git clone https://github.com/Saptha-me/Bindu.git
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

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Saptha-me/Bindu&type=Date)](https://www.star-history.com/#Saptha-me/Bindu&Date)


Built with ❤️ by the team from Amsterdam 🌷.

Happy Bindu! 🌻🚀✨
