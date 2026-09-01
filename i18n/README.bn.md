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
        <b>বাংলা</b> |
        <a href="README.zh.md">中文</a> |
        <a href="README.nl.md">Nederlands</a> |
        <a href="README.id.md">Bahasa Indonesia</a> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">AI এজেন্টদের জন্য পরিচয়, যোগাযোগ ও পেমেন্টের স্তর।</h3>

পরিস্থিতিটা এমন। আপনি একটা agent বানিয়েছেন। সে কাজও করছে। কিন্তু তাকে সত্যিই ছেড়ে দিতে চাইলে — অন্য agents-এর সাথে কথা বলা, সে কে তা প্রমাণ করা, কাজের বিনিময়ে টাকা নেওয়া — আপনাকে অনেক বিরক্তিকর প্লাম্বিং নিজে করতে হবে। একটা DID লাইব্রেরি বসানো। একটা OAuth ফ্লো দাঁড় করানো। পেমেন্ট মিডলওয়্যার। একটা HTTP লেয়ার যেটা agent দুনিয়ার বাকিরা যে protocol-ই ব্যবহার করছে সেটাই বলে।

Bindu হল এই পুরো প্লাম্বিং — মাত্র একটা ফাংশন কলের পেছনে। আপনি আপনার handler-কে `bindufy()` দিয়ে মুড়ে দেন, আর কয়েক সেকেন্ডের মধ্যে আপনার agent অনলাইন — নিজের ক্রিপ্টোগ্রাফিক পরিচয় নিয়ে, [A2A](https://github.com/a2aproject/A2A) (যে protocol অন্যান্য agents আগে থেকেই বলে) ভাষায় কথা বলতে বলতে, এবং কোনো কাজ শুরুর আগেই যেকোনো EVM চেইনে USDC দাবি করার জন্য তৈরি ([x402](https://github.com/coinbase/x402))। আপনার handler থাকে ঠিক ততটাই ছোট — `(messages) -> response`। handler-এর ভেতরে কোন framework — Agno, LangChain, CrewAI, নাকি আপনার নিজের — Bindu-র কিছু আসে যায় না।

Python, TypeScript, Kotlin-এর SDK আছে, এবং সবাই একই gRPC core ভাগ করে নেয়। ভাষাটা একটা পছন্দ; protocol আর পরিচয় যেকোনোভাবেই এক। যখন আরও গভীরে যেতে চাইবেন, [docs](https://docs.getbindu.com) পরের গন্তব্য।

## ইনস্টলেশন

আপনাকে Python 3.12+ এবং [uv](https://github.com/astral-sh/uv) লাগবে।

```bash
uv add bindu
```

যদি আপনি Bindu শুধু ব্যবহার নয়, Bindu-র ভেতরেই কাজ করছেন:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

উদাহরণগুলো চালাতে অন্তত একটা LLM প্রোভাইডারের API key লাগবে — `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, অথবা `MINIMAX_API_KEY`।

<br/>

## কুইকস্টার্ট

যে agent বানাতে চান তা বানান, `bindufy()`-এর হাতে দিন, ব্যাস সে অনলাইন। নিচের ব্লকটাই পুরো জিনিস — একটা ফাইলে কপি করুন, আপনার `OPENAI_API_KEY` সেট করুন, চালান।

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

Agent এখন `http://localhost:3773`-এ লাইভ। `expose: True` একটা FRP টানেল খুলে দেয়, যাতে বাকি ইন্টারনেট port forwarding না সেট করেই তার কাছে পৌঁছাতে পারে।

<details>
<summary>TypeScript সমতুল্য</summary>

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

TypeScript SDK ব্যাকগ্রাউন্ডে Python core চালু করে — আপনি তাকে দেখবেন না, এবং আপনার নিজের codebase-এ Python-এর একটাও লাইন লাগবে না। একই protocol, একই DID। পূর্ণ উদাহরণ [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/) এ।

</details>

<details>
<summary>curl দিয়ে agent-কে কল করা</summary>

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

তারপর একই `taskId` দিয়ে `tasks/get` poll করুন যতক্ষণ না state `completed`-এ পৌঁছায়।

</details>

<br/>

## ফিচার

প্রতিটা সারি গাইডে লিংক করছে যেখানে আসলে বিস্তারে আলোচনা আছে।

| ফিচার | কী করে | Docs |
|---|---|---|
| **A2A JSON-RPC** | অন্যান্য agents যে protocol-ই আগে থেকে বলে। `message/send`, `tasks/get`, `message/stream` — পোর্ট 3773-এ। | — |
| **DID পরিচয়** | আপনার agent যে উত্তরই পাঠায় তাতে Ed25519 key দিয়ে সাইন করা থাকে। কল করা পক্ষ W3C DID দিয়ে যাচাই করে — কোনো শেয়ার করা secret নেই যা ফাঁস হতে পারে। | [DID.md](../docs/DID.md) |
| **Hydra-র মাধ্যমে OAuth2** | scoped token (`agent:read`, `agent:write`, `agent:execute`) — সব দরজা খোলে এমন একটাই bearer-এর বদলে। | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **x402 পেমেন্ট** | একটা flag চালু করুন, agent USDC দাবি করতে শুরু করবে — আপনার handler request দেখার আগেই। **৫টা চেইন আগে থেকে কনফিগার করা** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — আর অন্য যেকোনো EVM চেইন (Polygon, Avalanche, Arbitrum, …) একটা `extra_networks` এন্ট্রিতে ধরে যায়। | [PAYMENT.md](../docs/PAYMENT.md) |
| **পুশ নোটিফিকেশন** | টাস্কের state বদলালে agent আপনাকে webhook করে। polling বন্ধ করুন। | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Skills সিস্টেম** | ঘোষণা করুন আপনার agent কী করতে পারে; কল করা পক্ষ একটা token খরচের আগেই agent card-এ দেখে নেয়। | [SKILLS.md](../docs/SKILLS.md) |
| **প্রাইভেট skills** | আপনার বাণিজ্যিক skill বিবরণ পাবলিক ক্যাটালগের বাইরে রাখুন। পাবলিক crawler একটা সাধারণ "আমরা X করি" দেখে — allowlist-এ থাকা পার্টনার DID-রা আপনার আসল মেন্যু দেখে দ্বিতীয় auth-গেটেড endpoint-এ। যখন আপনার skill বিবরণ-ই আপনার প্রোডাক্ট রোডম্যাপ, তখন কাজে লাগে। | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **এজেন্ট নেগোসিয়েশন** | দুই agent দাম, latency আর SLA নিয়ে আগেই একমত হয়ে নেয়। কোনো surprise bill নেই। | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **স্টোরেজ** | task আর message-এর জন্য Postgres। পছন্দ হলে backend বদলে নিন। | [STORAGE.md](../docs/STORAGE.md) |
| **শিডিউলার** | Redis-ভিত্তিক retry, timeout আর পুনরাবৃত্ত task। | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **পাবলিক টানেল** | `expose: true` আপনার ল্যাপটপকে ইন্টারনেটে এনে দাঁড় করায়। port forwarding না, router কনফিগও না। | [TUNNELING.md](../docs/TUNNELING.md) |
| **পলিগ্লট SDK** | Python, TypeScript, Kotlin — নিচে একই gRPC core, একই DID, একই auth। | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **ক্লাউড ডিপ্লয়** | `bindu deploy agent.py --runtime=boxd` আপনার স্ক্রিপ্টকে একটা microVM-এ পাঠায় এবং HTTPS URL ছেপে দেয়। কোনো Dockerfile নেই। | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | একটা planner LLM যেটা A2A-র মাধ্যমে agent-এর একটা বহরকে অর্কেস্ট্রেট করে এবং ফলাফল স্ট্রিম করে ফিরিয়ে দেয়। | [GATEWAY.md](../docs/GATEWAY.md) |
| **অবজার্ভেবিলিটি** | OpenTelemetry trace, Sentry error, একটা health endpoint। যে বিরক্তিকর জিনিসগুলো রাত ২টায় আপনাকে বাঁচায়। | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## ডেমো

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu demo video" width="640" />
  </a>
</div>

[`inbox/`](../inbox/)-এ একটা Gmail-আকৃতির operator inbox-ও আছে। `cd inbox && npm run dev` চালান আর `http://localhost:3775` খুলুন।

<br/>

## উদাহরণ

[`examples/`](../examples/) থেকে কিছু:

| উদাহরণ | কী দেখায় |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Agno agents-এর একটা ছোট সমাজ, যারা একে অপরকে কাজ পাচার করে। |
| [Premium Advisor](../examples/premium-advisor/) | x402 বাস্তবে — কল করা পক্ষকে কিছু শুরু হওয়ার আগে USDC দিতে হয়। |
| [Hermes via Bindu](../examples/hermes_agent/) | Nous Research-এর Hermes agent, ~৯০ লাইনে bindufied। |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | পাঁচটা agent আর একটা gateway — multi-agent গল্প পুরোটা। |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | শুধু TS-এর agent — আপনার repo-তে এক লাইন Python নেই। |

CSV বিশ্লেষণ, PDF Q&A, speech-to-text, web scraping, বহুভাষিক সহযোগিতা, blog লেখা — এসব নিয়ে ২০+ আরও আছে। [`examples/`](../examples/)-এ ঘুরে দেখুন।

<br/>

## আমরা Bindu কেন বানিয়েছি

আমরা Bindu প্রোডাকশনে ব্যবহার করছি **Trade Compliance OS** বানাতে — agent-দের একটা ঝাঁক যেটা CBAM, EUDR, HS কোড আর Digital Product Passport সামলায়, যাতে একটা SMB কফি, টেক্সটাইল বা ইস্পাত সীমান্ত পার করে পাঠাতে পারে — কোনো ল ফার্মকে ছ-অঙ্কের চেক না লিখেই। সেই ঝাঁকের প্রতিটা agent bindufied। protocol, পরিচয়, পেমেন্ট রেল — Bindu-কে দিয়ে আমাদের প্রথমেই এগুলোই সমাধান করাতে হয়েছিল।

আপনি যদি এমন কোনো agent বানিয়ে থাকেন যেটা এই সবের সাথে ছোঁয়া রাখে — কাস্টমস কাগজপত্র, supplier audit, materials sourcing, regulatory filing — পাশের যেকোনো কিছু — আমরা তাকে নেটওয়ার্কে চাই। [Discord-এ এসে আমাদের খুঁজুন](https://discord.gg/3w5zuYUuwt) — কথা বলি।

<br/>

## সমর্থিত ফ্রেমওয়ার্ক

যে দিয়ে আপনি আগে থেকেই agent লিখতে ভালোবাসেন, সেটাই নিয়ে আসুন। handler-এর ভেতরে কী আছে, Bindu-র সেটা নিয়ে মাথাব্যথা নেই।

| ভাষা | এই repo-তে যাচাই করা framework |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **অন্য যেকোনো** | [gRPC core](../docs/grpc/)-র মাধ্যমে — নতুন একটা SDK সাধারণত কয়েকশো লাইনের কাজ |

আপনার model provider যদি OpenAI বা Anthropic API বলে, তাহলে চলে — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) এবং বাকিরা।

<br/>

## ডকুমেন্টেশন

- [পূর্ণ docs সাইট](https://docs.getbindu.com)
- [একটা সুরক্ষিত agent-কে কল করা](../docs/AUTHENTICATION.md) — DID signing আর Hydra token-সহ auth ফ্লো, সঙ্গে চলমান একটা Python ক্লায়েন্ট
- [ক্লাউড ডিপ্লয়মেন্ট](../docs/runtime/quickstart.md) — `bindu deploy` walkthrough
- [Gateway](../docs/GATEWAY.md) — multi-agent অর্কেস্ট্রেশন
- [প্রাইভেট skills](../docs/PRIVATE_SKILLS.md) — আপনার বাণিজ্যিক মেন্যু পাবলিক ক্যাটালগ থেকে লুকান; শুধু allowlist-এর পার্টনার DID-দের দেখান
- [gRPC স্থাপত্য](../docs/grpc/) — যারা নতুন ভাষার SDK বানাচ্ছেন তাদের জন্য
- [জানা সমস্যা](../bugs/known-issues.md) — প্রোডাকশনে দেওয়ার আগে পড়ুন
- [Troubleshooting](../docs/AUTHENTICATION.md#troubleshooting) — যেসব এরর-এ ঠুকবেন, এবং সেগুলোর পাশ কাটানোর উপায়

<br/>

## টেস্টিং

```bash
uv run pytest tests/unit/ -v                                    # দ্রুত ইউনিট টেস্ট
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # সম্পূর্ণ suite
```

<br/>

## অবদান

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

সম্পূর্ণ গাইড [`.github/contributing.md`](../.github/contributing.md)-এ। প্রতিদিনের বেশিরভাগ আলাপ-আলোচনা [Discord](https://discord.gg/3w5zuYUuwt)-এ — এসে হাই বলে যান।

<br/>

## মেইনটেইনার

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

## কৃতজ্ঞতা

Bindu অনেক ভালো open source-এর কাঁধে দাঁড়িয়ে আছে:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Star ইতিহাস

<a href="https://star-history.com/#getbindu/Bindu&Date">
  <img src="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date" alt="Star ইতিহাস">
</a>

<br/>

## লাইসেন্স

Apache 2.0। [LICENSE.md](../LICENSE.md) দেখুন।

<p align="center">
  <em>"আমরা সূর্যমুখী তত্ত্বে বিশ্বাস করি — একসাথে সোজা দাঁড়িয়ে, Agent-এর ইন্টারনেটে আশা আর আলো বয়ে আনতে।"</em>
</p>
