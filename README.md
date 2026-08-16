<p align="center">
  <img src="./assets/bindu_logo.png" alt="Bindu" width="120" />
</p>

<h1 align="center">Bindu</h1>

<p align="center">
    <a href="https://www.python.org/downloads/"><img alt="Python Version" src="https://img.shields.io/badge/python-3.12+-blue.svg"></a>
    <a href="https://pypi.org/project/bindu/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/bindu.svg"></a>
    <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img alt="Coverage" src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18"></a>
    <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img alt="Tests" src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg"></a>
    <a href="https://discord.gg/3w5zuYUuwt"><img alt="Discord" src="https://img.shields.io/badge/Discord-7289DA?logo=discord&logoColor=white"></a>
    <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img alt="Contributors" src="https://img.shields.io/github/contributors/getbindu/Bindu"></a>
    <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img alt="Hits" src="https://hits.sh/github.com/Saptha-me/Bindu.svg"></a>
    <a href="https://www.star-history.com/getbindu/bindu">
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/badge?repo=GetBindu/Bindu&theme=dark" />
            <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/badge?repo=GetBindu/Bindu" />
            <img alt="Star History Rank" src="https://api.star-history.com/badge?repo=GetBindu/Bindu" />
        </picture>
    </a>
</p>

<h4 align="center">
    <p>
        <b>English</b> |
        <a href="i18n/README.de.md">Deutsch</a> |
        <a href="i18n/README.es.md">Español</a> |
        <a href="i18n/README.fr.md">Français</a> |
        <a href="i18n/README.hi.md">हिंदी</a> |
        <a href="i18n/README.bn.md">বাংলা</a> |
        <a href="i18n/README.zh.md">中文</a> |
        <a href="i18n/README.nl.md">Nederlands</a> |
        <a href="i18n/README.id.md">Bahasa Indonesia</a> |
        <a href="i18n/README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">The identity, communication, and payments layer for AI agents.</h3>

<br/>

<p align="center">
  <em>A Gmail-shaped inbox for the agent internet. Watch your agents send signed JSON-RPC to each other, verify identities inline, and reply to a swarm like it's a thread.</em>
</p>

<p align="center">
  <a href="inbox/README.md"><img src="./assets/inbox.png" alt="Bindu inbox — agents talking to agents, signatures verified inline" width="880" /></a>
</p>

<p align="center">
  <a href="inbox/README.md"><strong>→ Open the inbox walkthrough</strong></a>
</p>

<br/>

Here's the situation. You built an agent. It works. But to actually let it loose — talk to other agents, prove who it is, take money for the work — you'd be on the hook for a lot of boring plumbing. A DID library to integrate. An OAuth flow to set up. Payment middleware. An HTTP layer that follows whatever protocol the rest of the agent world is using.

Bindu is all of that plumbing, behind one function call. You wrap your handler with `bindufy()`, and a few seconds later your agent is online with its own cryptographic identity, speaking [A2A](https://github.com/a2aproject/A2A) (the protocol other agents already use), and ready to demand USDC on any EVM chain before it does any work ([x402](https://github.com/coinbase/x402)). Your handler stays as small as `(messages) -> response`. The framework inside the handler — Agno, LangChain, CrewAI, your own thing — Bindu doesn't care.

There are SDKs for Python, TypeScript, and Kotlin, and they all share the same gRPC core. The language is a choice; the protocol and identity are the same either way. When you're ready to go deeper, the [docs](https://docs.getbindu.com) are the next stop.

## Installation

You'll need Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
uv add bindu
```

If you're hacking on Bindu itself rather than using it:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

To run the examples you'll need an API key for at least one LLM provider — `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `MINIMAX_API_KEY`.

<br/>

## Quickstart

Build the agent you want, hand it to `bindufy()`, and it's online. The block below is the whole thing — copy it into a file, set your `OPENAI_API_KEY`, run it.

```python
import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

agent = Agent(
    instructions="You are a research assistant.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

config = {
    "author": "you@example.com",
    "name": "research_agent",
    "description": "Research assistant with web search.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering"],
}

def handler(messages: list[dict[str, str]]):
    return agent.run(input=messages)

bindufy(config, handler)
```

The agent is now live at `http://localhost:3773`. `expose: True` opens an FRP tunnel so the rest of the internet can hit it without you setting up port forwarding.

<details>
<summary>TypeScript equivalent</summary>

```typescript
import { bindufy } from "@bindu/sdk";
import OpenAI from "openai";

const openai = new OpenAI();

bindufy({
  author: "you@example.com",
  name: "research_agent",
  description: "Research assistant.",
  deployment: { url: "http://localhost:3773", expose: true },
  skills: ["skills/question-answering"],
}, async (messages) => {
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: messages.map(m => ({ role: m.role as "user" | "assistant" | "system", content: m.content })),
  });
  return response.choices[0].message.content || "";
});
```

The TypeScript SDK spawns the Python core in the background — you won't see it, and you don't need any Python in your own codebase. Same protocol, same DID. Full example in [`examples/typescript-openai-agent/`](examples/typescript-openai-agent/).

</details>

<details>
<summary>Calling the agent with curl</summary>

```bash
curl -X POST http://localhost:3773/ \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "id": "<uuid>",
    "params": {
      "message": {
        "role": "user",
        "kind": "message",
        "parts": [{"kind": "text", "text": "Hello"}],
        "messageId": "<uuid>",
        "contextId": "<uuid>",
        "taskId": "<uuid>"
      }
    }
  }'
```

Then poll `tasks/get` with the same `taskId` until state hits `completed`.

</details>

<br/>

## Security: three layers, on by default

Most agent frameworks treat security as your problem. Bindu treats it as transport.

When an A2A request lands on a Bindu agent, three different middlewares fire before your handler sees the body — and each one answers a question the other two cannot:

| Layer | The question it answers | What it actually is |
|---|---|---|
| **mTLS** | _Is the socket itself encrypted and mutually authenticated?_ | X.509 cert from [Smallstep step-ca](https://smallstep.com/docs/step-ca/), SAN = DID, 24-hour TTL, auto-renewed in-process |
| **OAuth2 via Hydra** | _Is the caller allowed to perform this operation right now?_ | Ed-style bearer token, ~1-hour TTL, validated via [Ory Hydra](https://www.ory.sh/hydra/) introspection |
| **DID signature** | _Was this exact JSON body authored by the DID it claims?_ | Ed25519 signature over canonical body, carried in `X-DID-Signature` |

You don't pick one. You don't bolt them on. They ship together — and on the operator's personal agent, **they're on by default as of 2026.21.1**.

Why three layers, not one? Because each fails safe in a way the others can't:

- An attacker who steals a bearer token still can't decrypt your traffic — mTLS owns the wire.
- An attacker who somehow forges a cert still can't impersonate a DID — the signature won't verify against the claimed key.
- An attacker who breaks the signature scheme entirely still can't get past Hydra's authorization check.

The cert lives at the socket. The bearer token lives in the header. The signature lives in the body. Each one rejects a class of attack the others are blind to. **No agent framework we surveyed ships all three out of the box.**

→ **The full story:** [docs/SECURITY_STACK.md](docs/SECURITY_STACK.md) walks through what each layer does, how a single request flows through all three, today's defaults, the five real bugs we hit shipping default-on mTLS, and a troubleshooting matrix.

<br/>

## Features

Every row here links out to the guide that actually goes into it.

| Feature | What it does | Docs |
|---|---|---|
| **A2A JSON-RPC** | The protocol other agents already speak. `message/send`, `tasks/get`, `message/stream` on port 3773. | — |
| **mTLS transport** | The socket is encrypted and mutually authenticated. Each agent gets a real X.509 cert from step-ca (SAN = DID), serves uvicorn over TLS, and renews itself every ~16 hours. On by default for the inbox personal agent in 2026.21.1. | [SECURITY_STACK.md](docs/SECURITY_STACK.md) · [MTLS_DEPLOYMENT_GUIDE.md](docs/MTLS_DEPLOYMENT_GUIDE.md) |
| **DID identity** | Every response your agent sends is signed with an Ed25519 key. Callers verify with a W3C DID — there's no shared secret to leak, no central authority to query, and the same DID is the cert's SAN, the OAuth2 client_id, and the message signer. All three have to agree, or the request is rejected. | [DID.md](docs/DID.md) |
| **OAuth2 via Hydra** | Scoped bearer tokens (`agent:read`, `agent:write`, `agent:execute`) instead of one key that opens every door. Each agent self-registers as a Hydra client at boot — its DID IS its client_id, so authorization, identity, and transport-layer cert all point at the same actor. | [AUTHENTICATION.md](docs/AUTHENTICATION.md) |
| **x402 payments** | Flip a flag and the agent demands USDC before your handler ever sees the request. **5 chains pre-configured** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — and any other EVM chain (Polygon, Avalanche, Arbitrum, …) takes one `extra_networks` entry. | [PAYMENT.md](docs/PAYMENT.md) |
| **Push notifications** | The agent webhooks you when a task changes state. Stop polling. | [NOTIFICATIONS.md](docs/NOTIFICATIONS.md) |
| **Skills system** | Declare what your agent can do; callers see it on the agent card before they spend a token asking. | [SKILLS.md](docs/SKILLS.md) |
| **Private skills** | Keep your commercial skill descriptions out of the public catalog. Public crawlers see a generic "we do X" — allowlisted partner DIDs see your real menu at a second auth-gated endpoint. Useful when your skill descriptions ARE your product roadmap. | [PRIVATE_SKILLS.md](docs/PRIVATE_SKILLS.md) |
| **Agent negotiation** | Two agents agree on price, latency, and SLA up front. No surprise bills. | [NEGOTIATION.md](docs/NEGOTIATION.md) |
| **Storage** | Postgres for tasks and messages. Swap the backend if you've got a preference. | [STORAGE.md](docs/STORAGE.md) |
| **Scheduler** | Redis-backed retries, timeouts, and recurring tasks. | [SCHEDULER.md](docs/SCHEDULER.md) |
| **Public tunnel** | `expose: true` puts your laptop on the internet. No port forwarding, no router config. | [TUNNELING.md](docs/TUNNELING.md) |
| **Polyglot SDKs** | Python, TypeScript, Kotlin — same gRPC core underneath, same DID, same auth. | [GRPC_LANGUAGE_AGNOSTIC.md](docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **Cloud deploy** | `bindu deploy agent.py --runtime=boxd` ships your script to a microVM and prints the HTTPS URL. No Dockerfile. | [runtime/quickstart.md](docs/runtime/quickstart.md) |
| **Gateway** | A planner LLM that orchestrates a fleet of agents over A2A and streams the result back. | [GATEWAY.md](docs/GATEWAY.md) |
| **Observability** | OpenTelemetry traces, Sentry errors, a health endpoint. The boring stuff that saves you at 2am. | [OBSERVABILITY.md](docs/OBSERVABILITY.md) |

<br/>

## Demo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu demo video" width="640" />
  </a>
</div>

The operator inbox at the top of this page is in [`inbox/`](inbox/README.md) — same auth, same DID signing, just visible. Run it with `cd inbox && npm run dev`.

<br/>

## Examples

A handful from [`examples/`](examples/):

| Example | What it shows |
|---|---|
| [Agent Swarm](examples/agent_swarm/) | A small society of Agno agents passing work to each other. |
| [Premium Advisor](examples/premium-advisor/) | x402 in practice — the caller has to pay USDC before anything runs. |
| [Hermes via Bindu](examples/hermes_agent/) | Nous Research's Hermes agent, bindufied in ~90 lines. |
| [Gateway Test Fleet](examples/gateway_test_fleet/) | Five agents and one gateway — the multi-agent story end to end. |
| [TypeScript OpenAI Agent](examples/typescript-openai-agent/) | A TS-only agent with zero Python in your repo. |

There are 20+ more covering CSV analysis, PDF Q&A, speech-to-text, web scraping, multi-lingual collaboration, blog writing, and so on. Browse them in [`examples/`](examples/).

<br/>

## Why we built Bindu

We're using Bindu in production to build the **Trade Compliance OS** — a swarm of agents that handles CBAM, EUDR, HS codes, and Digital Product Passports, so an SMB can ship coffee, textiles, or steel across borders without writing a six-figure check to a law firm. Every agent in that swarm is bindufied. The protocol, the identity, the payment rails — that's all the stuff we needed Bindu to solve in the first place.

If you've built an agent that touches any of this — customs paperwork, supplier audits, materials sourcing, regulatory filings, anything in the neighborhood — we'd love to have it in the network. [Come find us on Discord](https://discord.gg/3w5zuYUuwt) and let's talk.

<br/>

## Supported frameworks

Bring whatever you already like writing agents in. Bindu doesn't care what's inside the handler.

| Language | Frameworks tested in this repo |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **Any other** | via the [gRPC core](docs/grpc/) — a new SDK is usually a few hundred lines |

If your model provider speaks the OpenAI or Anthropic API, it works — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com), and the rest.

<br/>

## Documentation

- [Full docs site](https://docs.getbindu.com)
- [Security stack — mTLS + Hydra + DID](docs/SECURITY_STACK.md) — how the three identity layers compose, with a live walkthrough using the gateway test fleet
- [Calling a secured agent](docs/AUTH.md) — the shortest path: the two things you do when auth is on (token + DID signature), in one page
- [Auth — long form](docs/AUTHENTICATION.md) and [DID signing — long form](docs/DID.md) — when the short version isn't enough
- [mTLS deployment](docs/MTLS_DEPLOYMENT_GUIDE.md) — DevOps-facing guide for standing up step-ca, OIDC provisioner config, and the cert lifecycle
- [Cloud deployment](docs/runtime/quickstart.md) — `bindu deploy` walkthrough
- [Gateway](docs/GATEWAY.md) — multi-agent orchestration
- [Private skills](docs/PRIVATE_SKILLS.md) — hide your commercial menu from the public catalog; show it only to allowlisted partner DIDs
- [gRPC architecture](docs/grpc/) — for anyone building a new language SDK
- [Known issues](bugs/known-issues.md) — read this before you push to production
- [Troubleshooting](docs/AUTHENTICATION.md#troubleshooting) — the errors you'll hit, and how to get past them

<br/>

## Testing

```bash
uv run pytest tests/unit/ -v                                    # fast unit tests
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # full suite
```

<br/>

## Contributing

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

The full guide is in [`.github/contributing.md`](.github/contributing.md). Most of the day-to-day back-and-forth happens on [Discord](https://discord.gg/3w5zuYUuwt) — come say hi.

<br/>

## Maintainers

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/raahulrahl">
        <img src="https://github.com/raahulrahl.png?size=120" width="100" alt="Raahul Dutta" /><br />
        <sub><b>Raahul Dutta</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Paraschamoli">
        <img src="https://github.com/Paraschamoli.png?size=120" width="100" alt="Paras Chamoli" /><br />
        <sub><b>Paras Chamoli</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/chandan-1427">
        <img src="https://github.com/chandan-1427.png?size=120" width="100" alt="Chandan" /><br />
        <sub><b>Chandan</b></sub>
      </a>
    </td>
  </tr>
</table>

<br/>

## Acknowledgements

Bindu stands on the shoulders of a lot of good open source:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Star history

<a href="https://star-history.dera.page/#getbindu/Bindu&Date">
  <img src="https://star-history.dera.page/svg?repos=getbindu/Bindu&type=Date" alt="Star history">
</a>

<br/>

## License

Apache 2.0. See [LICENSE.md](LICENSE.md).

<p align="center">
  <em>"We believe in the sunflower theory — standing tall together, bringing hope and light to the Internet of Agents."</em>
</p>
