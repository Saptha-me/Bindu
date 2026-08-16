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
        <b>Español</b> |
        <a href="README.fr.md">Français</a> |
        <a href="README.hi.md">हिंदी</a> |
        <a href="README.bn.md">বাংলা</a> |
        <a href="README.zh.md">中文</a> |
        <a href="README.nl.md">Nederlands</a> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">La capa de identidad, comunicación y pagos para agentes de IA.</h3>

La situación es esta. Construiste un agente. Funciona. Pero para soltarlo de verdad — hablar con otros agentes, demostrar quién es, cobrar por el trabajo — te tocaría montar un montón de fontanería aburrida. Integrar una librería DID. Configurar un flujo OAuth. Middleware de pagos. Una capa HTTP que hable el protocolo que esté usando el resto del mundo de los agentes.

Bindu es toda esa fontanería, detrás de una sola llamada a función. Envuelves tu handler con `bindufy()`, y unos segundos después tu agente está online — con su propia identidad criptográfica, hablando [A2A](https://github.com/a2aproject/A2A) (el protocolo que ya usan otros agentes), y listo para exigir USDC en cualquier cadena EVM antes de hacer nada ([x402](https://github.com/coinbase/x402)). Tu handler se queda tan pequeño como `(messages) -> response`. El framework dentro del handler — Agno, LangChain, CrewAI, el tuyo propio — a Bindu le da igual.

Hay SDKs para Python, TypeScript y Kotlin, y todos comparten el mismo core en gRPC. El lenguaje es una elección; el protocolo y la identidad son los mismos en cualquier caso. Cuando quieras ir más a fondo, los [docs](https://docs.getbindu.com) son la siguiente parada.

## Instalación

Vas a necesitar Python 3.12+ y [uv](https://github.com/astral-sh/uv).

```bash
uv add bindu
```

Si estás trasteando con Bindu en sí, no solo usándolo:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

Para correr los ejemplos hace falta una clave de API de al menos un proveedor de LLM — `OPENROUTER_API_KEY`, `OPENAI_API_KEY` o `MINIMAX_API_KEY`.

<br/>

## Inicio rápido

Construye el agente que quieras, pásalo a `bindufy()`, y está online. El bloque de abajo es todo — cópialo en un archivo, pon tu `OPENAI_API_KEY`, ejecútalo.

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

El agente ya está activo en `http://localhost:3773`. `expose: True` abre un túnel FRP para que el resto de internet pueda llegar a él sin que configures port forwarding.

<details>
<summary>Equivalente en TypeScript</summary>

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

El SDK de TypeScript arranca el core de Python en segundo plano — no lo ves, y no necesitas nada de Python en tu propio código. Mismo protocolo, misma DID. Ejemplo completo en [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/).

</details>

<details>
<summary>Llamar al agente con curl</summary>

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

Después haz polling de `tasks/get` con el mismo `taskId` hasta que el estado llegue a `completed`.

</details>

<br/>

## Características

Cada fila enlaza a la guía que realmente entra en detalle.

| Característica | Qué hace | Docs |
|---|---|---|
| **A2A JSON-RPC** | El protocolo que ya hablan otros agentes. `message/send`, `tasks/get`, `message/stream` en el puerto 3773. | — |
| **Identidad DID** | Cada respuesta que envía tu agente va firmada con una clave Ed25519. Quien llama verifica con una DID W3C — no hay un secreto compartido que se pueda filtrar. | [DID.md](../docs/DID.md) |
| **OAuth2 vía Hydra** | Tokens con scopes (`agent:read`, `agent:write`, `agent:execute`) en lugar de un único bearer que abra todas las puertas. | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **Pagos x402** | Activas un flag y el agente exige USDC antes de que tu handler vea la petición. **5 cadenas preconfiguradas** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — y cualquier otra cadena EVM (Polygon, Avalanche, Arbitrum, …) entra con una entrada `extra_networks`. | [PAYMENT.md](../docs/PAYMENT.md) |
| **Notificaciones push** | El agente te avisa por webhook cuando una tarea cambia de estado. Deja de hacer polling. | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Sistema de skills** | Declara lo que tu agente sabe hacer; quien llama lo ve en la agent card antes de gastar un token preguntando. | [SKILLS.md](../docs/SKILLS.md) |
| **Skills privadas** | Mantén las descripciones comerciales de tus skills fuera del catálogo público. Los crawlers públicos ven un "hacemos X" genérico — las DIDs de partners en la allowlist ven tu menú real en un segundo endpoint con auth. Útil cuando las descripciones SON tu roadmap de producto. | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **Negociación entre agentes** | Dos agentes se ponen de acuerdo de antemano sobre precio, latencia y SLA. Sin facturas sorpresa. | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **Almacenamiento** | Postgres para tareas y mensajes. Cambia el backend si tienes preferencia. | [STORAGE.md](../docs/STORAGE.md) |
| **Scheduler** | Reintentos, timeouts y tareas recurrentes respaldados por Redis. | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **Túnel público** | `expose: true` pone tu portátil en internet. Sin port forwarding, sin configuración del router. | [TUNNELING.md](../docs/TUNNELING.md) |
| **SDKs políglotas** | Python, TypeScript, Kotlin — el mismo core gRPC debajo, la misma DID, la misma auth. | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **Despliegue en cloud** | `bindu deploy agent.py --runtime=boxd` lleva tu script a una microVM y te imprime la URL HTTPS. Sin Dockerfile. | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | Un LLM-planificador que orquesta una flota de agentes sobre A2A y va devolviendo el resultado por streaming. | [GATEWAY.md](../docs/GATEWAY.md) |
| **Observabilidad** | Trazas OpenTelemetry, errores en Sentry, un endpoint de health. Lo aburrido que te salva a las 2 de la mañana. | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## Demo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Vídeo demo de Bindu" width="640" />
  </a>
</div>

También hay un buzón de operador con aspecto de Gmail en [`inbox/`](../inbox/). Ejecuta `cd inbox && npm run dev` y abre `http://localhost:3775`.

<br/>

## Ejemplos

Un puñado de [`examples/`](../examples/):

| Ejemplo | Qué muestra |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Una pequeña sociedad de agentes Agno pasándose trabajo entre ellos. |
| [Premium Advisor](../examples/premium-advisor/) | x402 en la práctica — quien llama tiene que pagar USDC antes de que arranque nada. |
| [Hermes vía Bindu](../examples/hermes_agent/) | El agente Hermes de Nous Research, bindufiado en ~90 líneas. |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | Cinco agentes y un gateway — la historia multi-agente de cabo a rabo. |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | Un agente sólo en TS sin nada de Python en tu repo. |

Hay 20+ más cubriendo análisis de CSV, Q&A sobre PDF, speech-to-text, web scraping, colaboración multilingüe, escritura de blogs, etc. Échales un ojo en [`examples/`](../examples/).

<br/>

## Por qué construimos Bindu

Estamos usando Bindu en producción para construir el **Trade Compliance OS** — un enjambre de agentes que gestiona CBAM, EUDR, códigos HS y Pasaportes Digitales de Producto, para que una pyme pueda enviar café, textiles o acero cruzando fronteras sin extenderle un cheque de seis cifras a un bufete. Cada agente de ese enjambre está bindufiado. El protocolo, la identidad, los raíles de pago — eso es exactamente lo que necesitábamos que Bindu resolviera de entrada.

Si has construido un agente que toca algo de esto — papeleo aduanero, auditorías de proveedores, sourcing de materiales, presentaciones regulatorias, cualquier cosa del barrio — nos encantaría tenerlo en la red. [Búscanos en Discord](https://discord.gg/3w5zuYUuwt) y lo hablamos.

<br/>

## Frameworks soportados

Trae lo que ya te guste para escribir agentes. A Bindu le da igual lo que haya dentro del handler.

| Lenguaje | Frameworks probados en este repo |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **Cualquier otro** | vía el [core gRPC](../docs/grpc/) — un SDK nuevo suele ser unas pocas cientos de líneas |

Si tu proveedor de modelos habla la API de OpenAI o Anthropic, funciona — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) y el resto.

<br/>

## Documentación

- [Sitio de docs completo](https://docs.getbindu.com)
- [Llamar a un agente protegido](../docs/AUTHENTICATION.md) — el flujo de auth con firma DID y tokens de Hydra, con un cliente Python que funciona
- [Despliegue en cloud](../docs/runtime/quickstart.md) — walkthrough de `bindu deploy`
- [Gateway](../docs/GATEWAY.md) — orquestación multi-agente
- [Skills privadas](../docs/PRIVATE_SKILLS.md) — esconde tu menú comercial del catálogo público; muéstralo sólo a DIDs de partners en la allowlist
- [Arquitectura gRPC](../docs/grpc/) — para cualquiera que esté construyendo un SDK en otro lenguaje
- [Issues conocidos](../bugs/known-issues.md) — léelo antes de subir a producción
- [Troubleshooting](../docs/AUTHENTICATION.md#troubleshooting) — los errores con los que vas a chocar, y cómo salir de ellos

<br/>

## Tests

```bash
uv run pytest tests/unit/ -v                                    # tests unitarios rápidos
uv run pytest tests/integration/grpc/ -v -m e2e                 # E2E de gRPC
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # suite completa
```

<br/>

## Cómo contribuir

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

La guía completa está en [`.github/contributing.md`](../.github/contributing.md). La mayor parte del día a día pasa por [Discord](https://discord.gg/3w5zuYUuwt) — pásate y saluda.

<br/>

## Mantenedores

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

## Agradecimientos

Bindu se apoya en los hombros de mucho buen open source:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Historial de estrellas

<a href="https://star-history.dera.page/#getbindu/Bindu&Date">
  <img src="https://star-history.dera.page/svg?repos=getbindu/Bindu&type=Date" alt="Historial de estrellas">
</a>

<br/>

## Licencia

Apache 2.0. Mira [LICENSE.md](../LICENSE.md).

<p align="center">
  <em>"Creemos en la teoría del girasol — mantenernos en pie juntos, llevando esperanza y luz al Internet de los Agentes."</em>
</p>
