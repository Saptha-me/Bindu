# Bindu.Sdk — C# SDK for Bindu

![.NET](https://img.shields.io/badge/.NET-10.0-512BD4?logo=dotnet&logoColor=white)
![gRPC](https://img.shields.io/badge/gRPC-2.80-244c5a?logo=grpc)
![License](https://img.shields.io/badge/license-Apache%202.0-blue)

Turn any .NET agent into a full A2A-compliant microservice with one function call.

Write your agent in plain C# — call your own LLM, use Semantic Kernel, Microsoft.Extensions.AI, or nothing at all — then call `Bindufy()`. Bindu handles DID identity, authentication, x402 payments, task scheduling, storage, and the A2A protocol. You just write the handler.

The C# SDK speaks the same gRPC protocol as the [TypeScript](https://github.com/getbindu/Bindu/tree/main/sdks/typescript) and [Kotlin](https://github.com/getbindu/Bindu/tree/main/sdks/kotlin) SDKs against the same Bindu core, so agent identity and protocol are identical across languages.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [What `Bindufy()` Does](#what-bindufy-does)
- [API Reference](#api-reference)
  - [`BinduAgent`](#binduagent)
  - [`Bindufy(config, handler)`](#bindufyconfig-handler)
  - [`AgentConfig`](#agentconfig)
  - [The handler](#the-handler)
  - [`BinduResponse`](#binduresponse)
  - [`ChatMessage`](#chatmessage)
  - [`RegistrationResult`](#registrationresult)
  - [Shutting down](#shutting-down)
- [Examples](#examples)
  - [Echo agent](#echo-agent)
  - [Multi-turn conversation](#multi-turn-conversation)
  - [LLM-backed agent](#llm-backed-agent)
  - [Graceful shutdown](#graceful-shutdown)
- [How It Works Internally](#how-it-works-internally)
- [Ports](#ports)
- [Project Layout](#project-layout)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Prerequisites

- **.NET 10 SDK** — the SDK targets `net10.0`.
- **The Bindu Python core** — install it on the same machine:

  ```bash
  pip install bindu
  # or with uv:
  uv pip install bindu
  ```

  You don't start the core yourself — the SDK locates it and launches it as a child process (see [How It Works Internally](#how-it-works-internally)).

## Installation

The SDK is not on NuGet yet. Reference the project directly (path relative to a consumer project at the repo root):

```xml
<ItemGroup>
  <ProjectReference Include="sdks\csharp\Bindu-csharp-sdk.csproj" />
</ItemGroup>
```

or, from the CLI:

```bash
dotnet add reference sdks/csharp/Bindu-csharp-sdk.csproj
```

The gRPC dependencies (`Grpc.AspNetCore`, `Grpc.Net.Client`, `Google.Protobuf`) flow to your project transitively — no extra package references needed. Once the package is published to NuGet, `dotnet add package Bindu.Sdk` will work as well.

## Quick Start

Create a console app (`dotnet new console`) and replace `Program.cs`:

```csharp
using Bindu.Grpc;
using Bindu.Sdk;

var bindu = new BinduAgent();

var config = new AgentConfig {
    Author = "dev@example.com",
    Name = "echo-agent",
    Description = "Repeats the last message back",
    DeploymentUrl = "http://localhost:3773",
    ExposeDeployment = false,
    Version = "0.1.0"
};

var result = await bindu.Bindufy(config, HandleMessages);

Console.WriteLine($"AgentId:  {result.AgentId}");
Console.WriteLine($"AgentUrl: {result.AgentUrl}");
Console.WriteLine($"DID:      {result.Did}");

// Keep the process alive — the agent is now serving requests.
Console.WriteLine("Press any key to stop...");
Console.ReadKey();

static Task<object> HandleMessages(IReadOnlyList<ChatMessage> messages) {
    var last = messages[^1].Content;
    return Task.FromResult<object>($"Echo: {last}");
}
```

Run it:

```bash
dotnet run
```

That's it. Your agent is now a microservice at `http://localhost:3773` with DID, auth, and A2A protocol support.

> The SDK ships with a full xUnit test suite. Open `sdks/csharp/Bindu-csharp-sdk.slnx`, build, and run the tests from Visual Studio or the CLI (see [Testing](#testing)).

## What `Bindufy()` Does

When you call `Bindufy(config, handler)`, the SDK:

1. **Locates the Bindu core** — tries `bindu` on `PATH`, then `uv run bindu`, then `python3 -m bindu.cli`
2. **Launches the core** as a child process with gRPC enabled on `:3774`
3. **Waits for the core's gRPC port** to accept connections (30s timeout)
4. **Starts a gRPC callback server** for your handler (on `GrpcCallbackPort`, or a free port)
5. **Registers your agent** with the core via the `RegisterAgent` gRPC call
6. **Core runs full bindufy logic**: config validation, agent ID generation, DID key setup, auth, x402 payments, manifest creation, and the A2A HTTP server on the deployment URL (`:3773`)
7. **Returns** `RegistrationResult` with your agent ID, DID, and A2A URL
8. **Starts a heartbeat loop** (every 30 seconds) so the core knows the agent is alive

When a message arrives via A2A HTTP, the core's worker calls your handler over gRPC. Your handler runs, returns a response, and the core sends it back to the client. You never touch gRPC, HTTP, or A2A — it's all handled internally.

```
Client ──HTTP──► Bindu Core ──gRPC──► Your Handler ──► LLM API
                 (:3773)              (:dynamic)
                 DID, Auth, x402
                 Scheduler, Storage
```

## API Reference

### `BinduAgent`

The entry point of the SDK.

```csharp
var bindu = new BinduAgent();
```

Implements `IDisposable` and `IAsyncDisposable` — dispose it to unregister the agent and shut everything down cleanly. The SDK also hooks `Ctrl+C` and process exit automatically, so disposing is optional in most console apps.

### `Bindufy(config, handler)`

```csharp
public Task<RegistrationResult> Bindufy(
    AgentConfig config,
    Func<IReadOnlyList<ChatMessage>, Task<object>> handler)
```

Transforms your agent into a Bindu microservice. Blocks until registration is complete.

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `AgentConfig` | Agent configuration (see below) |
| `handler` | `Func<IReadOnlyList<ChatMessage>, Task<object>>` | Your handler: receives the conversation history, returns a `string` or `BinduResponse` |

**Returns:** `RegistrationResult` with `AgentId`, `Did`, and `AgentUrl`.

**Throws:**

- `InvalidOperationException` — when the Bindu core cannot be found or started, or the core rejects the registration
- `TimeoutException` — when the core does not start within the allotted time

### `AgentConfig`

```csharp
var config = new AgentConfig {
    Author = "dev@example.com",        // required
    Name = "my-agent",                 // required
    Description = "What it does",      // required
    DeploymentUrl = "http://localhost:3773",
    ExposeDeployment = false,
    GrpcCallbackPort = 0,              // 0 = auto-pick a free port
    Skills = [],
    Version = "0.1.0"
};
```

| Property | Type | Notes |
|----------|------|-------|
| `Author` | `string` (required) | Email address of the agent's author |
| `Name` | `string` (required) | Agent name, returned by the capabilities endpoint |
| `Description` | `string` (required) | Human-readable description of the agent |
| `DeploymentUrl` | `string` | A2A server URL. Default: `http://localhost:3773` |
| `ExposeDeployment` | `bool` | Expose the deployment publicly. Default: `false` |
| `GrpcCallbackPort` | `int` | Port for the SDK's gRPC callback server. `0` (default) picks a free port automatically — and if a chosen port is busy, the SDK falls back to a free one |
| `Skills` | `string[]` | Reserved for future use — not yet transmitted during registration |
| `Version` | `string?` | Agent version. Default: `0.1.0` |

### The handler

```csharp
Func<IReadOnlyList<ChatMessage>, Task<object>> handler
```

Your handler receives the full conversation history (oldest → newest) and returns either:

- **A `string`** — normal response; the task completes
- **A `BinduResponse`** — for state transitions (multi-turn conversations)

The framework inside your handler doesn't matter — Bindu only cares about the messages it passes in and what you return.

### `BinduResponse`

```csharp
var response = new BinduResponse {
    Content = "The capital of France is Paris.",
    State = "",                        // "", "input-required", or "auth-required"
    Prompt = "",                       // follow-up prompt when State is set
    Metadata = new Dictionary<string, string>()
};
```

| Property | Type | Description |
|----------|------|-------------|
| `Content` | `string` | The response text returned to the caller |
| `State` | `string` | `""` for a completed task, `"input-required"` to ask a follow-up question, or `"auth-required"` to request authentication |
| `Prompt` | `string` | Follow-up prompt shown to the user when `State` is set |
| `Metadata` | `Dictionary<string, string>` | Optional key-value metadata included in the response |

### `ChatMessage`

A single conversation turn (`Bindu.Grpc` namespace, generated from the proto contract):

```csharp
messages[^1].Role      // "user", "assistant", or "system"
messages[^1].Content   // message text
```

### `RegistrationResult`

Returned by `Bindufy()`:

| Property | Type | Description |
|----------|------|-------------|
| `AgentId` | `string` | UUID assigned to the agent by the Bindu core |
| `Did` | `string` | W3C Decentralized Identifier (e.g. `did:bindu:...`) |
| `AgentUrl` | `string` | A2A HTTP endpoint (e.g. `http://localhost:3773`) |

### Shutting down

The SDK cleans up on `Ctrl+C` or process exit automatically: it unregisters the agent, stops the callback server and heartbeat, and kills the core process. You can also trigger this explicitly:

```csharp
using var bindu = new BinduAgent();
var result = await bindu.Bindufy(config, HandleMessages);
// ...disposed at the end of the block
```

## Examples

### Echo agent

```csharp
static Task<object> HandleMessages(IReadOnlyList<ChatMessage> messages) {
    var last = messages[^1].Content;
    return Task.FromResult<object>($"Echo: {last}");
}
```

### Multi-turn conversation

```csharp
static Task<object> SurveyHandler(IReadOnlyList<ChatMessage> messages) {
    var last = messages[^1].Content;

    // First message — ask for more info and keep the task open
    if (messages.Count == 1) {
        return Task.FromResult<object>(new BinduResponse {
            Content = "Got it.",
            State = "input-required",
            Prompt = "Which topic would you like to explore?"
        });
    }

    // Follow-up — normal completion
    return Task.FromResult<object>(new BinduResponse {
        Content = $"Great question about \"{last}\". Here's what I found...",
        State = ""
    });
}
```

### LLM-backed agent

Any OpenAI-compatible chat-completions endpoint works — no SDK dependency required:

```csharp
using System.Net.Http.Json;
using System.Text.Json;

static async Task<object> LlmHandler(IReadOnlyList<ChatMessage> messages) {
    using var http = new HttpClient();
    http.DefaultRequestHeaders.Authorization =
        new("Bearer", Environment.GetEnvironmentVariable("OPENAI_API_KEY"));

    var payload = new {
        model = "gpt-4o",
        messages = messages.Select(m => new { role = m.Role, content = m.Content })
    };

    var response = await http.PostAsJsonAsync(
        "https://api.openai.com/v1/chat/completions", payload);
    response.EnsureSuccessStatusCode();

    using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
    return doc.RootElement
              .GetProperty("choices")[0]
              .GetProperty("message")
              .GetProperty("content")
              .GetString() ?? "";
}
```

### Graceful shutdown

```csharp
using var bindu = new BinduAgent();
var result = await bindu.Bindufy(config, HandleMessages);

Console.WriteLine($"Agent online at {result.AgentUrl}");

// When the using block exits, the agent is unregistered and the
// core process is shut down.
```

## How It Works Internally

```
Bindufy(config, handler)
  |
  |  1. Find the core: bindu → uv run bindu → python3 -m bindu.cli
  |  2. Spawn: bindu serve --grpc --grpc-port 3774
  |  3. Wait for :3774 to accept TCP connections (30s timeout)
  |
  |  4. Start the AgentHandler gRPC server on the callback port
  |     (GrpcCallbackPort, or a free port when 0 / when busy)
  |
  |  5. Call BinduService.RegisterAgent on :3774
  |     (sends config JSON + callback address)
  |
  |  Core runs full bindufy logic:
  |     - Config validation
  |     - Agent ID generation
  |     - DID setup (Ed25519 key generation)
  |     - Auth + x402 payment setup (when configured)
  |     - Manifest creation (manifest.run = GrpcAgentClient)
  |     - A2A HTTP server on the deployment URL (:3773)
  |
  |  6. Return {AgentId, Did, AgentUrl}
  |  7. Start heartbeat loop (every 30s)
  |  8. Wait for HandleMessages calls
```

## Ports

| Port | Protocol | Who | Purpose |
|------|----------|-----|---------|
| 3773 | HTTP | Bindu Core | A2A protocol server (clients connect here) |
| 3774 | gRPC | Bindu Core | Registration server (SDK connects here) |
| dynamic | gRPC | SDK | Handler server (core calls the SDK here) |

## Project Layout

```
sdks/csharp/
├── Bindu-csharp-sdk.slnx        # Solution — SDK + test project
├── Bindu-csharp-sdk.csproj      # net10.0, gRPC packages, XML docs
├── .gitignore                   # Local C#/VS/test ignores for the SDK
├── proto/
│   └── agent_handler.proto      # gRPC contract shared with other SDKs
├── src/
│   ├── BinduAgent.cs            # Public API: BinduAgent, AgentConfig, RegistrationResult
│   ├── BinduResponse.cs         # Structured handler response
│   ├── AgentHandler.cs          # gRPC service hosting your handler
│   ├── CoreLauncher.cs          # Locates and spawns the Bindu core
│   ├── GrpcClient.cs            # Talks to the core on :3774
│   ├── GrpcServer.cs            # Hosts the callback server
│   └── HeartbeatService.cs      # 30s heartbeat loop
└── tests/
    └── Bindu.Sdk.Tests/         # xUnit suite — unit + in-process integration tests
```

## Testing

The SDK ships with an xUnit test suite that runs entirely in-process — it spins up a
**fake Bindu core** on a random port, so no Python core or network access is needed.

```bash
cd sdks/csharp/tests/Bindu.Sdk.Tests
dotnet test
```

With a coverage report (excludes generated proto/gRPC code):

```bash
dotnet test --collect:"XPlat Code Coverage" --settings coverlet.runsettings
```

## Troubleshooting

### "Cannot find bindu, uv, or python3. Ensure at least one is installed."

The Bindu Python core isn't on the machine or `PATH`. Install it and try again:

```bash
pip install bindu
# or with uv:
uv pip install bindu
```

### "Bindu core did not start within 30s"

The core failed to launch. Check:

```bash
# Is Bindu installed?
pip show bindu

# Can it serve?
bindu serve --grpc --help
# or: uv run bindu serve --grpc --help
# or: python3 -m bindu.cli serve --grpc --help
```

### "Bindu agent registration failed: ..."

The core rejected the registration — the message after the colon explains why. Core logs are printed to your console with a `[bindu-core]` prefix; the SDK's own diagnostics use `[bindu-sdk]`.

### The callback port I configured is already in use

Not a problem — the SDK logs `Port X is in use, picking a free port automatically` and uses a free one. Set `GrpcCallbackPort = 0` to always auto-pick.

### Heartbeat errors

If you see `[bindu-sdk:err] Heartbeat failed: ...`, the core became unreachable (it exited or the network changed). Check that no other process is fighting over port 3774.

## License

Apache License 2.0. See the [repository LICENSE](https://github.com/getbindu/Bindu/blob/main/LICENSE.md).
