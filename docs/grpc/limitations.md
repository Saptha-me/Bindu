# Limitations

Honest accounting of what doesn't work yet and what trade-offs we made.

## Streaming Responses

**Status: Not implemented**

The proto defines `HandleMessagesStream` — a server-side streaming RPC where the SDK yields response chunks incrementally. But `GrpcAgentClient` doesn't call it. Remote agents can only return complete responses.

**What this means in practice:**

You're building a TypeScript agent with GPT-4o. In a Python agent, you could stream tokens back to the user as they're generated — they see the response forming word by word. With a gRPC agent, the user waits for the entire response, then sees it all at once.

For short answers (< 2 seconds), this doesn't matter. For long responses (analysis, code generation, research), the UX is noticeably worse.

**Workaround:** Return complete responses. Most agents do this anyway — the streaming gap only matters for chat-like interfaces where perceived latency matters.

**What needs to happen:**
1. Add `stream_messages()` method to `GrpcAgentClient`
2. Wire it into `ManifestWorker` for streaming task execution
3. Update SDK `AgentHandler` to support streaming handlers
4. Add E2E tests for streaming round-trips

## No TLS

gRPC connections use `grpc.insecure_channel`. Traffic between the core and SDK is unencrypted.

**Why it's okay for now:** The core and SDK run on the same machine (localhost). The SDK spawns the core as a child process. There's no network exposure.

**When it matters:** If you deploy the core and SDK on different machines, or in a zero-trust network environment. TLS/mTLS support is planned.

## No Automatic Reconnection

If the SDK process crashes mid-execution, the `GrpcAgentClient` doesn't retry. The task fails, and the agent must be re-registered.

**What happens:** ManifestWorker catches the gRPC `UNAVAILABLE` error and marks the task as failed. The user gets an error response. On restart, the SDK calls `RegisterAgent` again and the agent is back.

**What would be better:** Automatic reconnection with exponential backoff, so transient failures (SDK restart, brief network blip) recover without re-registration.

## No Connection Pooling

Each `GrpcAgentClient` creates a single gRPC channel. Under high concurrency (many simultaneous tasks), all calls share one channel.

For most agents this is fine — gRPC channels handle multiplexing well. But for agents processing hundreds of concurrent requests, a connection pool would reduce contention.

## No gRPC-Specific Metrics

The `/metrics` endpoint (Prometheus) reports HTTP request metrics but not gRPC call metrics. You can't see HandleMessages latency, error rates, or call counts in the dashboard.

**Workaround:** Check the core's log output, which includes timing information for each handler call.

## No Load Balancing

If you run two instances of the same TypeScript agent, each one registers separately with a different callback address. There's no built-in routing to spread load across instances.

**Workaround:** Use a reverse proxy (like Envoy) in front of the SDK instances, and register the proxy address as the callback.

## Feature Comparison

| Feature | Python Agents | gRPC Agents |
|---------|--------------|-------------|
| Unary responses | works | works |
| Streaming responses | works | **not implemented** |
| DID identity | works | works |
| x402 payments | works | works |
| Skills | works | works |
| State transitions (input-required) | works | works |
| Health checks | works | works |
| Multi-language | Python only | any language |
| File/binary parts | works (raw A2A parts) | **flattened to text** |
| Latency overhead | 0ms | 1-5ms |
| TLS | N/A (in-process) | **not implemented** |
| Auto-reconnection | N/A (in-process) | **not implemented** |

The bottom line: gRPC agents have **near-full feature parity** with Python agents for the core functionality (DID, auth, payments, skills). The message contract differs in one important way: Python handlers receive raw A2A messages with `parts` intact (including file bytes), while the gRPC proto `ChatMessage` only carries `{role, content}` strings — so file parts are text-extracted (PDF/txt/docx) or replaced with an `[Unsupported file type: ...]` placeholder at the wire boundary, and messages with no extractable text (e.g. data-part-only) are dropped from the gRPC request. Vision/file agents that need raw bytes must be Python handlers until the proto grows a parts field. The remaining gaps are streaming, security, and resilience — all planned for future releases.
