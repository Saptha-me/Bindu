---

name: rag-agent
description: Answer questions using retrieval augmented generation via FAISS and OpenRouter
-------------------------------------------------------------------------------------------

# RAG Agent Skill

## Overview

Retrieve relevant document chunks using embeddings and FAISS, then generate grounded answers using the platform model provider (OpenRouter).

## Inputs

* User question
* Optional knowledge source

## Execution Contract

1. Split documents into chunks
2. Generate embeddings (bge-small)
3. Store and search via FAISS
4. Retrieve top-k context
5. Generate answer using OpenRouter

## Guardrails

* Answer only from retrieved context
* Prefer concise grounded responses

## Output Format

```json
{
  "answer": "final grounded answer"
}
```

## Example Usage

/skill rag-agent "What is LangChain?"
