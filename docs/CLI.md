# Command-Line Interface (CLI)

## Why this page exists

The Bindu CLI provides a command-line interface to interact with the Bindu framework. It simplifies tasks such as starting the core server, deploying agents, and managing runtime environments. This page explains the available commands, their usage, and how they work under the hood.

---

## Overview of CLI commands

The CLI exposes the following commands:

| Command                     | Description                                                                 |
|-----------------------------|-----------------------------------------------------------------------------|
| `bindu serve --grpc`        | Starts the Bindu core with gRPC for SDK registration.                       |
| `bindu serve --script PATH` | Executes a user agent script.                                               |
| `bindu deploy <script>`     | Deploys an agent script to a runtime environment.                           |
| `bindu logs <agent>`        | Streams logs from the specified agent's runtime environment.                |
| `bindu shell <agent>`       | Opens an interactive shell on the specified agent's runtime environment.    |

---

## Command details

### `bindu serve`

Starts the Bindu core or executes a user agent script.

#### Usage

```bash
bindu serve --grpc [--grpc-port <port>]
bindu serve --script <path>
```

#### Options

- `--grpc`: Starts the gRPC server for SDK registration.
- `--grpc-port`: Specifies the port for the gRPC server (default: 3774).
- `--script <path>`: Executes the specified user agent script.

#### Example

Start the gRPC server:

```bash
bindu serve --grpc --grpc-port 3774
```

Run a user agent script:

```bash
bindu serve --script examples/agent.py
```

---

### `bindu deploy`

Deploys an agent script to a runtime environment.

#### Usage

```bash
bindu deploy <script> --runtime=<runtime> [options]
```

#### Options

- `--runtime`: Specifies the runtime environment (e.g., `boxd`).
- `--name`: Overrides the agent name defined in the script.
- `--vcpu`, `--memory`, `--disk`: Configures resource limits for the runtime.
- `--env KEY=VALUE`: Sets environment variables for the agent (repeatable).
- `--bindu-version`: Specifies the Bindu version to use (e.g., `local`).
- `--image`: Deploys the agent using a prebuilt image.

#### Example

Deploy an agent script to the `boxd` runtime:

```bash
bindu deploy examples/agent.py --runtime=boxd --vcpu=4 --memory=8G --disk=40G
```

---

### `bindu logs`

Streams logs from the specified agent's runtime environment.

#### Usage

```bash
bindu logs <agent> [--follow]
```

#### Options

- `--follow`: Streams logs in real-time (default: true).

#### Example

Stream logs from the `my-agent` runtime:

```bash
bindu logs my-agent
```

---

### `bindu shell`

Opens an interactive shell on the specified agent's runtime environment.

#### Usage

```bash
bindu shell <agent>
```

#### Example

Open a shell on the `my-agent` runtime:

```bash
bindu shell my-agent
```

---

## How it works

### `bindu serve`

- **gRPC mode**: Starts the core server for SDK registration. The server listens on the specified port and handles gRPC requests.
- **Script mode**: Executes the specified user agent script in the `__main__` context.

### `bindu deploy`

- Packages the agent script and its dependencies.
- Deploys the package to the specified runtime environment.
- Configures runtime resources and environment variables.

### `bindu logs`

- Streams logs from the agent's runtime environment to the host terminal.
- Uses the `StreamLogs` API to fetch logs in real-time.

### `bindu shell`

- Opens an interactive shell (e.g., `bash`) on the agent's runtime environment.
- Uses the `exec` API to establish the shell session.

---

## Testing the CLI

The CLI is tested using unit tests that mock runtime environments and simulate command execution. Key test cases include:

- Verifying that `bindu deploy` correctly parses flags and passes them to the runtime provider.
- Ensuring that `bindu logs` streams logs to stdout.
- Checking that `bindu shell` opens an interactive shell.

---

## Related

- [AUTHENTICATION.md](./AUTHENTICATION.md): How authentication works in Bindu.
- [PRIVATE_SKILLS.md](./PRIVATE_SKILLS.md): Managing private skills in agents.
- [SKILLS.md](./SKILLS.md): The underlying skill system.

---

This document provides a comprehensive overview of the Bindu CLI. For more details, refer to the source code and tests in the `bindu/cli` and `tests/unit/runtime` directories.