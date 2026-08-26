# Bindu AG-UI Bridge — Low-Level Specification

> **Version**: 1.0.0  
> **Stack**: Bun + Hono  
> **Purpose**: Translate AG-UI protocol events ↔ Bindu A2A JSON-RPC

---

## 1. Overview

The AG-UI Bridge is a lightweight Bun service that:

1. **Accepts AG-UI Run Requests** from an Inspector UI (React frontend)
2. **Translates** them into Bindu JSON-RPC calls (`message/send`)
3. **Polls** Bindu for task state transitions (`tasks/get`)
4. **Streams AG-UI Events** back to the frontend via SSE (Server-Sent Events)

```
┌─────────────────────┐
│   Inspector UI      │
│   (React + AG-UI)   │
└──────────┬──────────┘
           │ POST /agui/run (AG-UI Run Request)
           │ SSE Stream (AG-UI Events)
           ▼
┌─────────────────────┐
│ Bindu AG-UI Bridge  │
│   (Bun + Hono)      │
└──────────┬──────────┘
           │ POST / (JSON-RPC)
           │  - message/send
           │  - tasks/get
           ▼
┌─────────────────────┐
│   Bindu Agent       │
│   (A2A Protocol)    │
└─────────────────────┘
```

---

## 2. Configuration

### 2.1 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BINDU_URL` | Base URL of the Bindu agent | `http://localhost:3773` |
| `PORT` | Bridge server port | `8080` |
| `POLL_INTERVAL_MS` | Task polling interval (ms) | `500` |
| `REQUEST_TIMEOUT_MS` | Timeout for Bindu requests (ms) | `30000` |
| `MAX_POLL_ATTEMPTS` | Maximum polling attempts before timeout | `120` |

### 2.2 Configuration Schema

```typescript
interface BridgeConfig {
  binduUrl: string;
  port: number;
  pollIntervalMs: number;
  requestTimeoutMs: number;
  maxPollAttempts: number;
}
```

---

## 3. Concept Mapping: AG-UI ↔ Bindu

| AG-UI Concept | Bindu Equivalent | Notes |
|---------------|------------------|-------|
| `thread_id` | `contextId` | Conversation context identifier |
| `run_id` | `taskId` | Individual task/run identifier |
| `messages` | `message.parts` | User message content |
| `RUN_STARTED` | Task `submitted` | Task created and queued |
| `RUN_FINISHED` | Task `completed` | Task successfully completed |
| `RUN_ERROR` | Task `failed` | Task execution failed |
| `STATE_DELTA` | Task state change | `submitted` → `working` → `completed` |
| `TEXT_MESSAGE_*` | `task.artifacts` | Agent output content |
| `TOOL_CALL_*` | Future: skill/tool logs | Not yet exposed by Bindu |

### 3.1 Bindu Task States

```typescript
type BinduTaskState = 
  | 'submitted'     // Task created, queued for execution
  | 'working'       // Task is being processed
  | 'input-required' // Agent needs user input
  | 'auth-required'  // Authentication needed
  | 'completed'      // Task finished successfully
  | 'canceled'       // Task was canceled
  | 'failed';        // Task execution failed

// Terminal states (stop polling)
const TERMINAL_STATES = ['completed', 'canceled', 'failed'];
```

---

## 4. API Specification

### 4.1 Endpoint: `POST /agui/run`

Initiates an AG-UI run by translating the request to Bindu and streaming events.

#### Request

```typescript
interface AGUIRunRequest {
  thread_id: string;        // Maps to Bindu contextId
  run_id?: string;          // Optional, auto-generated if not provided
  messages: AGUIMessage[];  // User messages to send
  config?: {
    polling_interval_ms?: number;
    timeout_ms?: number;
  };
}

interface AGUIMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}
```

#### Example Request

```json
{
  "thread_id": "550e8400-e29b-41d4-a716-446655440038",
  "messages": [
    { "role": "user", "content": "Hello agent, provide a sunset quote" }
  ]
}
```

#### Response

SSE stream with `Content-Type: text/event-stream`

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

---

### 4.2 Endpoint: `GET /health`

Health check endpoint for monitoring.

```json
{
  "status": "ok",
  "bindu_url": "http://localhost:3773",
  "timestamp": "2024-12-23T15:30:00Z"
}
```

---

### 4.3 Endpoint: `GET /agui/runs` (Optional v1.1)

List recent runs for a thread (using Bindu `tasks/list`).

```typescript
interface ListRunsRequest {
  thread_id?: string;  // Filter by contextId
  limit?: number;      // Max results (default: 10)
}

interface ListRunsResponse {
  runs: Array<{
    run_id: string;
    thread_id: string;
    state: BinduTaskState;
    created_at: string;
    completed_at?: string;
  }>;
}
```

---

## 5. Internal Components

### 5.1 BinduClient

HTTP client for communicating with Bindu JSON-RPC API.

```typescript
class BinduClient {
  constructor(private config: BridgeConfig) {}

  /**
   * Call a Bindu JSON-RPC method
   */
  async call<T>(method: string, params: Record<string, unknown>): Promise<T> {
    const requestId = crypto.randomUUID();
    
    const response = await fetch(this.config.binduUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method,
        params,
        id: requestId,
      }),
    });
    
    const data = await response.json();
    
    if (data.error) {
      throw new BinduRPCError(data.error.code, data.error.message);
    }
    
    return data.result as T;
  }

  /**
   * Send a message to create a new task
   */
  async sendMessage(params: SendMessageParams): Promise<BinduTask> {
    return this.call('message/send', params);
  }

  /**
   * Get task status
   */
  async getTask(taskId: string): Promise<BinduTask> {
    return this.call('tasks/get', { taskId });
  }

  /**
   * List tasks (optional)
   */
  async listTasks(limit?: number): Promise<BinduTask[]> {
    return this.call('tasks/list', { limit });
  }
}
```

### 5.2 SendMessageParams

```typescript
interface SendMessageParams {
  message: {
    role: 'user';
    parts: Array<{ kind: 'text'; text: string }>;
    kind: 'message';
    messageId: string;
    contextId: string;
    taskId: string;
  };
  configuration?: {
    acceptedOutputModes: string[];
  };
}
```

### 5.3 BinduTask Response

```typescript
interface BinduTask {
  id: string;              // taskId
  context_id: string;      // contextId
  kind: 'task';
  status: {
    state: BinduTaskState;
    timestamp: string;     // ISO 8601
  };
  artifacts?: Array<{
    kind: 'text' | 'file' | 'data';
    text?: string;
    file?: unknown;
    data?: unknown;
  }>;
  history?: Array<{
    message_id: string;
    role: 'user' | 'agent';
    parts: Array<{ kind: string; text?: string }>;
  }>;
  metadata?: Record<string, unknown>;
}
```

---

### 5.4 EventEmitter

Utility for building and emitting AG-UI events.

```typescript
interface BaseEvent {
  type: EventType;
  timestamp: number;
  thread_id: string;
  run_id: string;
}

enum EventType {
  RUN_STARTED = 'RUN_STARTED',
  RUN_FINISHED = 'RUN_FINISHED',
  RUN_ERROR = 'RUN_ERROR',
  STATE_DELTA = 'STATE_DELTA',
  TEXT_MESSAGE_START = 'TEXT_MESSAGE_START',
  TEXT_MESSAGE_CONTENT = 'TEXT_MESSAGE_CONTENT',
  TEXT_MESSAGE_END = 'TEXT_MESSAGE_END',
  // Future: TOOL_CALL_* events
}

class AGUIEventBuilder {
  constructor(
    private threadId: string,
    private runId: string,
  ) {}

  private base(type: EventType): BaseEvent {
    return {
      type,
      timestamp: Date.now(),
      thread_id: this.threadId,
      run_id: this.runId,
    };
  }

  runStarted(): RunStartedEvent {
    return this.base(EventType.RUN_STARTED);
  }

  runFinished(): RunFinishedEvent {
    return this.base(EventType.RUN_FINISHED);
  }

  runError(error: string, code?: number): RunErrorEvent {
    return {
      ...this.base(EventType.RUN_ERROR),
      error: { message: error, code },
    };
  }

  stateDelta(binduState: BinduTaskState): StateDeltaEvent {
    return {
      ...this.base(EventType.STATE_DELTA),
      delta: { bindu_state: binduState },
    };
  }

  textMessageStart(messageId: string, role: string = 'assistant'): TextMessageStartEvent {
    return {
      ...this.base(EventType.TEXT_MESSAGE_START),
      message_id: messageId,
      role,
    };
  }

  textMessageContent(messageId: string, content: string): TextMessageContentEvent {
    return {
      ...this.base(EventType.TEXT_MESSAGE_CONTENT),
      message_id: messageId,
      content,
    };
  }

  textMessageEnd(messageId: string): TextMessageEndEvent {
    return {
      ...this.base(EventType.TEXT_MESSAGE_END),
      message_id: messageId,
    };
  }
}
```

---

### 5.5 SSE Response Builder

```typescript
function formatSSEEvent(event: BaseEvent): string {
  const eventType = event.type;
  const data = JSON.stringify(event);
  return `event: ${eventType}\ndata: ${data}\n\n`;
}

function createSSEStream(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  encoder: TextEncoder,
): {
  emit: (event: BaseEvent) => Promise<void>;
  close: () => Promise<void>;
} {
  return {
    async emit(event: BaseEvent) {
      const formatted = formatSSEEvent(event);
      await writer.write(encoder.encode(formatted));
    },
    async close() {
      await writer.close();
    },
  };
}
```

---

## 6. Run Handler Flow

### 6.1 Sequence Diagram

```
Inspector UI          AG-UI Bridge              Bindu Agent
     │                      │                        │
     │  POST /agui/run      │                        │
     │─────────────────────>│                        │
     │                      │  POST / (message/send) │
     │                      │───────────────────────>│
     │                      │<───────────────────────│
     │                      │    { task: submitted } │
     │<─────────────────────│                        │
     │  RUN_STARTED         │                        │
     │                      │                        │
     │                      │  POST / (tasks/get)    │
     │                      │───────────────────────>│
     │                      │<───────────────────────│
     │                      │   { state: working }   │
     │<─────────────────────│                        │
     │  STATE_DELTA         │                        │
     │                      │                        │
     │        ...poll...    │        ...agent...     │
     │                      │                        │
     │                      │  POST / (tasks/get)    │
     │                      │───────────────────────>│
     │                      │<───────────────────────│
     │                      │  { state: completed,   │
     │                      │    artifacts: [...] }  │
     │<─────────────────────│                        │
     │  TEXT_MESSAGE_*      │                        │
     │  RUN_FINISHED        │                        │
     │                      │                        │
```

### 6.2 Pseudocode

```typescript
async function handleAGUIRun(c: Context) {
  const body = await c.req.json<AGUIRunRequest>();
  
  // 1. Generate IDs
  const threadId = body.thread_id;
  const taskId = body.run_id || crypto.randomUUID();
  const messageId = crypto.randomUUID();
  
  // 2. Create SSE stream
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const encoder = new TextEncoder();
  const sse = createSSEStream(writer, encoder);
  const events = new AGUIEventBuilder(threadId, taskId);
  
  // 3. Start background processing
  (async () => {
    try {
      // 3a. Call Bindu message/send
      const task = await binduClient.sendMessage({
        message: {
          role: 'user',
          parts: body.messages.map(m => ({ kind: 'text', text: m.content })),
          kind: 'message',
          messageId,
          contextId: threadId,
          taskId,
        },
        configuration: { acceptedOutputModes: ['application/json'] },
      });
      
      // 3b. Emit RUN_STARTED
      await sse.emit(events.runStarted());
      
      // 3c. Poll for task completion
      let lastState: BinduTaskState = 'submitted';
      let pollCount = 0;
      
      while (pollCount < config.maxPollAttempts) {
        await sleep(config.pollIntervalMs);
        
        const currentTask = await binduClient.getTask(taskId);
        const currentState = currentTask.status.state;
        
        // Emit state change
        if (currentState !== lastState) {
          await sse.emit(events.stateDelta(currentState));
          lastState = currentState;
        }
        
        // Check for terminal state
        if (TERMINAL_STATES.includes(currentState)) {
          if (currentState === 'completed') {
            // Emit message events for artifacts
            await emitArtifactsAsMessages(sse, events, currentTask);
            await sse.emit(events.runFinished());
          } else if (currentState === 'failed') {
            await sse.emit(events.runError('Task failed'));
          } else if (currentState === 'canceled') {
            await sse.emit(events.runError('Task canceled', -32000));
          }
          break;
        }
        
        pollCount++;
      }
      
      // Timeout error
      if (pollCount >= config.maxPollAttempts) {
        await sse.emit(events.runError('Polling timeout'));
      }
      
    } catch (error) {
      await sse.emit(events.runError(error.message));
    } finally {
      await sse.close();
    }
  })();
  
  // 4. Return SSE response immediately
  return new Response(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

async function emitArtifactsAsMessages(
  sse: SSEStream,
  events: AGUIEventBuilder,
  task: BinduTask,
) {
  if (!task.artifacts?.length) return;
  
  for (const artifact of task.artifacts) {
    if (artifact.kind === 'text' && artifact.text) {
      const msgId = crypto.randomUUID();
      await sse.emit(events.textMessageStart(msgId, 'assistant'));
      await sse.emit(events.textMessageContent(msgId, artifact.text));
      await sse.emit(events.textMessageEnd(msgId));
    }
  }
}
```

---

## 7. File Structure

```
bindu-inspector-bridge/
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
├── SPECIFICATION.md          # This file
└── README.md                 # Usage documentation
```

---

## 8. Error Handling

### 8.1 Error Types

```typescript
class BinduRPCError extends Error {
  constructor(
    public code: number,
    message: string,
  ) {
    super(message);
    this.name = 'BinduRPCError';
  }
}

class AGUIBridgeError extends Error {
  constructor(
    message: string,
    public aguiCode?: string,
  ) {
    super(message);
    this.name = 'AGUIBridgeError';
  }
}
```

### 8.2 Error Mapping

| Bindu Error | AG-UI Event | Notes |
|-------------|-------------|-------|
| Task not found (-32001) | `RUN_ERROR` | Invalid run_id |
| Connection refused | `RUN_ERROR` | Bindu unreachable |
| Timeout | `RUN_ERROR` | Poll timeout exceeded |
| Invalid params (-32602) | `RUN_ERROR` | Bad request format |

---

## 9. CORS Configuration

```typescript
import { cors } from 'hono/cors';

app.use('/*', cors({
  origin: '*',  // Or specific inspector UI origin
  allowMethods: ['GET', 'POST', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
  exposeHeaders: ['X-Request-Id'],
}));
```

---

## 10. Future Enhancements (v1.1+)

| Feature | Description | Priority |
|---------|-------------|----------|
| **TOOL_CALL events** | Map Bindu skill/tool logs to AG-UI events | High |
| **Streaming messages** | Use Bindu `message/stream` for real-time chunks | High |
| **Run history** | Persist and replay past runs | Medium |
| **WebSocket support** | Alternative to SSE for bidirectional communication | Medium |
| **Authentication passthrough** | Forward JWT tokens to Bindu | Medium |
| **Human-in-the-loop** | Handle `input-required` state with UI prompts | Low |

---

## 11. Implementation Checklist

- [x] Initialize Hono app with CORS middleware
- [x] Implement `config.ts` with env parsing
- [x] Implement `BinduClient` with `sendMessage` and `getTask`
- [x] Implement AG-UI event types and builder
- [x] Implement SSE response streaming
- [x] Implement `/agui/run` handler
- [x] Implement `/health` endpoint
- [x] Add error handling and logging
- [ ] Write unit tests for event builder
- [ ] Write integration tests with mock Bindu
- [x] Add `bun run dev` and `bun run start` scripts


---

## 12. References

- [AG-UI Protocol Documentation](https://github.com/ag-ui-protocol/ag-ui)
- [Bindu A2A Protocol (openapi.yaml)](../openapi.yaml)
- [Hono Framework](https://hono.dev/)
- [Bun Runtime](https://bun.sh/)
