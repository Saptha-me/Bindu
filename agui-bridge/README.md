# Bindu AG-UI Bridge

> Translates AG-UI protocol events ↔ Bindu A2A JSON-RPC

## Overview

The AG-UI Bridge is a lightweight Bun service that:

1. **Accepts AG-UI Run Requests** from an Inspector UI (React frontend)
2. **Translates** them into Bindu JSON-RPC calls (`message/send`)
3. **Polls** Bindu for task state transitions (`tasks/get`)
4. **Streams AG-UI Events** back to the frontend via SSE (Server-Sent Events)

## Quick Start

### Prerequisites

- [Bun](https://bun.sh/) runtime installed
- A running Bindu agent on localhost:3773 (or configure via env)

### Installation

```bash
bun install
```

### Development

```bash
bun run dev
```

### Production

```bash
bun run start
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `BINDU_URL` | Base URL of the Bindu agent | `http://localhost:3773` |
| `PORT` | Bridge server port | `8080` |
| `POLL_INTERVAL_MS` | Task polling interval (ms) | `500` |
| `REQUEST_TIMEOUT_MS` | Timeout for Bindu requests (ms) | `30000` |
| `MAX_POLL_ATTEMPTS` | Maximum polling attempts before timeout | `120` |

## API Endpoints

### `GET /`

Returns bridge info and available endpoints.

### `GET /health`

Health check endpoint.

```json
{
  "status": "ok",
  "bindu_url": "http://localhost:3773",
  "bindu_reachable": true,
  "timestamp": "2024-12-23T15:30:00Z"
}
```

### `POST /agui/run`

Initiates an AG-UI run by translating the request to Bindu and streaming events.

**Request:**

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440038",
  "messages": [
    { "role": "user", "content": "Hello agent, provide a sunset quote" }
  ]
}
```

**Response:** SSE stream with AG-UI events:

```
event: RUN_STARTED
data: {"type":"RUN_STARTED","thread_id":"abc...","run_id":"xyz...","timestamp":1703353200}

event: STATE_DELTA
data: {"type":"STATE_DELTA","thread_id":"abc...","run_id":"xyz...","delta":{"bindu_state":"working"}}

event: TEXT_MESSAGE_START
data: {"type":"TEXT_MESSAGE_START","thread_id":"abc...","run_id":"xyz...","message_id":"msg-123","role":"assistant"}

event: TEXT_MESSAGE_CONTENT
data: {"type":"TEXT_MESSAGE_CONTENT","message_id":"msg-123","content":"The sunset paints hope..."}

event: TEXT_MESSAGE_END
data: {"type":"TEXT_MESSAGE_END","message_id":"msg-123"}

event: RUN_FINISHED
data: {"type":"RUN_FINISHED","thread_id":"abc...","run_id":"xyz...","timestamp":1703353205}
```

### `GET /agui/runs`

List recent runs (optional feature).

**Query Parameters:**
- `thread_id` - Filter by thread ID
- `limit` - Maximum results (default: 10)

## Project Structure

```
agui-bridge/
├── src/
│   ├── index.ts              # Hono app entry point
│   ├── config.ts             # Environment configuration
│   ├── routes/
│   │   ├── agui.ts           # /agui/* route handlers
│   │   └── health.ts         # /health route
│   ├── clients/
│   │   └── bindu.ts          # BinduClient class
│   ├── events/
│   │   ├── types.ts          # AG-UI event type definitions
│   │   ├── builder.ts        # AGUIEventBuilder class
│   │   └── sse.ts            # SSE formatting utilities
│   ├── handlers/
│   │   └── run.ts            # Main run handler logic
│   └── utils/
│       ├── errors.ts         # Custom error classes
│       └── sleep.ts          # Async utilities
├── package.json
├── tsconfig.json
└── README.md
```

## AG-UI Event Types

| Event Type | Description |
|------------|-------------|
| `RUN_STARTED` | Run has started |
| `RUN_FINISHED` | Run completed successfully |
| `RUN_ERROR` | Run encountered an error |
| `STATE_DELTA` | Bindu task state changed |
| `TEXT_MESSAGE_START` | Beginning of assistant message |
| `TEXT_MESSAGE_CONTENT` | Content of assistant message |
| `TEXT_MESSAGE_END` | End of assistant message |

## Concept Mapping

| AG-UI Concept | Bindu Equivalent |
|---------------|------------------|
| `thread_id` | `contextId` |
| `run_id` | `taskId` |
| `messages` | `message.parts` |
| `RUN_STARTED` | Task `submitted` |
| `RUN_FINISHED` | Task `completed` |
| `RUN_ERROR` | Task `failed` |

## License

MIT
