# Bindu Inbox

A Gmail-shaped operator console for the A2A network. Every JSON-RPC message between two DIDs lands here as a row, threads group by `context_id`, and signatures are verified inline so you can see whether a peer is actually who it claims to be.

<p align="center">
  <img src="../assets/inbox.png" alt="Bindu inbox — three-pane layout with folders, threads, and a signed message in the right rail" width="900" />
</p>

This README walks you from `git clone` to a signed message landing in the right rail, with auth on the whole way through. **No prior bindu knowledge required** — just follow it top to bottom.

## TL;DR

If you've done this before, here's the whole flow:

```bash
git clone https://github.com/getbindu/Bindu.git && cd Bindu
uv sync
export OPENROUTER_API_KEY=<get one at https://openrouter.ai/keys>
cd inbox && npm install && npm run dev    # → http://127.0.0.1:3775
# In another shell, once the UI is up:
./scripts/spawn-demo-peers.sh             # boots joke + poet agents
# In the UI:  gear icon (top-left)  → paste OPENROUTER_API_KEY into Settings
#            "+ Create your agent" (bottom-left) → fill persona → Save
#            Start (same card)     → spawns your personal agent + Hydra OAuth
#            Contacts → +          → paste http://127.0.0.1:5773 then 5776
#            Compose               → pick joke_agent → type a message → ⌘↵
```

## Trust verification (vertical slice)

The Inbox records a peer as **unknown** when it is discovered. The server-side
canonical DID-signature verifier supplies the verified result; webhook JSON is
never trusted as a verification claim. The Inbox persists the verification
outcome, rejects duplicate accepted message IDs, and rejects timestamps outside
its clock-skew window. Configure the
retention controls on the Inbox API process:

```bash
BINDU_SIGNATURE_MAX_CLOCK_SKEW_SECONDS=300
BINDU_REPLAY_RETENTION_SECONDS=86400
```

Select a message and open **Verify** to inspect the accessible trust badge and
verification history. Signature verification remains a server/agent operation:
the browser never supplies a trust decision.

If you've never done this before, keep reading — every step below explains what it does and what you should see.

## What ends up running

By the time you finish this guide, five things will be alive on your machine:

| Port | Process | What it does |
| --- | --- | --- |
| `3775` | Vite dev server | The React UI you open in your browser |
| `3787` | Hono API (`server/index.ts`) | SQLite event store, webhook intake, outbound A2A composer |
| `<auto>` (e.g. `5xxxx`) | Your personal agent (Python, spawned on demand) | Your DID + Hydra OAuth client. Listens for inbound A2A and signs everything you send. |
| `5773` + `5776` | Demo peers (joke + poet) | Two example agents to talk to. Optional — bring your own if you have them. |
| `3774` | Gateway (optional) | The planner. Only spawns when you message ≥2 agents at once. |

`3775` is hard-pinned (Vite refuses to drift) and `3787` is hard-coded; both have to be free before you start. If something else is on those ports, the inbox won't boot — see [Troubleshooting](#troubleshooting).

## Prerequisites

You need four things on your machine before this works:

1. **Node 20+** and **npm**. Check with `node --version`. If you need it: <https://nodejs.org/>.
2. **Python 3.12+** and [**uv**](https://github.com/astral-sh/uv). Check with `python3 --version` and `uv --version`. To install uv:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **A bindu checkout with dependencies synced.** From scratch:
   ```bash
   git clone https://github.com/getbindu/Bindu.git
   cd Bindu
   uv sync           # installs python deps under .venv/
   ```
   The inbox lives at `Bindu/inbox` and locates the repo via `..` from its own folder, so running it from inside the checkout Just Works. If you moved the inbox out, set `BINDU_REPO_DIR=/path/to/Bindu`.
4. **An OpenRouter API key.** The personal agent and the demo peers all use OpenRouter for LLM calls.
   - Get one (free trial credits, no card required for testing) at <https://openrouter.ai/keys>.
   - Then either export it in your shell:
     ```bash
     export OPENROUTER_API_KEY=sk-or-v1-...
     ```
   - …or paste it into the inbox's Settings tab after boot (gear icon, top-left). Settings-tab values win over env vars.

That's it. No Docker, no Postgres, no Hydra of your own — the inbox uses the public Bindu Hydra at `hydra.getbindu.com` for OAuth.

## Start it

From the repo root:

```bash
cd inbox
npm install        # ~30s first time, cached after
npm run dev
```

You should see two concurrent processes logging side by side:

```
[web] VITE v6.x  ready in 400 ms
[web] ➜  Local:   http://127.0.0.1:3775/
[api] [inbox] api on http://127.0.0.1:3787
```

If you see `[inbox] GATEWAY_API_KEY not set` it's a warning, not an error — you only need the gateway key for multi-agent compose, which isn't part of this guide.

Open <http://127.0.0.1:3775>. You'll see:
- **Left sidebar**: folders (Inbox, Sent), an empty Contacts section, a **gear icon** at the top (Settings — API keys), and at the bottom a dashed-border **➕ Create your agent** button.
- **Middle pane**: empty thread list.
- **Right pane**: nothing selected.

That's the cold-start state. The next four steps fill it in.

> 💡 **Recommended first**: click the **gear icon** at the top of the sidebar and paste your OpenRouter API key into Settings. The personal agent reads it from the database on every spawn, so doing it before Step 2 saves you a retry.

### 1 · Create your persona (opens the wizard)

At the bottom of the sidebar, click **➕ Create your agent**. This opens the persona wizard.

Fill in at least:
- **Name** — anything. "Sheldon Cooper" works fine.
- **Occupation** — a short title + organization.
- **Personality traits** — a few comma-separated traits.

Click **Save**. This writes `~/.bindu/personal/persona.json` and the bottom-of-sidebar card changes: it now shows your persona name, a gray dot, status **down**, and a **Start** button. **Nothing is signed yet** — you're just a row in the inbox DB.

### 2 · Spawn your personal agent (this is what turns auth on)

Click **Start** on the personal-agent card (where the wizard button used to be).

Here's what happens behind the scenes, in order — this takes ~10s the first time, ~3s on subsequent spawns:

1. **Port picked.** A free local port (typically in the 50000–65000 range) is assigned.
2. **Files written to `~/.bindu/personal/`.**
   - `agent.py` — rendered from the template in `server/personal-agent.ts`. Hand-edits get overwritten.
   - `.env` — mode `0600` (POSIX), contains `AUTH__ENABLED=true`, `AUTH__PROVIDER=hydra`, `HYDRA__ADMIN_URL`, `HYDRA__PUBLIC_URL`, `OPENROUTER_API_KEY`.
3. **`uv run python agent.py` is spawned** from the bindu repo root. Bindufy then:
   - **Registers an OAuth client with Hydra** (`https://hydra-admin.getbindu.com` by default). `client_id` = your DID. Public key goes into the client metadata. Idempotent — re-runs reuse the same client.
   - **Generates an Ed25519 keypair** under `~/.bindu/personal/.bindu/private.pem` + `public.pem`. First spawn only.
   - **Starts the A2A server** on the assigned port and the gRPC core on its own.

When the spawn returns, the slot flips to **alive** (green dot) and shows your DID:

```
did:bindu:<your-author>:<persona-slug>:<uuid>
```

That's your cryptographic identity from now on. Every outbound message the inbox sends is **bearer-token-authed against Hydra** *and* **Ed25519-signed with this key** — same envelope a fully-deployed bindufy agent uses.

**If it didn't go alive:** see Troubleshooting → `Personal agent stays "down"`.

### 3 · Add a peer (spawn two demo agents)

You need at least one other agent to talk to. The inbox ships a script that spawns two single-purpose demo agents with auth on:

```bash
# from the inbox/ directory
./scripts/spawn-demo-peers.sh
```

This boots:
- **`joke_agent`** on `http://127.0.0.1:5773` — tells jokes, declines anything else.
- **`poet_agent`** on `http://127.0.0.1:5776` — writes 4-line poems, declines anything else.

Both run with `AUTH__ENABLED=true`, so they reject unauthenticated callers — same as your personal agent. Source: [`examples/gateway_test_fleet/joke_agent.py`](../examples/gateway_test_fleet/joke_agent.py) and [`poet_agent.py`](../examples/gateway_test_fleet/poet_agent.py).

Output looks like:

```
Spawning demo peers for the inbox...
  [joke_agent] starting on port 5773...
  [joke_agent] ready, pid=12345, log=.../scripts/logs/joke_agent.log
  [poet_agent] starting on port 5776...
  [poet_agent] ready, pid=12346, log=.../scripts/logs/poet_agent.log

Paste these into the inbox: Contacts → + → Add a peer
  joke_agent   http://127.0.0.1:5773
  poet_agent   http://127.0.0.1:5776
```

Now in the UI:
1. Sidebar → **Contacts** section → click the **+** button.
2. Paste `http://127.0.0.1:5773`. The inbox calls `/.well-known/agent.json`, records the DID, and tags the contact `protected` (because Hydra auth is on).
3. Repeat with `http://127.0.0.1:5776`.

Both should now appear under **Agents** in the sidebar.

Stop the demo peers later with `./scripts/stop-demo-peers.sh`. Their logs live under `inbox/scripts/logs/` — both are gitignored.

> ℹ️ **Bringing your own agent works the same way.** Any bindufy URL — local or remote, with or without auth — is a valid peer. The inbox auto-detects the auth shape from the agent card.

### 4 · Send your first message

1. Click the big **Compose** button at the top of the sidebar.
2. In the modal, pick **joke_agent** from the recipient picker.
3. Type something like `tell me a joke about databases`.
4. Press `⌘↵` (or click **Send**).

The inbox does this:
1. Mints (or reuses, if cached) a Hydra client-credentials token with `agent:read agent:write`.
2. Builds the JSON-RPC `message/send` envelope with a fresh `contextId` + `taskId`.
3. **Signs the canonical body** with your personal agent's Ed25519 private key, attaches `X-DID`, `X-DID-Signature`, `X-DID-Timestamp` headers.
4. POSTs to `http://127.0.0.1:5773/` with `Authorization: Bearer <jwt>`.

Two things should happen within a few seconds:
- A new row appears in the **Sent** folder (your outbound message).
- The agent's webhook fires back to the inbox at `/webhooks/bindu/joke_agent`, and a reply appears in the **Inbox** folder. Both messages are threaded under the same `context_id`.

Click the thread to read the reply. You're done — you've just sent a signed, authed A2A message and received an answer.

## Verify it's actually using auth

Don't trust the UI — prove it from your terminal.

**Find the personal-agent port:**
```bash
curl -s http://127.0.0.1:3787/api/me | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])"
# → http://127.0.0.1:61380
```

**Confirm unauthed callers are rejected:**
```bash
curl -s -X POST http://127.0.0.1:61380/ \
  -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"x","params":{"message":{"role":"user","kind":"message","parts":[{"kind":"text","text":"hi"}],"messageId":"m","contextId":"c","taskId":"t"}}}'
# → {"jsonrpc":"2.0","error":{"code":-32009,"message":"Authentication is required ..."},"id":null}
```

**Confirm the inbox can:**
```bash
curl -s -X POST http://127.0.0.1:3787/api/compose \
  -H 'content-type: application/json' \
  -d '{"agentId":"joke_agent","text":"hi"}'
# → {"ok":true,"status":200,"contextId":"...","taskId":"...","response":{"jsonrpc":"2.0",...}}
```

**Inside the UI:** open any thread and click **Verify** in the top-right of the right rail. Each row should report `signed / verified` against the peer's published `publicKeyBase58`. The detail rail's **Verify** tab shows the DID match, the signature, and the timestamp nonce.

## What "auth on" means here

There are three independent auth layers in play. The inbox uses all three:

| Layer | Who enforces it | How to turn it on | Default |
| --- | --- | --- | --- |
| **Peer A2A auth** — outbound calls must carry a JWT + DID signature | The peer's bindufy middleware (`-32009` if missing) | Set `AUTH__ENABLED=true` on the peer. Done automatically when the inbox spawns your personal agent or the demo peers. | **On** |
| **Operator gate** — `/api/*` on the inbox requires a bearer token | `inbox/server/index.ts` | `export BINDU_COMMS_TOKEN=$(openssl rand -hex 32)` before `npm run dev`. UI needs `?token=<token>` in the URL (SSE can't send headers). | Off (single-user dev) |
| **Webhook gate** — agents POSTing to `/webhooks/bindu/:agentId` must carry a bearer token | `inbox/server/index.ts` | `export BINDU_WEBHOOK_TOKEN=<token>` and configure the same value as `global_webhook_token` on the bindufy side. | Off |

The first is non-negotiable once your personal agent is alive. The other two are belt-and-suspenders for multi-user or exposed deployments — leave them off until you actually share the URL.

## Using the inbox

### Layout

| Pane | What it shows |
| --- | --- |
| **Left** | Folders (Inbox / Sent / Drafts / Archive), Contacts grouped into **Gateways** (orchestrators for multi-agent plans) and **Agents** (single-purpose peers). Your operator identity sits at the bottom. |
| **Middle** | Thread list — newest first, one row per `context_id`. The badge is the message count. |
| **Right** | Selected thread, oldest message at top. State pills + DID per row; bodies render inline. Reply composer pinned at the bottom. |

### Sending

- **One agent** → direct A2A `message/send` to that peer.
- **Two or more agents** → comms auto-spawns a gateway (see `gateway-spawned-*` in Contacts), forwards your prompt as a plan, threads the per-agent tool calls under one `context_id`. The gateway's `/plan` is bearer-gated; the inbox auto-loads `GATEWAY_API_KEY` from `gateway/.env.local` if it's there.

### Reading a thread

Each row carries:

- **State pill** — `submitted` · `working` · `input-required` · `payment-required` · `auth-required` · `completed` · `failed`. Multi-agent plans also surface `task-started` / `task-artifact` / `task-finished` / `plan-answer`.
- **Trust pill** — `first-contact` (new peer) · `known` · `self` (your own agents / planner).
- **DID** of the counterparty — click for the full agent card.
- Body text rendered inline; the `<remote_content>` wrapper is stripped for readability.

**Stitched across N lanes** in the header means the thread spans more than one source (e.g. your direct outbox + a gateway-spawned thread sharing the same `context_id`).

### Replying

Type in the box at the bottom of the open thread. `⌘↵` sends. Replies inherit the thread's `context_id` and resume the existing task if it's still open, refine it (with `referenceTaskIds`) if the task ended terminal, or start fresh otherwise.

## Files & directories

| Path | What's there |
| --- | --- |
| `inbox/data/events.db` | SQLite event log. Delete to start fresh; the schema rebuilds on boot. Gitignored. |
| `inbox/.env.local` | Per-developer env. Gitignored. Same shell-env vars below also work. |
| `inbox/scripts/logs/` | Demo-peer stdout/stderr. Gitignored. |
| `inbox/scripts/pids/` | Demo-peer pidfiles. Gitignored. |
| `~/.bindu/personal/persona.json` | Your operator persona. Hand-editable. |
| `~/.bindu/personal/.env` | Mode-`0600` env file: OpenRouter key, Pipedream tokens, Hydra URLs, `AUTH__ENABLED=true`. Regenerated on every spawn. |
| `~/.bindu/personal/agent.py` | Auto-generated bindufy agent. Hand-edits are overwritten — edit `persona.json` or the template in `server/personal-agent.ts`. |
| `~/.bindu/personal/.bindu/oauth_credentials.json` | OAuth client_id + secret from Hydra. Required for outbound token minting. |
| `~/.bindu/personal/.bindu/private.pem` | Ed25519 private key. Required for DID signatures. |
| `~/.bindu/personal/logs/agent.log` | Personal agent stdout/stderr. Tail this when spawn fails. |
| `examples/.env` | Shared env for the demo agents (`OPENROUTER_API_KEY=...`). The spawn script falls back to your shell env if this file isn't there. |

## Environment knobs

All optional unless noted:

| Var | Default | Why |
| --- | --- | --- |
| `BINDU_COMMS_TOKEN` | unset | Bearer token gate on `/api/*`. See "auth on" above. |
| `BINDU_WEBHOOK_TOKEN` | unset | Bearer token gate on `/webhooks/bindu/*`. Must match agent-side `global_webhook_token`. |
| `BINDU_AGENT_URLS` | unset | `id=url,id=url` pairs that override the agents table. Ops escape hatch. |
| `BINDU_REPO_DIR` | `..` | Where bindu lives. Needed if you moved the inbox out of the repo. |
| `BINDU_PERSONAL_DIR` | `~/.bindu/personal` | Personal agent files. Useful for sandboxing tests. |
| `BINDU_GATEWAY_DIR` | `../gateway` | Where the gateway lives. Needed if you split repos. |
| `GATEWAY_API_KEY` | read from `gateway/.env.local` | Bearer the inbox sends to the gateway's `/plan`. Without it multi-agent compose 401s. |
| `HYDRA__ADMIN_URL` | `https://hydra-admin.getbindu.com` | Hydra admin API. Used for OAuth client registration. |
| `HYDRA__PUBLIC_URL` | `https://hydra.getbindu.com` | Token endpoint for outbound Hydra minting. |
| `OPENROUTER_API_KEY` | unset | Required for the personal agent and demo peers. UI Settings tab is the recommended path. |
| `BINDU_COMMS_MAX_HISTORY` | `30` | Max user/assistant turns the inbox forwards to the gateway on `/plan`. |
| `BINDU_PERSONAL_USE_VENV` | unset | Skip `uv` and run the personal agent under `<repo>/.venv/bin/python` instead. |

## Troubleshooting

**`npm install` fails on `better-sqlite3`.** Native build needs Xcode CLI tools on macOS / `build-essential` on Linux. `xcode-select --install` or `apt install build-essential python3-dev`, then `rm -rf node_modules && npm install`.

**Port 3775 or 3787 already in use.** Something else is bound — usually an old inbox you forgot to stop. Find it: `lsof -ti:3775 -ti:3787 | xargs ps -p` to confirm it's stale, then `lsof -ti:3775 -ti:3787 | xargs kill`.

**UI loads but everything fails with "Failed to fetch".** The API on `3787` died. Check the `[api]` lines in your `npm run dev` output. Common: `better-sqlite3` ABI mismatch (`npm rebuild better-sqlite3`).

**Personal agent stays "down" after clicking Start.** Open `~/.bindu/personal/logs/agent.log` and read the last 30 lines:
- `OPENROUTER_API_KEY` not set → paste it in Settings or export it before `npm run dev`.
- Hydra unreachable (network/firewall blocking `hydra-admin.getbindu.com`) → set `HYDRA__ADMIN_URL` + `HYDRA__PUBLIC_URL` to a Hydra you can reach. If you don't have one, the public Bindu Hydra is the easiest path; check connectivity with `curl -sI https://hydra.getbindu.com/.well-known/openid-configuration`.
- `uv: command not found` → install uv (Prerequisites) or set `BINDU_PERSONAL_USE_VENV=1`.

**`-32009: Authentication is required` on every send.** Personal agent isn't running, or its Hydra OAuth client isn't registered. Check `~/.bindu/personal/.bindu/oauth_credentials.json` exists. Stop and re-spawn from the UI; watch the log.

**`spawn-demo-peers.sh` says `OPENROUTER_API_KEY not set and examples/.env missing`.** Either export the key in your current shell or create `examples/.env`:
```bash
echo "OPENROUTER_API_KEY=sk-or-v1-..." > examples/.env
```

**Add-a-peer says `agent-not-reachable` or returns no card.** The agent isn't up on that URL, or it's blocking `/.well-known/agent.json`. Confirm with `curl http://127.0.0.1:5773/.well-known/agent.json` — should return JSON.

**`pipedream-not-configured` when connecting Gmail/Notion.** Personal agent works fine without Pipedream — only the optional MCP tools need it. Either ignore or set `PIPEDREAM_PROJECT_ID` + `PIPEDREAM_CLIENT_ID` + `PIPEDREAM_CLIENT_SECRET` in Settings.

**`unauthorized` on `/api/plan`** (multi-agent compose). Either `GATEWAY_API_KEY` isn't loaded (inbox prints a warning at boot) or it doesn't match the gateway's value. The inbox auto-reads `gateway/.env.local` — make sure it's not stale.

**`SyntaxError` on Python startup.** You're on Python below 3.12. Install 3.12+ and re-run `uv sync` so `.venv` picks up the right interpreter.

**I want to nuke everything and start over.**
```bash
./scripts/stop-demo-peers.sh                                  # stop demo peers
# In the UI: click Stop on the personal-agent card, then close the tab.
rm -rf ~/.bindu/personal/                                     # forget your DID + Hydra client
rm -f  inbox/data/events.db inbox/data/events.db-{shm,wal}    # wipe inbox history
# Now restart from the Start it section.
```

## Build

```bash
npm run build       # TypeScript + Vite production build
npm run preview     # Serve the build locally
npm run typecheck   # tsc -b --noEmit, no emit
```

There's no production runtime story yet — the inbox is single-operator, single-machine. Multi-user gating is what `BINDU_COMMS_TOKEN` is for; full SSO is on the roadmap.

## Stack

React 19 · React Router v7 (SPA) · Vite 6 · Tailwind v4 · TanStack Query · Zustand · Phosphor icons · SQLite (events) via `better-sqlite3` · Hono on the API side.

## Attribution

Visual aesthetic inspired by [cloudflare/agentic-inbox](https://github.com/cloudflare/agentic-inbox) (Apache 2.0). See [NOTICE](./NOTICE).
