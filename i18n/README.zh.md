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
        <b>中文</b> |
        <a href="README.nl.md">Nederlands</a> |
        <a href="README.ta.md">தமிழ்</a>
    </p>
</h4>

<h3 align="center">AI Agent 的身份、通信与支付层。</h3>

情况是这样的。你做了一个 agent，能跑。但要真正放它出去——与别的 agent 对话、证明自己是谁、为工作收钱——你就得自己接一大堆无聊的管道：集成一个 DID 库、搭一套 OAuth 流程、做支付中间件、再写一层 HTTP 来跟上当前 agent 圈子用的协议。

Bindu 把这一切管道塞进一次函数调用。你用 `bindufy()` 把你的 handler 包起来，几秒钟之后你的 agent 就在线了——拥有自己的加密身份，说着 [A2A](https://github.com/a2aproject/A2A)（别的 agent 已经在用的协议），并且做好准备在做任何事之前先要求在任意 EVM 链上付 USDC（[x402](https://github.com/coinbase/x402)）。你的 handler 仍然小到 `(messages) -> response`。Handler 里面用什么框架——Agno、LangChain、CrewAI，或者你自己写的——Bindu 不关心。

Bindu 有 Python、TypeScript、Kotlin 的 SDK，全都共享同一个 gRPC 内核。语言是个人选择，协议和身份不变。等你想往深里挖，[文档](https://docs.getbindu.com) 就是下一站。

## 安装

你需要 Python 3.12+ 和 [uv](https://github.com/astral-sh/uv)。

```bash
uv add bindu
```

如果你是要折腾 Bindu 本身，而不是只是使用：

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv sync --dev
```

要跑示例的话，至少需要一个 LLM 服务商的 API key——`OPENROUTER_API_KEY`、`OPENAI_API_KEY` 或 `MINIMAX_API_KEY`。

<br/>

## 快速开始

写好你想要的 agent，把它交给 `bindufy()`，它就在线了。下面这块就是全部——复制到一个文件里，设好你的 `OPENAI_API_KEY`，运行它。

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

Agent 现在已在 `http://localhost:3773` 在线运行。`expose: True` 会开一条 FRP 隧道，让外网可以直接访问，省去你自己配端口转发的麻烦。

<details>
<summary>TypeScript 等价写法</summary>

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

TypeScript SDK 会在后台启动 Python 内核——你看不见它，你自己的代码里也不需要任何 Python。同样的协议，同样的 DID。完整示例在 [`examples/typescript-openai-agent/`](../examples/typescript-openai-agent/)。

</details>

<details>
<summary>用 curl 调用 agent</summary>

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

然后用同一个 `taskId` 轮询 `tasks/get`，直到状态变成 `completed`。

</details>

<br/>

## 功能

下表每一行都指向真正展开讲的指南。

| 功能 | 它做什么 | 文档 |
|---|---|---|
| **A2A JSON-RPC** | 别的 agent 已经在用的协议。`message/send`、`tasks/get`、`message/stream`，端口 3773。 | — |
| **DID 身份** | 你的 agent 发出的每个响应都用 Ed25519 密钥签名。调用方通过 W3C DID 验证——没有可以泄漏的共享密钥。 | [DID.md](../docs/DID.md) |
| **通过 Hydra 的 OAuth2** | 带 scope 的 token（`agent:read`、`agent:write`、`agent:execute`），而不是一个开所有门的万能 bearer。 | [AUTHENTICATION.md](../docs/AUTHENTICATION.md) |
| **x402 支付** | 打开一个开关，agent 就会在你的 handler 看到请求之前先要求 USDC。**预置 5 条链**——Base、Base Sepolia、Ethereum、Ethereum Sepolia、SKALE Europa——任何其它 EVM 链（Polygon、Avalanche、Arbitrum、…）只需加一条 `extra_networks` 条目。 | [PAYMENT.md](../docs/PAYMENT.md) |
| **推送通知** | 任务状态变化时 agent 用 webhook 通知你。别再轮询了。 | [NOTIFICATIONS.md](../docs/NOTIFICATIONS.md) |
| **技能系统** | 声明你的 agent 能做什么；调用方在花一个 token 提问之前就能在 agent card 上看到。 | [SKILLS.md](../docs/SKILLS.md) |
| **私有技能** | 把你的商业技能描述挡在公共目录之外。公开的爬虫只看到一句通用的"我们做 X"——白名单上的合作伙伴 DID 会在第二个带鉴权的端点看到你真正的菜单。当你的技能描述本身就是你的产品路线图时特别有用。 | [PRIVATE_SKILLS.md](../docs/PRIVATE_SKILLS.md) |
| **Agent 协商** | 两个 agent 提前就价格、延迟和 SLA 谈拢。不会有惊喜账单。 | [NEGOTIATION.md](../docs/NEGOTIATION.md) |
| **存储** | 任务和消息走 Postgres。有偏好的话可以换后端。 | [STORAGE.md](../docs/STORAGE.md) |
| **调度器** | 基于 Redis 的重试、超时和循环任务。 | [SCHEDULER.md](../docs/SCHEDULER.md) |
| **公网隧道** | `expose: true` 把你的笔记本直接放到公网。不需要端口转发，不需要改路由器。 | [TUNNELING.md](../docs/TUNNELING.md) |
| **多语言 SDK** | Python、TypeScript、Kotlin——底下都是同一个 gRPC 内核、同样的 DID、同样的鉴权。 | [GRPC_LANGUAGE_AGNOSTIC.md](../docs/GRPC_LANGUAGE_AGNOSTIC.md) |
| **云部署** | `bindu deploy agent.py --runtime=boxd` 把你的脚本送进 microVM，并打印 HTTPS URL。不用 Dockerfile。 | [runtime/quickstart.md](../docs/runtime/quickstart.md) |
| **Gateway** | 一个 planner LLM，通过 A2A 调度一支 agent 舰队并把结果流式回传。 | [GATEWAY.md](../docs/GATEWAY.md) |
| **可观测性** | OpenTelemetry 链路、Sentry 错误、health 端点。凌晨两点救你命的那些"无聊"功能。 | [OBSERVABILITY.md](../docs/OBSERVABILITY.md) |

<br/>

## 演示

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu 演示视频" width="640" />
  </a>
</div>

[`inbox/`](../inbox/) 里还有一个 Gmail 风格的操作员收件箱。运行 `cd inbox && npm run dev`，然后打开 `http://localhost:3775`。

<br/>

## 示例

从 [`examples/`](../examples/) 里挑几个：

| 示例 | 它展示什么 |
|---|---|
| [Agent Swarm](../examples/agent_swarm/) | 一小群 Agno agent 互相把活儿往下传。 |
| [Premium Advisor](../examples/premium-advisor/) | x402 实战——调用方先付 USDC 才能让 agent 动起来。 |
| [Hermes via Bindu](../examples/hermes_agent/) | Nous Research 的 Hermes agent，用大约 90 行 bindufy。 |
| [Gateway Test Fleet](../examples/gateway_test_fleet/) | 五个 agent 加一个 gateway——多 agent 协作的全过程。 |
| [TypeScript OpenAI Agent](../examples/typescript-openai-agent/) | 纯 TS 的 agent，你 repo 里一行 Python 都没有。 |

还有 20 多个示例覆盖 CSV 分析、PDF 问答、语音转文字、网页抓取、多语种协作、博客写作等等。到 [`examples/`](../examples/) 里翻一翻。

<br/>

## 我们为什么造 Bindu

我们用 Bindu 在生产环境里构建 **Trade Compliance OS**——一个 agent 集群，处理 CBAM、EUDR、HS 编码、数字产品护照，让中小企业可以把咖啡、纺织品、钢材运过国境，而不必给律所开一张六位数的支票。这个集群里的每个 agent 都是 bindufied。协议、身份、支付通道——这些正是我们一开始就需要 Bindu 解决的问题。

如果你也做过沾边的 agent——海关单据、供应商审计、原材料采购、合规申报，任何相关方向——我们很想把它接进网络。[到 Discord 上找我们](https://discord.gg/3w5zuYUuwt) 聊聊。

<br/>

## 支持的框架

把你本来就喜欢写 agent 的工具带过来。Bindu 不关心 handler 里面是什么。

| 语言 | 此 repo 中测过的框架 |
|---|---|
| **Python** | [AG2](https://github.com/ag2ai/ag2)、[Agno](https://github.com/agno-agi/agno)、[CrewAI](https://github.com/joaomdmoura/crewAI)、[Hermes Agent](https://github.com/NousResearch/hermes-agent)、[LangChain](https://github.com/langchain-ai/langchain)、[LangGraph](https://github.com/langchain-ai/langgraph)、[Notte](https://github.com/nottelabs/notte) |
| **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node)、[LangChain.js](https://github.com/langchain-ai/langchainjs) |
| **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
| **其它任何语言** | 通过 [gRPC 内核](../docs/grpc/)——写一个新 SDK通常几百行就够。 |

只要你的模型服务商说 OpenAI 或 Anthropic 的 API 方言，就能跑——[OpenRouter](https://openrouter.ai/)、[OpenAI](https://platform.openai.com/)、[MiniMax](https://platform.minimaxi.com) 等等。

<br/>

## 文档

- [完整文档站点](https://docs.getbindu.com)
- [调用受保护的 agent](../docs/AUTHENTICATION.md) —— 带 DID 签名和 Hydra token 的鉴权流程，附可运行的 Python 客户端
- [云部署](../docs/runtime/quickstart.md) —— `bindu deploy` 走一遍
- [Gateway](../docs/GATEWAY.md) —— 多 agent 编排
- [私有技能](../docs/PRIVATE_SKILLS.md) —— 把商业菜单从公共目录里藏起来，只给白名单上的合作伙伴 DID 看
- [gRPC 架构](../docs/grpc/) —— 给想做新语言 SDK 的人
- [已知问题](../bugs/known-issues.md) —— 上生产之前先读
- [疑难排查](../docs/AUTHENTICATION.md#troubleshooting) —— 你会撞到的错和怎么绕过去

<br/>

## 测试

```bash
uv run pytest tests/unit/ -v                                    # 快速单测
uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC 端到端
uv run pytest -n auto --cov=bindu --cov-report=term-missing     # 完整套件
```

<br/>

## 贡献

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9 && source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

完整指南在 [`.github/contributing.md`](../.github/contributing.md)。日常大部分交流在 [Discord](https://discord.gg/3w5zuYUuwt) 上——欢迎来打个招呼。

<br/>

## 维护者

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

## 致谢

Bindu 站在很多优秀开源项目的肩膀上：

[FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

<br/>

## Star 历史

<a href="https://star-history.dera.page/#getbindu/Bindu&Date">
  <img src="https://star-history.dera.page/svg?repos=getbindu/Bindu&type=Date" alt="Star 历史">
</a>

<br/>

## 许可证

Apache 2.0。见 [LICENSE.md](../LICENSE.md)。

<p align="center">
  <em>"我们信奉向日葵理论——一同挺立，向 Agent 互联网带去希望与光。"</em>
</p>
