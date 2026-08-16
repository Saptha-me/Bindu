<p align="center">
  <img src="../assets/bindu_logo.png" alt="Bindu" width="120" />
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
</p>

<h4 align="center">
    <p>
        <a href="../README.md">English</a> |
        <a href="README.de.md">Deutsch</a> |
        <a href="README.es.md">Español</a> |
        <a href="README.fr.md">Français</a> |
        <a href="README.hi.md">हिंदी</a> |
        <a href="README.bn.md">বাংলা</a> |
        <a href="README.zh.md">中文</a> |
        <b>Nederlands</b> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">De identiteits-, communicatie- en betalingslaag voor AI-agenten.</h3>

Dit is de situatie. Je hebt een agent gebouwd. Hij werkt. Maar om hem echt los te laten — met andere agenten praten, bewijzen wie hij is, betaald krijgen voor zijn werk — zou je een hoop saai loodgieterswerk op je nek krijgen. Een DID-bibliotheek integreren. Een OAuth-flow opzetten. Betaal-middleware. Een HTTP-laag die het protocol volgt dat de rest van de agentenwereld toevallig gebruikt.

Bindu is al dat loodgieterswerk, achter één functie-aanroep. Je wikkelt je handler in met `bindufy()`, en een paar seconden later staat je agent online — met zijn eigen cryptografische identiteit, sprekend in [A2A](https://github.com/a2aproject/A2A) (het protocol dat andere agenten al gebruiken), en klaar om USDC op elke EVM-chain op te eisen voor hij iets doet ([x402](https://github.com/coinbase/x402)). Je handler blijft zo klein als `(messages) -> response`. Het framework in de handler — Agno, LangChain, CrewAI, je eigen ding — dat boeit Bindu niet.

Er zijn SDK's voor Python, TypeScript en Kotlin, en ze delen allemaal dezelfde gRPC-kern. De taal is een keuze; het protocol en de identiteit zijn hoe dan ook hetzelfde. Als je dieper wilt graven zijn de [docs](https://docs.getbindu.com) de volgende stop.

## Installatie

Je hebt Python 3.12+ en [uv](https://github.com/astral-sh/uv) nodig.

```bash
uv add bindu
```

Als je aan Bindu zelf sleutelt in plaats van het te gebruiken:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

Om de voorbeelden te draaien heb je een API-sleutel nodig voor minstens één LLM-provider — `OPENROUTER_API_KEY`, `OPENAI_API_KEY` of `MINIMAX_API_KEY`.

<br/>

## Snelstart

Bouw de agent die je wilt, geef 'm aan `bindufy()`, en hij is online. Het blok hieronder is het hele verhaal — kopieer 't in een bestand, zet je `OPENAI_API_KEY`, draai 't.

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

De agent staat nu live op `http://localhost:3773`. `expose: True` opent een FRP-tunnel zodat de rest van het internet hem kan bereiken zonder dat je port forwarding opzet.

<details>
<summary>TypeScript-equivalent</summary>

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

De TypeScript-SDK start de Python-kern op de achtergrond — je ziet 'm niet en je hebt geen regel Python in je eigen codebase nodig. Zelfde protocol, zelfde DID. Volledig voorbeeld in [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/).

</details>

<details>
<summary>De agent aanroepen met curl</summary>

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

Poll daarna `tasks/get` met dezelfde `taskId` tot de state op `completed` staat.

</details>

<br/>

## Features

Elke rij linkt naar de gids die echt in detail treedt.

| Feature | Wat 't doet | Docs |
|---|---|---|
| **A2A JSON-RPC** | Het protocol dat andere agenten al spreken. `message/send`, `tasks/get`, `message/stream` op poort 3773. | — |
| **DID-identiteit** | Elk antwoord dat je agent stuurt is ondertekend met een Ed25519-sleutel. Aanroepers verifiëren via een W3C-DID — er is geen gedeeld geheim dat kan lekken. | [DID.md](../docs/DID.md) |
| **OAuth2 via Hydra** | Scoped tokens (`agent:read`, `agent:write`, `agent:execute`) in plaats van één bearer die elke deur openzet. | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **x402-betalingen** | Zet een vlag aan en de agent eist USDC voordat je handler de request überhaupt ziet. **5 chains voorgeconfigureerd** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — en elke andere EVM-chain (Polygon, Avalanche, Arbitrum, …) past in één `extra_networks`-entry. | [PAYMENT.md](../docs/PAYMENT.md) |
| **Push-notificaties** | De agent webhookt jou wanneer een taak van status verandert. Stop met pollen. | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Skills-systeem** | Declareer wat je agent kan; aanroepers zien dat op de agent card voor ze een token uitgeven om te vragen. | [SKILLS.md](../docs/SKILLS.md) |
| **Private skills** | Houd je commerciële skill-beschrijvingen uit de publieke catalogus. Publieke crawlers zien een generiek "we doen X" — partner-DID's op de allowlist zien je echte menu op een tweede, auth-beveiligd endpoint. Handig als je skill-beschrijvingen je product-roadmap ZIJN. | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **Agent-onderhandeling** | Twee agenten worden het vooraf eens over prijs, latency en SLA. Geen verrassingsrekeningen. | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **Opslag** | Postgres voor taken en berichten. Ruil de backend om als je een voorkeur hebt. | [STORAGE.md](../docs/STORAGE.md) |
| **Scheduler** | Op Redis gebaseerde retries, timeouts en terugkerende taken. | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **Publieke tunnel** | `expose: true` zet je laptop op het internet. Geen port forwarding, geen routerconfiguratie. | [TUNNELING.md](../docs/TUNNELING.md) |
| **Polyglot SDK's** | Python, TypeScript, Kotlin — dezelfde gRPC-kern eronder, dezelfde DID, dezelfde auth. | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **Cloud deploy** | `bindu deploy agent.py --runtime=boxd` schiet je script naar een microVM en print de HTTPS-URL. Geen Dockerfile. | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | Een planner-LLM die een vloot agenten orkestreert over A2A en het resultaat terug streamt. | [GATEWAY.md](../docs/GATEWAY.md) |
| **Observability** | OpenTelemetry-traces, Sentry-errors, een health-endpoint. Het saaie spul dat je om 2 uur 's nachts redt. | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## Demo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu demovideo" width="640" />
  </a>
</div>

Er is ook een Gmail-achtige operator-inbox in [`inbox/`](../inbox/). Draai `cd inbox && npm run dev` en open `http://localhost:3775`.

<br/>

## Voorbeelden

Een greep uit [`examples/`](../examples/):

| Voorbeeld | Wat 't laat zien |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Een kleine maatschappij van Agno-agenten die werk aan elkaar doorgeven. |
| [Premium Advisor](../examples/premium-advisor/) | x402 in de praktijk — de aanroeper moet USDC betalen voor er iets draait. |
| [Hermes via Bindu](../examples/hermes_agent/) | De Hermes-agent van Nous Research, bindufied in ~90 regels. |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | Vijf agenten en één gateway — het multi-agent-verhaal van A tot Z. |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | Een TS-only agent met nul Python in je repo. |

Er zijn er nog 20+ over CSV-analyse, PDF-Q&A, speech-to-text, web scraping, meertalige samenwerking, blog schrijven enzovoort. Snuffel rond in [`examples/`](../examples/).

<br/>

## Waarom we Bindu hebben gebouwd

We gebruiken Bindu in productie om het **Trade Compliance OS** te bouwen — een zwerm agenten die CBAM, EUDR, HS-codes en Digitale Productpaspoorten afhandelt, zodat een mkb-bedrijf koffie, textiel of staal over de grens kan zetten zonder een cheque met zes cijfers naar een advocatenkantoor te schrijven. Elke agent in die zwerm is bindufied. Het protocol, de identiteit, de betalingsrails — dat is precies waar we Bindu in eerste instantie voor nodig hadden.

Heb je een agent gebouwd die iets van dit alles raakt — douanepapieren, leveranciersaudits, materiaalsourcing, regulatoire indieningen, alles in die hoek — dan zien we 'm graag in het netwerk. [Zoek ons op op Discord](https://discord.gg/3w5zuYUuwt) en laten we praten.

<br/>

## Ondersteunde frameworks

Neem mee waarmee je toch al graag agenten schrijft. Bindu kan het niet schelen wat er in de handler zit.

| Taal | Frameworks die in deze repo zijn getest |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **Iets anders** | via de [gRPC-kern](../docs/grpc/) — een nieuw SDK is meestal een paar honderd regels |

Als je modelprovider de OpenAI- of Anthropic-API spreekt, werkt het — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) en de rest.

<br/>

## Documentatie

- [Volledige docs-site](https://docs.getbindu.com)
- [Een beveiligde agent aanroepen](../docs/AUTHENTICATION.md) — de auth-flow met DID-signering en Hydra-tokens, met een werkende Python-client
- [Cloud deployment](../docs/runtime/quickstart.md) — `bindu deploy`-walkthrough
- [Gateway](../docs/GATEWAY.md) — multi-agent-orkestratie
- [Private skills](../docs/PRIVATE_SKILLS.md) — verberg je commerciële menu voor de publieke catalogus; laat 't alleen aan partner-DID's op de allowlist zien
- [gRPC-architectuur](../docs/grpc/) — voor wie een nieuw taal-SDK bouwt
- [Bekende issues](../bugs/known-issues.md) — lees dit voor je naar productie pusht
- [Troubleshooting](../docs/AUTHENTICATION.md#troubleshooting) — de fouten die je gaat tegenkomen, en hoe je eromheen komt

<br/>

## Testen

```bash
uv run pytest tests/unit/ -v                                    # snelle unit tests
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # hele suite
```

<br/>

## Bijdragen

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

De volledige gids staat in [`.github/contributing.md`](../.github/contributing.md). Het meeste dagelijkse heen-en-weer loopt via [Discord](https://discord.gg/3w5zuYUuwt) — kom even gedag zeggen.

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

## Dankwoord

Bindu staat op de schouders van een hoop goeie open source:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Star-geschiedenis

<a href="https://star-history.dera.page/#getbindu/Bindu&Date">
  <img src="https://star-history.dera.page/svg?repos=getbindu/Bindu&type=Date" alt="Star-geschiedenis">
</a>

<br/>

## Licentie

Apache 2.0. Zie [LICENSE.md](../LICENSE.md).

<p align="center">
  <em>"Wij geloven in de zonnebloem-theorie — samen rechtop staan en hoop en licht brengen op het Internet van Agenten."</em>
</p>
