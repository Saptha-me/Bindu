# Boxd runtime

`bindu deploy <script> --runtime=boxd` runs your bindu agent inside a
[boxd](https://boxd.sh) microVM. The host process becomes a deploy tool;
the agent serves traffic from its own VM with a public HTTPS URL.

## Requirements

- A boxd account and API key (`BOXD_API_KEY=bxk_...` or `BOXD_TOKEN=...`
  in the host environment).
- The runtime-boxd extra: `pip install 'bindu[runtime-boxd]'` (pulls
  [`boxd`](https://pypi.org/project/boxd/) from PyPI).

## CLI flag reference

| Flag | Type | Default | Meaning |
|---|---|---|---|
| `--runtime` | str | `boxd` | Runtime provider. |
| `--name` | str | from script `config["name"]` | Override the agent name (e.g., for preview envs). |
| `--image` | str | unset | If set, **A1 mode**: VM is created from this image; no source ship. See [custom-image.md](custom-image.md). |
| `--vcpu` | int | org default | vCPUs. boxd machines come in fixed sizes (1 vCPU/4G, 2/8G, 4/16G) — set either `--vcpu` or `--memory` and the other follows. Unset uses your org's default size. |
| `--memory` | str | org default | RAM (`4G`, `8G`, `16G`). See `--vcpu`. |
| `--disk` | str | unset | Not supported by boxd yet — every machine gets 100 GiB, and the server refuses a per-machine disk size. Kept for when it lands. |
| `--auto-suspend` | int | `0` (disabled) | Seconds of *idle* (no HTTP request) before boxd auto-suspends the VM. **Default off** because bindu agents commonly run background work (scheduler ticks, streaming LLM calls, websockets) that would be frozen mid-flight by an idle timeout. Pass an explicit value like `--auto-suspend=60` only if your agent is pure request/response. |
| `--on-exit` | str | `suspend` | Behavior on Ctrl-C: `suspend` (actively call `machines.pause()`), `destroy` (tear down VM), `detach` (leave running). `suspend` works regardless of `--auto-suspend` — it suspends the VM directly when the host detaches. |
| `--bindu-version` | str | unset | Pin the bindu version installed in the VM. Special value `local` ships the host's bindu source instead of pulling from PyPI (useful for testing patched bindu). |
| `--env` | KEY=VALUE | — | Extra env var for the agent inside the VM (repeatable). |

## Lifecycle

1. **First run:** `bindu deploy` runs your script once locally with a capture
   sentinel set, so `bindufy()` returns the agent name without serving. The
   CLI then packages your project source, ships it to a fresh VM, runs
   `pip install bindu` + your project's deps, exec's
   `bindu serve --script <your-script>`, polls `/health` until ready.
   Cold path: ~10–30 seconds depending on dep weight.
2. **Subsequent runs (same agent name):** the CLI reuses the existing VM,
   updates source, restarts the agent. ~1–3 seconds.
3. **Ctrl-C with `--on-exit=suspend` (default):** the CLI explicitly calls
   `machines.pause()`, freezing the VM's memory and pausing all in-flight
   work. The VM is preserved on disk; re-running `bindu deploy` resumes
   in 1–3s with state intact (DID keys, vector store, conversation
   history, etc. all survive).
4. **`--auto-suspend=N` (off by default):** while the agent is *running*,
   suspend the VM after N seconds without an HTTP request. Useful for
   pure request/response agents to save cost during idle periods. Avoid
   if the agent has scheduled tasks, streaming LLM calls, or websocket
   connections — those will be frozen mid-execution and resume mid-RPC,
   which most upstreams don't tolerate.

## Identity and secrets

- The agent's DID keys, x402 wallet, OAuth tokens are all generated and
  persisted **inside the VM**. `BOXD_API_KEY` stays on the host and is
  never shipped to the VM.
- User secrets (`OPENAI_API_KEY`, etc.) ship via repeated
  `--env KEY=VALUE` flags on `bindu deploy`. They reach the agent
  process's environment inside the VM and never touch the source tarball.
- **`.env`-style files are never shipped.** A deployed agent runs on a
  public-IP VM, so accidentally tarballing a `.env` with `OPENAI_API_KEY=`
  would publish it. The deploy CLI silently drops `.env*`, `*.pem`,
  `*.key`, `id_rsa*`, `credentials*.json`, `*.kdbx`, `*.p12`, `*.pfx`,
  `*.kubeconfig` and anything under `.aws/` `.ssh/` `.gnupg/` `.bindu/`,
  and prints a stderr warning listing what was dropped. Use `--dry-run`
  to see the full list before deploying.

## Pre-deploy preview

```bash
bindu deploy agent.py --runtime=boxd --dry-run
```

Prints the target VM, source root, entry script, resource config, env-var
keys (values hidden), tarball file count + compressed size, and any
sensitive files that would be silently dropped. No VM is touched.

## Source packaging

Your project root is auto-discovered by walking up from your entry script
looking for `pyproject.toml`, `setup.py`, `requirements.txt`, or `.git`.

**Always shipped:** `*.py`, `*.toml`, `*.txt`, `*.md`, `*.json`,
`*.yaml`, `.env`.
**Always excluded:** `__pycache__/`, `.git/`, `.venv/`, `venv/`,
`node_modules/`, `*.pyc`, `*.log`, `*.sqlite`, `*.db`, plus everything
in your `.gitignore` and `.binduignore`.
**Hard cap:** 50 MB compressed. Bigger sources fail fast with a pointer
to `.binduignore`.

## Dev DX

- `bindu logs <agent>` — stream the agent's stdout/stderr to your terminal.
  Implemented as a ``tail -F`` of the in-VM agent log over a streaming exec —
  boxd's ``machines.logs`` is the VM console, which the detached agent
  process never writes to.
  The upside: you only see the agent's own output, not kernel/boot noise.
  Pass ``--no-follow`` to print what's there now and exit.
- `bindu shell <agent>` — open an interactive shell on the agent's VM
  (`/app` is the working directory).

## Troubleshooting

| Problem | Likely cause | Action |
|---|---|---|
| `BOXD_API_KEY or BOXD_TOKEN must be set` | No credentials in host env | `export BOXD_API_KEY=bxk_...` |
| `script did not call bindufy()` | Entry script raised before reaching `bindufy()`, or doesn't call it at all | Run the script directly first (`python agent.py`) to see the underlying error |
| `agent at <url> did not become healthy within 60s` | VM up but agent failed to start | `bindu logs <agent>` and inspect; common causes: missing dependency, syntax error in your script, port 3773 already in use inside VM |
| `pip install` failure | Dep not on PyPI, native build fails | Switch to A1 (custom image) and install the dep at image-build time |
| Source >50 MB | Large data files included | Add to `.binduignore` |
| Old bindu in VM rejects new features | Published bindu lags the host's | Pass `--bindu-version=local` to ship the host's source instead |
| `upload to /tmp/... incomplete` | The machine confirmed fewer bytes than the host sent | Re-run `bindu deploy`; if it persists, check boxd status — the deploy refuses to proceed on a corrupt artifact |
| Looks like the wrong code is running after redeploy | Old agent process kept port 3773 | The deploy kills the previous agent via its pidfile before starting the new one. If you see this anyway, run `bindu shell <agent>` and check `cat /tmp/bindu-agent.pid` against `pgrep python3` |
