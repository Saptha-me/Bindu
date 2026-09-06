# GrpcAgentClient

## What It Is

`GrpcAgentClient` is a Python class that looks like a function. You call it with messages, it returns a string or dict. Internally, it makes a gRPC call to a remote process in another language. But the caller doesn't know that.

This is the trick that makes the entire language-agnostic system work without changing a single line in ManifestWorker.

## The Problem It Solves

ManifestWorker has this line:

```python
raw_results = self.manifest.run(message_history or [])
```

For Python agents, `manifest.run` is a wrapper around the developer's handler function. It takes a list of message dicts, returns a string or dict.

For TypeScript/Kotlin agents, we need that same call to go over the network. But we can't change ManifestWorker — it handles task state transitions, error handling, tracing, payment settlement. Touching it risks breaking everything.

Solution: make `GrpcAgentClient` a callable that quacks like a handler function.

## How It Works

```python
class GrpcAgentClient:
    def __init__(self, callback_address: str, timeout: float = 30.0):
        self._address = callback_address  # e.g., "localhost:50052"
        self._timeout = timeout

    def __call__(self, messages, **kwargs):
        # 1. Flatten A2A messages (with `parts`) to protobuf {role, content}.
        #    The proto ChatMessage has no parts field, so text parts collapse
        #    to content, file parts are text-extracted, and A2A roles map to
        #    chat roles ("agent" -> "assistant") — this is the ONE place
        #    chat-format flattening still happens.
        request = self._build_request(messages)

        # 2. Call the SDK's AgentHandler over gRPC
        response = self._stub.HandleMessages(request, timeout=self._timeout)

        # 3. Convert back to what ManifestWorker expects
        if response.state:
            return {"state": response.state, "prompt": response.prompt}
        else:
            return response.content
```

Three steps: convert, call, convert back. That's the entire bridge.

## The Response Contract

ManifestWorker doesn't care how the response was produced. It only cares about the type:

| Handler returns | ManifestWorker does | Task state |
|----------------|---------------------|------------|
| `"The capital of France is Paris."` | Creates message + artifact | `completed` |
| `{"state": "input-required", "prompt": "Can you clarify?"}` | Creates message, keeps task open | `input-required` |
| `{"state": "auth-required"}` | Creates message, keeps task open | `auth-required` |

GrpcAgentClient returns exactly these types. The downstream code — `ResultProcessor`, `ResponseDetector`, `ArtifactBuilder` — processes them identically to a local Python handler's output.

## Real Example: What Happens When a User Asks a Question

A user sends "What is quantum computing?" to a TypeScript agent:

```
ManifestWorker calls manifest.run(messages)
  → GrpcAgentClient.__call__([{"role": "user", "kind": "message",
        "parts": [{"kind": "text", "text": "What is quantum computing?"}], ...}])
    → Flattens parts to protobuf: ChatMessage(role="user", content="What is quantum computing?")
    → gRPC call: AgentHandler.HandleMessages(HandleRequest{messages: [...]})
    → TypeScript SDK receives the call
    → Developer's handler runs: await openai.chat.completions.create(...)
    → OpenAI returns: "Quantum computing is a type of computation..."
    → SDK returns: HandleResponse{content: "Quantum computing is...", state: ""}
  → GrpcAgentClient sees state is empty, returns the string
→ ManifestWorker receives "Quantum computing is..." (same as a local handler)
→ ResultProcessor normalizes → ResponseDetector says "completed"
→ ArtifactBuilder creates DID-signed artifact
→ User gets the response
```

The GrpcAgentClient is the only component that knows gRPC exists. Everything above and below it is oblivious.

## When It's Created

During `RegisterAgent`, the gRPC service creates a `GrpcAgentClient` and attaches it to the manifest:

```python
# In BinduServiceImpl.RegisterAgent():
grpc_client = GrpcAgentClient(request.grpc_callback_address)

# In create_manifest():
manifest.run = grpc_client  # GrpcAgentClient IS the handler now
```

From this point on, every task for this agent flows through the client.

## Connection Lifecycle

The client connects lazily — the gRPC channel is created on the first call, not during initialization. This avoids connection errors during registration if the SDK's server isn't fully ready yet.

When the SDK disconnects (Ctrl+C, crash), the next `HandleMessages` call fails with `grpc.StatusCode.UNAVAILABLE`. ManifestWorker's existing error handling catches this and marks the task as failed. No special handling needed.

## Health Checks and Capabilities

```python
grpc_client.health_check()       # Is the SDK still running? Returns True/False
grpc_client.get_capabilities()   # What can the SDK do? Returns name, version, etc.
```

Used during heartbeat processing and capability discovery.

## What It Doesn't Do Yet

- **Streaming** — proto defines `HandleMessagesStream` but the client doesn't implement it. Remote agents can only return complete responses. See [limitations](./limitations.md).
- **Reconnection** — if the SDK crashes, the client doesn't retry. The agent must be re-registered.
- **TLS** — uses insecure channels. Only safe on localhost or trusted networks.
