# 🌻 RAG Router Agent (Bindu)

## 🚀 Overview

A Bindu-native agent that performs Retrieval-Augmented Generation (RAG) with **intent-based routing and multi-agent delegation (A2A-style)** across multiple knowledge sources.

---

## 🧠 Features

* Intent classification (finance, legal, tech)
* Dynamic database routing
* Context retrieval (top-k)
* **Agent-to-agent delegation (router → domain agents)**
* LLM-based final response synthesis
* Structured response output (`answer`, `intent`, `agent_used`, `db_used`)

---

## ⚙️ How it works

```text
User Query
    ↓
Intent Detection
    ↓
DB Routing + Retrieval
    ↓
Router Agent
    ↓
 ┌───────────────┬───────────────┬───────────────┐
Finance Agent   Legal Agent     Tech Agent
    ↓               ↓               ↓
  Response        Response        Response
    ↓
LLM Refines → Final Answer
```

---

## 🧪 Example

**Query:**
`What is GST?`

**Response:**

```json
{
  "answer": "GST is a tax applied on goods and services...",
  "intent": "finance",
  "agent_used": "finance",
  "db_used": "db/finance.txt"
}
```

---

## ▶️ Run Locally

```bash
cd examples/rag_router_agent
python run_local.py
```

> Requires: `OPENROUTER_API_KEY`

---

## 🧩 Project Structure

```text
rag_router_agent/
│
├── agent.py              # Main handler (orchestration + LLM)
├── router.py             # Intent + routing logic
├── retriever.py          # Document retrieval
├── agents/               # Domain agents (A2A)
│   ├── finance_agent.py
│   ├── legal_agent.py
│   ├── tech_agent.py
│
├── db/                   # Sample knowledge bases
├── run_local.py         # Local testing script
└── README.md
```

---

## 💡 Why this matters

This agent demonstrates how Bindu agents can:

* Understand intent before acting
* Delegate tasks to specialized agents
* Coordinate across multiple components
* Act as **modular building blocks in multi-agent systems**

---

## 🔌 Bindu Integration

* Built using `bindufy()`
* Exposed via JSON-RPC (A2A protocol)
* Runs as a lightweight agent microservice
* Compatible with agent-to-agent communication patterns

---

## 🔥 Future Scope

* True A2A communication (agent ↔ agent via Bindu protocol)
* Vector database integration (FAISS / Chroma)
* Confidence-based hybrid routing
* Multi-agent response aggregation

---

## ✨ Key Idea

> Instead of a single agent answering everything,
> this system routes tasks to **specialized agents** and combines their outputs.

---
