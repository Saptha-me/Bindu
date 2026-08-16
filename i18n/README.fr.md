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
        <b>Français</b> |
        <a href="README.hi.md">हिंदी</a> |
        <a href="README.bn.md">বাংলা</a> |
        <a href="README.zh.md">中文</a> |
        <a href="README.nl.md">Nederlands</a> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">La couche identité, communication et paiements pour les agents IA.</h3>

Voilà la situation. Tu as construit un agent. Il fonctionne. Mais pour vraiment le lâcher dans la nature — parler à d'autres agents, prouver qui il est, encaisser de l'argent pour son travail — tu serais bon pour pas mal de plomberie barbante. Intégrer une bibliothèque DID. Mettre en place un flux OAuth. Une middleware de paiement. Une couche HTTP qui suit le protocole que le reste du monde des agents utilise.

Bindu, c'est toute cette plomberie, derrière un seul appel de fonction. Tu emballes ton handler avec `bindufy()`, et quelques secondes plus tard ton agent est en ligne — avec sa propre identité cryptographique, parlant [A2A](https://github.com/a2aproject/A2A) (le protocole que les autres agents utilisent déjà), et prêt à exiger des USDC sur n'importe quelle chaîne EVM avant de bouger le moindre doigt ([x402](https://github.com/coinbase/x402)). Ton handler reste aussi petit que `(messages) -> response`. Le framework à l'intérieur du handler — Agno, LangChain, CrewAI, ton truc à toi — Bindu s'en fiche.

Il y a des SDK pour Python, TypeScript et Kotlin, et tous partagent le même cœur gRPC. Le langage est un choix ; le protocole et l'identité, eux, sont identiques de toute façon. Quand tu es prêt à aller plus loin, les [docs](https://docs.getbindu.com) sont la prochaine étape.

## Installation

Il te faut Python 3.12+ et [uv](https://github.com/astral-sh/uv).

```bash
uv add bindu
```

Si tu bricoles Bindu lui-même au lieu de simplement l'utiliser :

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

Pour faire tourner les exemples, il faut une clé d'API pour au moins un fournisseur de LLM — `OPENROUTER_API_KEY`, `OPENAI_API_KEY` ou `MINIMAX_API_KEY`.

<br/>

## Démarrage rapide

Construis l'agent que tu veux, passe-le à `bindufy()`, et il est en ligne. Le bloc ci-dessous, c'est tout — copie-le dans un fichier, mets ta `OPENAI_API_KEY`, lance-le.

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

L'agent est maintenant en ligne sur `http://localhost:3773`. `expose: True` ouvre un tunnel FRP pour que le reste d'internet puisse l'atteindre sans que tu touches à du port forwarding.

<details>
<summary>Équivalent TypeScript</summary>

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

Le SDK TypeScript lance le cœur Python en arrière-plan — tu ne le vois pas, et tu n'as pas besoin d'une ligne de Python dans ton propre code. Même protocole, même DID. Exemple complet dans [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/).

</details>

<details>
<summary>Appeler l'agent avec curl</summary>

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

Ensuite, fais du polling sur `tasks/get` avec le même `taskId` jusqu'à ce que l'état atteigne `completed`.

</details>

<br/>

## Fonctionnalités

Chaque ligne pointe vers le guide qui rentre vraiment dans le détail.

| Fonctionnalité | Ce qu'elle fait | Docs |
|---|---|---|
| **A2A JSON-RPC** | Le protocole que les autres agents parlent déjà. `message/send`, `tasks/get`, `message/stream` sur le port 3773. | — |
| **Identité DID** | Chaque réponse que ton agent envoie est signée avec une clé Ed25519. Les appelants vérifient avec un DID W3C — pas de secret partagé qui puisse fuiter. | [DID.md](../docs/DID.md) |
| **OAuth2 via Hydra** | Des tokens scopés (`agent:read`, `agent:write`, `agent:execute`) au lieu d'un seul bearer qui ouvre toutes les portes. | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **Paiements x402** | Tu actives un flag et l'agent exige des USDC avant même que ton handler voie la requête. **5 chaînes préconfigurées** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — et n'importe quelle autre chaîne EVM (Polygon, Avalanche, Arbitrum, …) tient en une entrée `extra_networks`. | [PAYMENT.md](../docs/PAYMENT.md) |
| **Notifications push** | L'agent te webhook quand une tâche change d'état. Arrête de poller. | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Système de skills** | Déclare ce que ton agent sait faire ; les appelants le voient sur l'agent card avant de dépenser un token pour demander. | [SKILLS.md](../docs/SKILLS.md) |
| **Skills privées** | Garde tes descriptions de skills commerciales hors du catalogue public. Les crawlers publics voient un "on fait X" générique — les DID de partenaires sur l'allowlist voient ton vrai menu sur un second endpoint protégé par auth. Utile quand tes descriptions de skills SONT ta roadmap produit. | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **Négociation entre agents** | Deux agents s'accordent à l'avance sur le prix, la latence et le SLA. Pas de factures surprises. | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **Stockage** | Postgres pour les tâches et les messages. Change le backend si tu as une préférence. | [STORAGE.md](../docs/STORAGE.md) |
| **Scheduler** | Retries, timeouts et tâches récurrentes adossés à Redis. | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **Tunnel public** | `expose: true` met ton portable sur internet. Pas de port forwarding, pas de config routeur. | [TUNNELING.md](../docs/TUNNELING.md) |
| **SDK polyglottes** | Python, TypeScript, Kotlin — le même cœur gRPC en dessous, le même DID, la même auth. | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **Déploiement cloud** | `bindu deploy agent.py --runtime=boxd` envoie ton script dans une microVM et te sort l'URL HTTPS. Pas de Dockerfile. | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | Un LLM-planificateur qui orchestre une flotte d'agents via A2A et te renvoie le résultat en streaming. | [GATEWAY.md](../docs/GATEWAY.md) |
| **Observabilité** | Traces OpenTelemetry, erreurs Sentry, un endpoint health. Le truc ennuyeux qui te sauve à 2h du matin. | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## Démo

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Vidéo démo Bindu" width="640" />
  </a>
</div>

Il y a aussi une boîte de réception opérateur façon Gmail dans [`inbox/`](../inbox/). Lance `cd inbox && npm run dev` et ouvre `http://localhost:3775`.

<br/>

## Exemples

Quelques-uns parmi [`examples/`](../examples/) :

| Exemple | Ce qu'il montre |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Une petite société d'agents Agno qui se passent du travail. |
| [Premium Advisor](../examples/premium-advisor/) | x402 en pratique — l'appelant doit payer des USDC avant que rien ne tourne. |
| [Hermes via Bindu](../examples/hermes_agent/) | L'agent Hermes de Nous Research, bindufié en ~90 lignes. |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | Cinq agents et un gateway — l'histoire multi-agent de bout en bout. |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | Un agent en TS uniquement, zéro Python dans ton repo. |

Il y en a 20+ de plus couvrant l'analyse CSV, le Q&A sur PDF, le speech-to-text, le web scraping, la collaboration multilingue, l'écriture de blog, etc. Parcours-les dans [`examples/`](../examples/).

<br/>

## Pourquoi on a construit Bindu

On utilise Bindu en production pour construire le **Trade Compliance OS** — un essaim d'agents qui gère CBAM, EUDR, codes HS et Passeports Numériques de Produit, pour qu'une PME puisse expédier du café, du textile ou de l'acier au-delà des frontières sans signer un chèque à six chiffres à un cabinet d'avocats. Chaque agent de cet essaim est bindufié. Le protocole, l'identité, les rails de paiement — c'est exactement ce qu'on avait besoin que Bindu résolve au départ.

Si tu as construit un agent qui touche à un de ces trucs — paperasse douanière, audits fournisseurs, sourcing matériaux, déclarations réglementaires, n'importe quoi dans le voisinage — on serait ravi de l'avoir dans le réseau. [Viens nous trouver sur Discord](https://discord.gg/3w5zuYUuwt), on en parle.

<br/>

## Frameworks supportés

Apporte ce que tu aimes déjà pour écrire des agents. Bindu se fiche de ce qu'il y a dans le handler.

| Langage | Frameworks testés dans ce repo |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **N'importe quel autre** | via le [cœur gRPC](../docs/grpc/) — un nouveau SDK fait en général quelques centaines de lignes |

Si ton fournisseur de modèles parle l'API OpenAI ou Anthropic, ça marche — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) et les autres.

<br/>

## Documentation

- [Site de docs complet](https://docs.getbindu.com)
- [Appeler un agent sécurisé](../docs/AUTHENTICATION.md) — le flux d'auth avec signature DID et tokens Hydra, avec un client Python qui marche
- [Déploiement cloud](../docs/runtime/quickstart.md) — walkthrough de `bindu deploy`
- [Gateway](../docs/GATEWAY.md) — orchestration multi-agent
- [Skills privées](../docs/PRIVATE_SKILLS.md) — cache ton menu commercial du catalogue public ; ne le montre qu'aux DID de partenaires sur l'allowlist
- [Architecture gRPC](../docs/grpc/) — pour quiconque construit un SDK dans un nouveau langage
- [Problèmes connus](../bugs/known-issues.md) — à lire avant de mettre en prod
- [Dépannage](../docs/AUTHENTICATION.md#troubleshooting) — les erreurs que tu vas voir, et comment t'en sortir

<br/>

## Tests

```bash
uv run pytest tests/unit/ -v                                    # tests unitaires rapides
uv run pytest tests/integration/grpc/ -v -m e2e                 # E2E gRPC
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # suite complète
```

<br/>

## Contribuer

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

Le guide complet est dans [`.github/contributing.md`](../.github/contributing.md). Le plus gros des échanges du quotidien se passe sur [Discord](https://discord.gg/3w5zuYUuwt) — viens dire bonjour.

<br/>

## Mainteneurs

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

## Remerciements

Bindu se tient sur les épaules de beaucoup de bon open source :

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Historique des étoiles

<a href="https://star-history.dera.page/#getbindu/Bindu&Date">
  <img src="https://star-history.dera.page/svg?repos=getbindu/Bindu&type=Date" alt="Historique des étoiles">
</a>

<br/>

## Licence

Apache 2.0. Voir [LICENSE.md](../LICENSE.md).

<p align="center">
  <em>« Nous croyons à la théorie du tournesol — se tenir droits ensemble, apporter espoir et lumière à l'Internet des Agents. »</em>
</p>
