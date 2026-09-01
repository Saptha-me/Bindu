# Quickstart: deploy your first bindu agent to the cloud

Hi! This guide walks you through deploying a bindu agent to a tiny computer
that lives on the internet, end to end, with no prior experience assumed.
By the end of it, you'll have an agent answering requests at a real
`https://...` URL — one that you (or anyone you share the URL with) can
talk to from anywhere.

If you've already run an agent locally with `python my_agent.py` and want
to know "okay, how do I make this real?" — this is for you.

> **Time budget:** ~10 minutes if your accounts are already set up.
> Most of that is waiting for the first deploy. After that, redeploys
> take about 15 seconds.

---

## What we're about to do

Right now, your bindu agent runs on your laptop. When you close the
terminal, the agent dies. Nobody else can reach it. That's fine for
development, but eventually you want the agent to be a *real service* —
running somewhere stable, on a public URL, that other agents and humans
can call.

We're going to ship the *exact same script* you'd run locally to a
[boxd](https://boxd.sh) **microVM**. A microVM is a tiny isolated Linux
machine that boots in seconds. boxd handles the boring parts: spinning
up the machine, giving it an HTTPS domain, keeping it alive. You write
your agent script. One command does the rest.

The command will be:

```bash
bindu deploy my_agent.py --runtime=boxd
```

That's it. Same script, one command, public URL.

---

## What you'll need

Three things, in order:

### 1. A boxd account and API key

Go to [boxd.sh](https://boxd.sh), sign up, and grab an API key from the
dashboard. It'll look something like `bxd_xxxxx...`. Keep it private —
anyone with this key can spin up VMs that get charged to your account.

Stash the key in your shell:

```bash
export BOXD_API_KEY="<your-key-from-boxd-dashboard>"
```

If you'd rather not retype it every time, add that line to your
`~/.zshrc` (or `~/.bashrc`).

> **Heads up:** the free tier covers small experiments. The example we
> deploy below uses ~$0.01 of compute. If you forget to pause your VM
> when you're done, you'll keep paying for it idling — we'll cover how
> to pause it at the end.

### 2. Bindu with the boxd extra installed

If you already have bindu installed, just add the optional `boxd` piece:

```bash
pip install 'bindu[runtime-boxd]'
```

Or, with `uv`:

```bash
uv add 'bindu[runtime-boxd]'
```

This pulls in the `boxd` Python library that knows how to talk to the
boxd cloud. The base `bindu` install doesn't include it because most
people don't deploy to boxd — you only pull it in when you need it.

### 3. An agent script

If you already have one (`my_agent.py` or whatever), great — keep using
it. If not, copy the one bundled with bindu. It's a 10-line echo agent
that just sends back whatever you send to it:

```bash
# From your shell, anywhere
curl -O https://raw.githubusercontent.com/getbindu/Bindu/main/examples/runtime-boxd-agent/agent.py
```

The whole thing looks like this:

```python
from bindu.penguin.bindufy import bindufy


def handler(messages):
    """Echo the latest user message back."""
    if not messages:
        return "send a message"
    return [
        {
            "role": "assistant",
            "content": messages[-1].get("content", ""),
        }
    ]


config = {
    "author": "you@example.com",
    "name": "runtime-boxd-example",
    "description": "Echo agent running inside a boxd microVM.",
    "deployment": {
        "url": "http://0.0.0.0:3773",
        "expose": True,
    },
}


if __name__ == "__main__":
    bindufy(config, handler)
```

Nothing surprising here. A handler function, a config dict, a
`bindufy()` call. Notice there's *nothing* about boxd in this file —
the deploy logic lives entirely in the CLI. Same script works for
`python agent.py` locally and `bindu deploy agent.py` to the cloud.

---

## Step 1: see what would happen (a safe dry run)

Before you spend any money, let's see what bindu *would* do if you
deployed. This step doesn't touch the cloud at all:

```bash
bindu deploy agent.py --runtime=boxd --dry-run
```

You should see something like:

```
DRY RUN — nothing will be deployed.

  agent name:    runtime-boxd-example
  source root:   /Users/you/playground
  entry script:  agent.py
  provider:      boxd
  vcpu / memory: 2 / 4G
  disk:          20G
  auto_suspend:  0s
  on_exit:       suspend
  bindu_version: local
  tarball:       4 files, 2.4 KB compressed
```

This is the *plan*. It tells you:

- **What the VM will be named** (`runtime-boxd-example` — bindu reads
  this from `config["name"]` in your script).
- **What hardware it gets** (2 vCPUs, 4 GB RAM, 20 GB disk by default).
- **What files will be uploaded** (just 4 files — your script plus a
  couple of metadata files).

If something looks wrong here (e.g., the agent name has a typo, or the
tarball is way bigger than you expected because you have a 200 MB
dataset in the same folder), fix it now. Dry runs are cheap.

> **Why "tarball"?** A tarball is just a bundle of files squished into
> one. Bindu packages up your folder into a single compressed file,
> uploads that one file to the VM, and unpacks it on the other side.
> Faster than uploading files one by one.

---

## Step 2: actually deploy

```bash
bindu deploy agent.py --runtime=boxd
```

The first deploy takes about a minute. Here's what you'll see scrolling
past in your terminal:

```
warning: dropped 2 sensitive file(s) from the deploy tarball
✓ runtime-boxd-example serving at https://runtime-boxd-example.boxd.sh

[runtime-boxd-example] INFO     Generated agent_id: 80fc00b6-a5ac-...
[runtime-boxd-example] INFO     Initializing DID extension...
[runtime-boxd-example] INFO     ✅ DID configuration and keys pass integrity check
[runtime-boxd-example] INFO     Creating agent manifest...
[runtime-boxd-example] INFO     Agent 'did:bindu:...' successfully bindufied!
[runtime-boxd-example] INFO     Starting uvicorn server at 0.0.0.0:3773...
[runtime-boxd-example] INFO     ✅ Storage initialized: InMemoryStorage
[runtime-boxd-example] INFO     ✅ TaskManager started
[runtime-boxd-example] INFO     Application startup complete.
```

A few things to notice:

- **"dropped 2 sensitive file(s)"** — bindu found things in your folder
  that look like secrets (e.g., `.env`, `.pem` keys) and refused to
  upload them. This is a safety net: a VM with a public IP is the *last*
  place you want your API keys to live. We'll cover how to pass secrets
  *correctly* in a moment.
- **"✓ runtime-boxd-example serving at https://..."** — there it is.
  Your agent is alive on the internet at that URL. Bookmark it.
- **All the `[runtime-boxd-example]` lines** — these are the logs from
  *inside the VM*, streamed back to your terminal. The deploy command
  stays in the foreground showing you logs until you hit Ctrl-C.

Leave the deploy command running. Open another terminal for the next
step.

> **What just happened, in plain words:** bindu zipped up your script,
> told boxd "please make me a Linux VM with this code," waited for the
> VM to boot, copied your code in, ran `pip install bindu`, started
> your agent inside the VM, and hooked up a public HTTPS domain that
> forwards to it. That's it.

---

## Step 3: talk to your live agent

In a fresh terminal:

```bash
# Set this once
URL="https://runtime-boxd-example.boxd.sh"

# Is it alive?
curl $URL/health
```

You'll see something like:

```json
{
  "version": "0.3.14",
  "health": "healthy",
  "application": {
    "agent_did": "did:bindu:you_at_example_com:runtime-boxd-example:80fc00b6-..."
  },
  "status": "ok",
  "ready": true,
  "uptime_seconds": 18.11
}
```

"Healthy". "Ready". Good. Notice the `agent_did` — that's your agent's
cryptographic identity. We'll come back to it.

Now let's send it an actual message. Bindu agents speak a protocol
called **A2A** ("agent-to-agent"). It's just JSON over HTTP, but the
shape is opinionated — every message needs a unique ID (a UUID), and
messages live inside *tasks*, which live inside *contexts* (think:
conversation threads).

The shortest possible "hello":

```bash
REQ_ID=$(uuidgen)
MSG_ID=$(uuidgen)
CTX_ID=$(uuidgen)
TASK_ID=$(uuidgen)

curl -s -X POST $URL/ \
  -H 'Content-Type: application/json' \
  --data-raw "{
    \"jsonrpc\": \"2.0\",
    \"id\": \"$REQ_ID\",
    \"method\": \"message/send\",
    \"params\": {
      \"configuration\": {\"acceptedOutputModes\": [\"text\"]},
      \"message\": {
        \"role\": \"user\",
        \"kind\": \"message\",
        \"parts\": [{\"kind\": \"text\", \"text\": \"hello!\"}],
        \"messageId\": \"$MSG_ID\",
        \"contextId\": \"$CTX_ID\",
        \"taskId\": \"$TASK_ID\"
      }
    }
  }" | python -m json.tool
```

You'll get back a *task object* — the agent has accepted your message
and is processing it. Pull out the task ID it returned:

```json
{
  "result": {
    "id": "0df35c9d-b96d-...",
    "status": {"state": "submitted"}
  }
}
```

Now ask for the result:

```bash
# Replace <task-id> with the "id" from the previous response
curl -s -X POST $URL/ \
  -H 'Content-Type: application/json' \
  --data-raw "{
    \"jsonrpc\": \"2.0\",
    \"id\": \"$(uuidgen)\",
    \"method\": \"tasks/get\",
    \"params\": {\"taskId\": \"<task-id>\"}
  }" | python -m json.tool
```

And there's your echo, back from the VM:

```json
{
  "result": {
    "status": {"state": "completed"},
    "artifacts": [
      {
        "name": "result",
        "parts": [
          {
            "text": "hello!",
            "metadata": {
              "did.message.signature": "Gj7ar6GJdTrjD8asKT24..."
            }
          }
        ]
      }
    ]
  }
}
```

The `did.message.signature` field is the agent *cryptographically
signing its response*. Anyone receiving this artifact can verify the
agent really sent it (and nobody tampered with it in transit) using the
agent's public DID. You didn't have to write a line of crypto code —
bindu handled it.

You just had a complete round-trip with an agent running in a VM you
don't manage, on a domain you don't own, with a signature you can
verify. That's the whole point.

---

## Step 4: pausing your VM (so you stop paying for it)

When you're done experimenting, head back to the terminal where
`bindu deploy` is still running. Press **Ctrl-C**.

By default, that **suspends** your VM. Suspending means: "freeze the
machine in its current state, keep the disk around, stop billing for
CPU." Cheap to keep, instant to wake up.

Next time you run `bindu deploy agent.py --runtime=boxd`, the same VM
resumes in a couple of seconds with everything exactly as you left it —
DID keys, conversation history, the lot.

If you want different behavior on Ctrl-C, pass `--on-exit`:

| Flag value | What happens on Ctrl-C |
|---|---|
| `--on-exit=suspend` (default) | Freeze the VM. Keeps disk, stops CPU billing. Fast resume. |
| `--on-exit=destroy` | Delete the VM entirely. You'll start fresh next time. |
| `--on-exit=detach` | Leave the VM running. Bills continue. Useful when you want the agent to keep serving even after you close your laptop. |

If you want the VM to stay running but go to sleep automatically
during idle periods, use `--auto-suspend`:

```bash
bindu deploy agent.py --runtime=boxd --auto-suspend=60
```

This means: "after 60 seconds with no HTTP requests, suspend yourself."
The next incoming request wakes it back up. Great for cost control on
agents that don't get traffic 24/7.

> **One known wart:** in bindu v2026.20.2, `--on-exit=suspend` sometimes
> doesn't fire cleanly when you hit Ctrl-C from a non-interactive shell
> (like a script). If you suspect the VM kept running, check the boxd
> dashboard. To force-suspend from Python:
>
> ```python
> from boxd import AsyncBoxd
> import asyncio
>
> async def main():
>     async with AsyncBoxd() as boxd:  # reads BOXD_API_KEY from the env
>         machine = await boxd.machines.get("runtime-boxd-example")
>         await boxd.machines.pause(machine.id)  # or .delete(machine.id)
>
> asyncio.run(main())
> ```
>
> Tracked in our bug list — interactive Ctrl-C from a normal terminal
> works fine; this is a corner case.

---

## What about secrets?

Your real agents will need API keys (OpenAI, Anthropic, etc.). **Never
put these in your script.** Two reasons:

1. If you check the script into git, your key goes with it.
2. Bindu refuses to upload `.env` files for the same reason.

The right way: pass them as `--env` flags on `bindu deploy`:

```bash
bindu deploy agent.py --runtime=boxd \
  --env OPENAI_API_KEY=sk-... \
  --env ANTHROPIC_API_KEY=sk-ant-...
```

These get injected into the VM's environment, so your script can read
them with `os.getenv("OPENAI_API_KEY")` exactly like it would locally.
They don't end up in the source tarball, and they don't end up in git.

---

## Useful follow-up commands

While your VM is running:

| Command | What it does |
|---|---|
| `bindu logs runtime-boxd-example` | Stream your agent's stdout to your terminal. Like `tail -f`. |
| `bindu logs runtime-boxd-example --no-follow` | Print the log so far and exit. |
| `bindu shell runtime-boxd-example` | Open an interactive bash shell *inside* the VM. Useful when something's broken and you want to poke around. |

The agent name (`runtime-boxd-example` here) is the same as
`config["name"]` in your script.

---

## Things that will trip you up at least once

**"BOXD_API_KEY or BOXD_TOKEN must be set"** — you forgot the
`export BOXD_API_KEY=...` step. Check `echo $BOXD_API_KEY` is not
empty.

**"agent at <url> did not become healthy within 60s"** — the VM is up
but your script crashed before serving. Run `bindu logs <name>` and look
at the bottom for the actual Python error. Common cause: you imported a
package that isn't in `pyproject.toml` (or `requirements.txt`).

**"old code is running after redeploy"** — you edited the script, but
when you redeployed, the old version is still serving. Almost always
because the previous Python process didn't get killed cleanly inside
the VM. Run `bindu shell <name>` and `pkill -f python3`, then
redeploy.

**"my agent works locally but fails inside the VM with `ModuleNotFoundError`"**
— the VM only installs the deps it can see. If your dep isn't in a
`pyproject.toml`, `requirements.txt`, or `setup.py` *inside the folder
that gets uploaded*, the VM doesn't know to install it. Easiest fix:
write a tiny `pyproject.toml` next to your `agent.py` listing the deps.

**"the tarball is way too big"** — bindu caps the upload at 50 MB
compressed. If you've got a virtualenv or model files in the same
folder, exclude them with a `.binduignore` file (works like
`.gitignore`):

```
# .binduignore
.venv/
data/
*.bin
```

---

## Where to go next

- **[boxd.md](boxd.md)** — every `bindu deploy` flag spelled out in
  detail. Read this when you start needing finer control (bigger VMs,
  custom images, etc.).
- **[custom-image.md](custom-image.md)** — for when your dep can't be
  `pip install`-ed and you need a pre-baked Docker image.
- **[README.md](README.md)** — runtime providers overview and the
  reasoning behind the design.
- **[boxd's own docs](https://docs.boxd.sh)** — for understanding the
  microVM platform itself: pricing, regions, the Python SDK we're using
  under the hood.

You've now got a complete loop: write a script, deploy it, talk to it,
suspend it, redeploy it. That's the whole workflow. Everything else
(secrets, sizing, custom images) is just dialing in details on top of
this loop.

Happy shipping. 🌻
