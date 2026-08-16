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
        <b>Deutsch</b> |
        <a href="README.es.md">Español</a> |
        <a href="README.fr.md">Français</a> |
        <a href="README.hi.md">हिंदी</a> |
        <a href="README.bn.md">বাংলা</a> |
        <a href="README.zh.md">中文</a> |
        <a href="README.nl.md">Nederlands</a> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">Die Identitäts-, Kommunikations- und Zahlungsschicht für KI-Agenten.</h3>

So sieht die Lage aus. Du hast einen Agenten gebaut. Er funktioniert. Aber damit du ihn wirklich von der Leine lässt — mit anderen Agenten reden, beweisen, wer er ist, Geld für seine Arbeit nehmen — wärst du für eine Menge langweiligen Klempnerkram zuständig. Eine DID-Bibliothek integrieren. Einen OAuth-Flow aufsetzen. Bezahl-Middleware. Eine HTTP-Schicht, die welches Protokoll auch immer der Rest der Agentenwelt gerade benutzt.

Bindu ist all dieser Klempnerkram, hinter einem einzigen Funktionsaufruf. Du wickelst deinen Handler mit `bindufy()` ein, und ein paar Sekunden später ist dein Agent online — mit seiner eigenen kryptografischen Identität, [A2A](https://github.com/a2aproject/A2A) sprechend (das Protokoll, das andere Agenten schon benutzen) und bereit, USDC auf jeder EVM-Chain einzufordern, bevor er irgendwas tut ([x402](https://github.com/coinbase/x402)). Dein Handler bleibt so klein wie `(messages) -> response`. Das Framework im Handler — Agno, LangChain, CrewAI, dein eigenes Ding — interessiert Bindu nicht.

Es gibt SDKs für Python, TypeScript und Kotlin, und sie alle teilen sich denselben gRPC-Kern. Die Sprache ist eine Wahl; das Protokoll und die Identität sind sowieso dieselben. Wenn du tiefer einsteigen willst, sind die [Docs](https://docs.getbindu.com) die nächste Station.

## Installation

Du brauchst Python 3.12+ und [uv](https://github.com/astral-sh/uv).

```bash
uv add bindu
```

Wenn du an Bindu selbst rumbastelst statt es nur zu benutzen:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

Um die Beispiele auszuführen, brauchst du einen API-Schlüssel für mindestens einen LLM-Anbieter — `OPENROUTER_API_KEY`, `OPENAI_API_KEY` oder `MINIMAX_API_KEY`.

<br/>

## Schnellstart

Bau den Agenten, den du willst, übergib ihn an `bindufy()`, und er ist online. Der Block unten ist das Ganze — kopier ihn in eine Datei, setz deinen `OPENAI_API_KEY`, lass ihn laufen.

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

Der Agent ist jetzt live auf `http://localhost:3773`. `expose: True` öffnet einen FRP-Tunnel, damit der Rest des Internets ihn erreichen kann, ohne dass du Port-Forwarding einrichtest.

<details>
<summary>TypeScript-Äquivalent</summary>

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

Das TypeScript-SDK startet den Python-Kern im Hintergrund — du siehst ihn nicht, und du brauchst auch kein Python in deinem eigenen Code. Gleiches Protokoll, gleiche DID. Vollständiges Beispiel in [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/).

</details>

<details>
<summary>Den Agenten mit curl aufrufen</summary>

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

Dann poll `tasks/get` mit derselben `taskId`, bis der Zustand `completed` erreicht.

</details>

<br/>

## Features

Jede Zeile hier verlinkt auf den Leitfaden, der tatsächlich ins Detail geht.

| Feature | Was es macht | Docs |
|---|---|---|
| **A2A JSON-RPC** | Das Protokoll, das andere Agenten schon sprechen. `message/send`, `tasks/get`, `message/stream` auf Port 3773. | — |
| **DID-Identität** | Jede Antwort, die dein Agent verschickt, ist mit einem Ed25519-Schlüssel signiert. Aufrufer verifizieren über eine W3C-DID — es gibt kein geteiltes Geheimnis, das durchsickern könnte. | [DID.md](../docs/DID.md) |
| **OAuth2 via Hydra** | Scoped Tokens (`agent:read`, `agent:write`, `agent:execute`) statt eines Bearer, der jede Tür öffnet. | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **x402-Zahlungen** | Setz ein Flag, und der Agent fordert USDC, bevor dein Handler die Anfrage überhaupt sieht. **5 Chains vorkonfiguriert** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — und jede andere EVM-Chain (Polygon, Avalanche, Arbitrum, …) braucht einen `extra_networks`-Eintrag. | [PAYMENT.md](../docs/PAYMENT.md) |
| **Push-Benachrichtigungen** | Der Agent ruft dich per Webhook, wenn sich ein Task-Zustand ändert. Hör auf zu pollen. | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Skills-System** | Deklariere, was dein Agent kann; Aufrufer sehen es auf der Agent Card, bevor sie einen Token ausgeben, um zu fragen. | [SKILLS.md](../docs/SKILLS.md) |
| **Private Skills** | Halte deine kommerziellen Skill-Beschreibungen aus dem öffentlichen Katalog raus. Öffentliche Crawler sehen ein generisches "wir machen X" — auf der Allowlist stehende Partner-DIDs sehen dein echtes Menü an einem zweiten, auth-geschützten Endpoint. Nützlich, wenn deine Skill-Beschreibungen DEINE Produkt-Roadmap SIND. | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **Agenten-Verhandlung** | Zwei Agenten einigen sich vorab auf Preis, Latenz und SLA. Keine Überraschungsrechnungen. | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **Speicher** | Postgres für Tasks und Nachrichten. Tausch das Backend, wenn du eine Vorliebe hast. | [STORAGE.md](../docs/STORAGE.md) |
| **Scheduler** | Redis-gestützte Retries, Timeouts und wiederkehrende Tasks. | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **Öffentlicher Tunnel** | `expose: true` stellt deinen Laptop ins Internet. Kein Port-Forwarding, keine Router-Konfiguration. | [TUNNELING.md](../docs/TUNNELING.md) |
| **Polyglot-SDKs** | Python, TypeScript, Kotlin — derselbe gRPC-Kern darunter, dieselbe DID, dieselbe Auth. | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **Cloud-Deploy** | `bindu deploy agent.py --runtime=boxd` schickt dein Skript an eine MicroVM und gibt die HTTPS-URL aus. Kein Dockerfile. | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | Ein Planer-LLM, der eine Flotte von Agenten über A2A orchestriert und das Ergebnis zurückstreamt. | [GATEWAY.md](../docs/GATEWAY.md) |
| **Observability** | OpenTelemetry-Traces, Sentry-Fehler, ein Health-Endpoint. Der langweilige Kram, der dich um 2 Uhr morgens rettet. | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## Demo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo-Video" width="640" />
  </a>
</div>

Es gibt außerdem eine Gmail-artige Betreiber-Inbox in [`inbox/`](../inbox/). Führe `cd inbox && npm run dev` aus und öffne `http://localhost:3775`.

<br/>

## Beispiele

Eine Auswahl aus [`examples/`](../examples/):

| Beispiel | Was es zeigt |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Eine kleine Gesellschaft aus Agno-Agenten, die sich gegenseitig Arbeit zuwerfen. |
| [Premium Advisor](../examples/premium-advisor/) | x402 in der Praxis — der Aufrufer muss USDC zahlen, bevor irgendwas läuft. |
| [Hermes über Bindu](../examples/hermes_agent/) | Der Hermes-Agent von Nous Research, in ~90 Zeilen bindufiziert. |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | Fünf Agenten und ein Gateway — die Multi-Agenten-Story von Anfang bis Ende. |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | Ein reiner TS-Agent ohne Python in deinem Repo. |

Es gibt 20+ weitere zu CSV-Analyse, PDF-Q&A, Speech-to-Text, Web-Scraping, mehrsprachiger Zusammenarbeit, Blog-Schreiben und so weiter. Stöber in [`examples/`](../examples/).

<br/>

## Warum wir Bindu gebaut haben

Wir setzen Bindu produktiv ein, um das **Trade Compliance OS** zu bauen — einen Schwarm Agenten, der CBAM, EUDR, HS-Codes und Digitale Produktpässe abwickelt, damit ein KMU Kaffee, Textilien oder Stahl über Grenzen schicken kann, ohne einen sechsstelligen Scheck an eine Anwaltskanzlei zu schreiben. Jeder Agent in diesem Schwarm ist bindufiziert. Das Protokoll, die Identität, die Bezahlschienen — genau das mussten wir mit Bindu zuerst lösen.

Wenn du einen Agenten gebaut hast, der irgendwas davon berührt — Zollpapiere, Lieferantenaudits, Materialbeschaffung, regulatorische Meldungen, irgendwas in der Nachbarschaft — hätten wir ihn gern im Netzwerk. [Triff uns auf Discord](https://discord.gg/3w5zuYUuwt), und lass uns reden.

<br/>

## Unterstützte Frameworks

Bring mit, was du sowieso schon gern zum Agenten-Schreiben benutzt. Bindu ist es egal, was im Handler steckt.

| Sprache | In diesem Repo getestete Frameworks |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **Jede andere** | über den [gRPC-Kern](../docs/grpc/) — ein neues SDK sind meistens ein paar hundert Zeilen |

Wenn dein Modell-Anbieter die OpenAI- oder Anthropic-API spricht, funktioniert es — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) und der Rest.

<br/>

## Dokumentation

- [Vollständige Doku-Seite](https://docs.getbindu.com)
- [Einen abgesicherten Agenten aufrufen](../docs/AUTHENTICATION.md) — der Auth-Flow mit DID-Signatur und Hydra-Tokens, inklusive funktionierendem Python-Client
- [Cloud-Deployment](../docs/runtime/quickstart.md) — `bindu deploy`-Walkthrough
- [Gateway](../docs/GATEWAY.md) — Multi-Agenten-Orchestrierung
- [Private Skills](../docs/PRIVATE_SKILLS.md) — versteck dein kommerzielles Menü vor dem öffentlichen Katalog; zeig es nur zugelassenen Partner-DIDs
- [gRPC-Architektur](../docs/grpc/) — für alle, die ein neues Sprach-SDK bauen
- [Bekannte Probleme](../bugs/known-issues.md) — lies das, bevor du in Produktion gehst
- [Troubleshooting](../docs/AUTHENTICATION.md#troubleshooting) — die Fehler, die du sehen wirst, und wie du an ihnen vorbeikommst

<br/>

## Tests

```bash
uv run pytest tests/unit/ -v                                    # schnelle Unit-Tests
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # volle Suite
```

<br/>

## Mitwirken

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

Der volle Leitfaden steht in [`.github/contributing.md`](../.github/contributing.md). Das meiste Tagesgeschäft läuft auf [Discord](https://discord.gg/3w5zuYUuwt) — komm vorbei und sag hallo.

<br/>

## Maintainer

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

## Danksagungen

Bindu steht auf den Schultern von viel guter Open-Source-Software:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Star-Verlauf

<a href="https://star-history.dera.page/#getbindu/Bindu&Date">
  <img src="https://star-history.dera.page/svg?repos=getbindu/Bindu&type=Date" alt="Star-Verlauf">
</a>

<br/>

## Lizenz

Apache 2.0. Siehe [LICENSE.md](../LICENSE.md).

<p align="center">
  <em>"Wir glauben an die Sonnenblumen-Theorie — gemeinsam aufrecht stehen, Hoffnung und Licht ins Internet der Agenten bringen."</em>
</p>
