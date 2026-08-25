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
        <b>हिंदी</b> |
        <a href="README.bn.md">বাংলা</a> |
        <a href="README.zh.md">中文</a> |
        <a href="README.nl.md">Nederlands</a> |
        <a href="README.id.md">Bahasa Indonesia</a> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">AI एजेंट्स के लिए पहचान, संचार और भुगतान की परत।</h3>

स्थिति कुछ इस तरह है। आपने एक agent बनाया। वो काम करता है। लेकिन उसे सच में खुला छोड़ने के लिए — दूसरे agents से बात करना, ये साबित करना कि वो कौन है, और काम के बदले पैसे लेना — आपको एक भारी-भरकम और उबाऊ प्लंबिंग खुद करनी पड़ेगी। एक DID लाइब्रेरी जोड़ना। एक OAuth फ्लो खड़ा करना। पेमेंट के लिए मिडलवेयर। और एक HTTP परत जो वो प्रोटोकॉल बोले जो बाकी agent दुनिया अभी इस्तेमाल कर रही है।

Bindu यही पूरी प्लंबिंग है — एक फंक्शन कॉल के पीछे। आप अपने handler को `bindufy()` से लपेटते हैं, और कुछ सेकंडों में आपका agent ऑनलाइन है — अपनी क्रिप्टोग्राफिक पहचान के साथ, [A2A](https://github.com/a2aproject/A2A) (वो प्रोटोकॉल जो दूसरे agents पहले से बोल रहे हैं) बोलते हुए, और किसी भी काम से पहले किसी भी EVM चेन पर USDC मांगने के लिए तैयार ([x402](https://github.com/coinbase/x402))। आपका handler उतना ही छोटा रहता है — `(messages) -> response`। handler के अंदर जो भी framework हो — Agno, LangChain, CrewAI, या आपका अपना — Bindu को कोई फर्क नहीं पड़ता।

Python, TypeScript और Kotlin के SDK हैं, और सब का एक ही gRPC core है। भाषा एक चुनाव है; प्रोटोकॉल और पहचान वही रहते हैं। जब आप गहराई में जाने को तैयार हों, [docs](https://docs.getbindu.com) अगला पड़ाव है।

## इंस्टॉलेशन

आपको Python 3.12+ और [uv](https://github.com/astral-sh/uv) चाहिए होगा।

```bash
uv add bindu
```

अगर आप Bindu को सिर्फ इस्तेमाल करने के बजाय खुद उस पर काम कर रहे हैं:

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

उदाहरण चलाने के लिए कम-से-कम एक LLM प्रदाता का API key चाहिए — `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, या `MINIMAX_API_KEY`।

<br/>

## तुरंत शुरुआत

जो agent बनाना है बनाइए, उसे `bindufy()` को सौंप दीजिए, और वो ऑनलाइन है। नीचे का ब्लॉक ही पूरा है — इसे एक फाइल में कॉपी करें, अपना `OPENAI_API_KEY` सेट करें, और चला दें।

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

Agent अब `http://localhost:3773` पर लाइव है। `expose: True` एक FRP टनल खोलता है, ताकि बाकी इंटरनेट उस तक पहुँच सके बिना आपके पोर्ट फॉरवर्डिंग सेट किए।

<details>
<summary>TypeScript समतुल्य</summary>

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

TypeScript SDK Python core को बैकग्राउंड में चलाता है — आप उसे देखेंगे नहीं, और अपने codebase में Python की एक भी लाइन की ज़रूरत नहीं। वही प्रोटोकॉल, वही DID। पूरा उदाहरण [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/) में।

</details>

<details>
<summary>curl से agent को कॉल करना</summary>

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

फिर उसी `taskId` के साथ `tasks/get` पोल करें जब तक state `completed` न हो जाए।

</details>

<br/>

## फीचर्स

हर पंक्ति उस गाइड पर लिंक करती है जो वाकई गहराई में जाती है।

| फीचर | क्या करता है | Docs |
|---|---|---|
| **A2A JSON-RPC** | वो प्रोटोकॉल जो दूसरे agents पहले से बोलते हैं। `message/send`, `tasks/get`, `message/stream` — पोर्ट 3773 पर। | — |
| **DID पहचान** | आपका agent जो भी जवाब भेजता है उस पर Ed25519 key से हस्ताक्षर होते हैं। कॉल करने वाला W3C DID से सत्यापन करता है — कोई साझा secret नहीं है जो लीक हो सके। | [DID.md](../docs/DID.md) |
| **Hydra के ज़रिए OAuth2** | scoped tokens (`agent:read`, `agent:write`, `agent:execute`) — हर दरवाज़ा खोलने वाले एक bearer के बजाय। | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **x402 पेमेंट** | एक flag चालू करें और agent USDC माँगने लगेगा — इससे पहले कि आपका handler रिक्वेस्ट देखे भी। **5 chains पहले से कॉन्फ़िगर** — Base, Base Sepolia, Ethereum, Ethereum Sepolia, SKALE Europa — और कोई भी दूसरी EVM chain (Polygon, Avalanche, Arbitrum, …) एक `extra_networks` एंट्री में जुड़ जाती है। | [PAYMENT.md](../docs/PAYMENT.md) |
| **पुश नोटिफिकेशन** | जब टास्क की state बदलती है तो agent आपको webhook करता है। पोलिंग बंद कर दीजिए। | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **Skills सिस्टम** | घोषित कीजिए कि आपका agent क्या कर सकता है; कॉल करने वाला agent card पर ही देख लेता है — एक token खर्च करने से पहले। | [SKILLS.md](../docs/SKILLS.md) |
| **प्राइवेट skills** | अपनी कमर्शियल skill विवरण को सार्वजनिक कैटलॉग से बाहर रखें। पब्लिक crawlers एक सामान्य "हम X करते हैं" देखते हैं — allowlist पर मौजूद पार्टनर DIDs आपका असली मेन्यू दूसरे auth-गेटेड endpoint पर देखते हैं। जब आपकी skill विवरण ही आपका प्रोडक्ट रोडमैप है तब उपयोगी है। | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **एजेंट निगोशिएशन** | दो agents पहले से ही कीमत, लेटेंसी और SLA पर सहमत हो जाते हैं। कोई surprise बिल नहीं। | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **स्टोरेज** | tasks और messages के लिए Postgres। पसंद हो तो backend बदल लीजिए। | [STORAGE.md](../docs/STORAGE.md) |
| **शेड्यूलर** | Redis-समर्थित retries, timeouts और दोहराने वाले tasks। | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **पब्लिक टनल** | `expose: true` आपके लैपटॉप को इंटरनेट पर रख देता है। न पोर्ट फॉरवर्डिंग, न राउटर कॉन्फ़िग। | [TUNNELING.md](../docs/TUNNELING.md) |
| **पोलीग्लॉट SDKs** | Python, TypeScript, Kotlin — नीचे एक ही gRPC core, वही DID, वही auth। | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **क्लाउड डिप्लॉय** | `bindu deploy agent.py --runtime=boxd` आपका script एक microVM पर भेजता है और HTTPS URL प्रिंट कर देता है। कोई Dockerfile नहीं। | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | एक planner LLM जो A2A के ज़रिए agents की एक फ्लीट को orchestrate करता है और परिणाम को stream करके वापस भेजता है। | [GATEWAY.md](../docs/GATEWAY.md) |
| **ऑब्ज़र्वेबिलिटी** | OpenTelemetry traces, Sentry errors, एक health endpoint। वो उबाऊ सामान जो आपको रात के 2 बजे बचाता है। | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## डेमो

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu demo video" width="640" />
  </a>
</div>

[`inbox/`](../inbox/) में एक Gmail-शक्ल का operator inbox भी है। `cd inbox && npm run dev` चलाइए और `http://localhost:3775` खोलिए।

<br/>

## उदाहरण

[`examples/`](../examples/) में से कुछ:

| उदाहरण | क्या दिखाता है |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | Agno agents की एक छोटी मंडली जो आपस में काम पास करती है। |
| [Premium Advisor](../examples/premium-advisor/) | x402 असल काम में — कॉल करने वाले को कुछ शुरू होने से पहले USDC देना होता है। |
| [Hermes via Bindu](../examples/hermes_agent/) | Nous Research का Hermes agent, ~90 लाइनों में bindufied। |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | पाँच agents और एक gateway — multi-agent कहानी पूरी की पूरी। |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | सिर्फ TS का agent — आपके repo में Python की एक लाइन भी नहीं। |

CSV विश्लेषण, PDF Q&A, speech-to-text, web scraping, बहुभाषी सहयोग, ब्लॉग लेखन और बाकी पर 20+ और भी हैं। [`examples/`](../examples/) में टहलिए।

<br/>

## हमने Bindu क्यों बनाया

हम Bindu को प्रोडक्शन में इस्तेमाल कर रहे हैं **Trade Compliance OS** बनाने के लिए — agents का एक झुंड जो CBAM, EUDR, HS codes और Digital Product Passports संभालता है, ताकि एक SMB सीमाओं के पार कॉफ़ी, टेक्सटाइल या स्टील भेज सके — और इसके लिए किसी law firm को छह आँकड़ों का चेक न लिखना पड़े। उस झुंड का हर agent bindufied है। प्रोटोकॉल, पहचान, पेमेंट रेल्स — यही वो सब था जो हमें Bindu से सबसे पहले हल करवाना था।

अगर आपने ऐसा कोई agent बनाया है जो इनमें से किसी से जुड़ता है — कस्टम्स की कागज़ी कार्रवाई, supplier audits, materials sourcing, regulatory filings, कुछ भी पड़ोस का — तो हम उसे नेटवर्क में देखकर खुश होंगे। [Discord पर मिलिए](https://discord.gg/3w5zuYUuwt) — बात करते हैं।

<br/>

## समर्थित फ्रेमवर्क

जिसके साथ आप पहले से agents लिखना पसंद करते हैं, वही ले आइए। Handler के अंदर क्या है, Bindu को इससे फर्क नहीं पड़ता।

| भाषा | इस repo में टेस्ट किए गए frameworks |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2), [Agno](https://github.com/agno-agi/agno), [CrewAI](https://github.com/joaomdmoura/crewAI), [Hermes Agent](https://github.com/NousResearch/hermes-agent), [LangChain](https://github.com/langchain-ai/langchain), [LangGraph](https://github.com/langchain-ai/langgraph), [Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node), [LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **कोई भी और** | [gRPC core](../docs/grpc/) के ज़रिए — एक नया SDK आमतौर पर कुछ सौ लाइनों का होता है |

अगर आपका model provider OpenAI या Anthropic API बोलता है, तो काम कर जाता है — [OpenRouter](https://openrouter.ai/), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) और बाकी।

<br/>

## दस्तावेज़ीकरण

- [पूरा docs साइट](https://docs.getbindu.com)
- [सुरक्षित agent को कॉल करना](../docs/AUTHENTICATION.md) — DID signing और Hydra tokens वाला auth फ्लो, साथ में एक चलता-फिरता Python client
- [क्लाउड डिप्लॉयमेंट](../docs/runtime/quickstart.md) — `bindu deploy` का walkthrough
- [Gateway](../docs/GATEWAY.md) — multi-agent orchestration
- [प्राइवेट skills](../docs/PRIVATE_SKILLS.md) — अपना कमर्शियल मेन्यू पब्लिक कैटलॉग से छिपाइए; उसे सिर्फ allowlist पर मौजूद पार्टनर DIDs को दिखाइए
- [gRPC आर्किटेक्चर](../docs/grpc/) — नई भाषा का SDK बनाने वालों के लिए
- [ज्ञात समस्याएँ](../bugs/known-issues.md) — प्रोडक्शन पर भेजने से पहले पढ़िए
- [Troubleshooting](../docs/AUTHENTICATION.md#troubleshooting) — जिन गलतियों से टकराएँगे, और उनसे आगे कैसे निकलना है

<br/>

## टेस्टिंग

```bash
uv run pytest tests/unit/ -v                                    # तेज़ unit tests
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # पूरी suite
```

<br/>

## योगदान देना

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

पूरी गाइड [`.github/contributing.md`](../.github/contributing.md) में है। ज़्यादातर रोज़मर्रा की बातचीत [Discord](https://discord.gg/3w5zuYUuwt) पर होती है — आइए, नमस्ते कह जाइए।

<br/>

## मेंटेनर्स

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

## आभार

Bindu बहुत सारे अच्छे open source के कंधों पर खड़ा है:

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Star का इतिहास

<a href="https://star-history.com/#getbindu/Bindu&Date">
  <img src="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date" alt="Star का इतिहास">
</a>

<br/>

## लाइसेंस

Apache 2.0। [LICENSE.md](../LICENSE.md) देखें।

<p align="center">
  <em>"हम सूरजमुखी सिद्धांत में विश्वास करते हैं — एक साथ तन कर खड़े होकर, Agents के इंटरनेट में आशा और रोशनी लाते हैं।"</em>
</p>
