# Runtime providers

A bindu agent's *runtime* is where its Python process actually executes.
By default, `python my_agent.py` runs the agent in your own terminal — that's
the in-process runtime. The `bindu deploy` CLI lets you run the same script
*elsewhere* via a `RuntimeProvider`. The canonical example is
`BoxdRuntimeProvider`, which runs the agent inside a [boxd](https://boxd.sh)
microVM with its own public URL, DID, and HTTPS domain.

## When to use

- **Default (in-process):** local development, anywhere you control the
  process and the network. Just `python my_agent.py`.
- **Boxd runtime (`bindu deploy --runtime=boxd`):** when you want the agent
  to be a *real* microservice — isolated from your laptop, addressable on a
  public URL, with its own identity and persistent state. Required for hosted
  multi-tenant agents.

## Design: deploy is a CLI verb, not a kwarg

The agent script is *pure runtime* — no deploy concerns leak into it:

```python
from bindu.penguin.bindufy import bindufy


def handler(messages):
    # A2A contract: the message text lives in parts.
    text = " ".join(
        p.get("text", "")
        for p in messages[-1].get("parts", [])
        if p.get("kind") == "text"
    )
    return [{"role": "assistant", "content": text}]


config = {
    "name": "my-agent",
    "description": "echo agent",
    "deployment": {"url": "http://localhost:3773"},
}

bindufy(config, handler)
```

Run locally: `python my_agent.py` → serves on `localhost:3773`.

Deploy remotely: `bindu deploy my_agent.py --runtime=boxd --auto-suspend=60` →
serves on `https://my-agent.boxd.sh`. Output:

```
✓ my-agent serving at https://my-agent.boxd.sh

[my-agent] INFO: Started server process [12]
[my-agent] INFO: Application startup complete.
```

The same script runs in both contexts; only the launch verb changes. Inside
the deployed VM the agent runs via `bindu serve --script my_agent.py`, which
is just `python my_agent.py` plus a few CLI niceties — `bindufy()` serves
in-process, exactly as it does locally.

A2A clients can now reach the agent at `https://my-agent.boxd.sh`. Ctrl-C
detaches; the VM auto-suspends after 60s of inactivity. Re-running
`bindu deploy` resumes the same VM and updates the source.

## See also

- **[quickstart.md](quickstart.md)** — friendly walkthrough for your first deploy.
  Start here if you've never used `bindu deploy` before.
- [boxd.md](boxd.md) — full `bindu deploy` flag reference for the boxd runtime.
- [custom-image.md](custom-image.md) — A1 mode (user-built Docker images).
- [`docs/superpowers/specs/2026-04-29-bindu-runtime-design.md`](../superpowers/specs/2026-04-29-bindu-runtime-design.md) — design rationale.

## Limitations (v1)

- One runtime provider ships in-tree: `boxd`. The abstraction supports
  others (e2b, modal, fly.io) but no providers besides boxd are bundled.
- No live source-watch / auto-redeploy. Editing your agent script requires
  re-running `bindu deploy`.
- No declarative manifest (`bindu.toml`) yet; all deploy config is via CLI
  flags. Planned as a follow-up.
