# Private Skills

## Why this page exists

When an agent advertises its skills, it exposes its capabilities to the world. This is great for open research agents but problematic for commercial agents where skill descriptions are proprietary. For example:

Imagine a compliance agent. Its value lies not in generic claims like "I do classification" but in specific capabilities like "I classify HS codes for steel imports under CBAM transitional rules." These descriptions are your product roadmap. If exposed publicly, they become a competitor's roadmap.

This page explains how to:

- Keep sensitive skills private.
- Share them only with trusted partners.
- Use `private_skills` and `allowed_dids` to control access.

---

## The idea behind private skills

Bindu agents support two views of their skill catalog:

1. **Public view**: Generic skills visible to everyone.
2. **Private view**: Full capabilities visible only to allowlisted partners.

This is achieved by splitting skills into `skills` (public) and `private_skills` (restricted). The agent exposes public skills at `/.well-known/agent.json` and private skills at `/agent/private.json`, gated by authentication and an allowlist.

---

## How to configure private skills

Here’s the smallest possible configuration:

```python
config = {
    "author": "you@example.com",
    "name": "acme_compliance_agent",
    "deployment": {"url": "http://localhost:3773"},

    "skills": [
        "skills/public-greet",
        "skills/public-status",
    ],

    "private_skills": [
        "skills/cbam-line-classify",
        "skills/eudr-due-diligence",
    ],

    "allowed_dids": [
        "did:bindu:partner-bank:agent:abc123",
        "did:bindu:partner-customs-broker:agent:def456",
    ],
}
```

### Key points:

- **Public skills**: Appear in `/.well-known/agent.json`.
- **Private skills**: Appear in `/agent/private.json` but only for allowlisted DIDs.
- **Allowlist**: Controls which DIDs can access private skills.

On disk, public and private skills are identical — each is a folder with a `skill.yaml`. The split is purely a configuration decision.

---

## How the gate works

Two layers protect private skills:

1. **Hydra middleware**: Verifies the OAuth bearer token and DID signature. Rejects unauthenticated requests with a `401`.
2. **Allowlist check**: Ensures the caller’s DID is in `allowed_dids`. Rejects unauthorized requests with a `403`.

If both checks pass, the agent returns a merged catalog of public and private skills.

---

## Testing the setup

Run the example agent:

```bash
uv run python examples/private_skills_agent/acme_compliance_agent.py
```

### Test cases

1. **Public view**:
   ```bash
   curl -s http://localhost:3773/.well-known/agent.json | jq '.skills[].id'
   ```
   Output:
   ```
   "public-greet"
   "public-status"
   ```

2. **Unauthorized private view**:
   ```bash
   curl -s -w "%{http_code}\n" http://localhost:3773/agent/private.json
   ```
   Output:
   ```
   {"error":"Authentication required for private agent card"}
   401
   ```

3. **Authorized private view**:
   With a valid bearer token and allowlisted DID:
   ```json
   {
     "id": "...",
     "skills": [
       {"id": "public-greet", "name": "greet"},
       {"id": "cbam-line-classify", "name": "CBAM classification"}
     ]
   }
   ```

---

## Operator workflow

- **Onboarding a partner**: Add their DID to `allowed_dids` and restart the agent.
- **Removing a partner**: Remove their DID and restart. Unauthorized requests will fail.
- **Audit trail**: Logs every request to `/agent/private.json` with details like `caller=`, `ip=`, and `result=`.

---

## When to use private skills

### Use this feature if:

- Your agent’s skill descriptions are proprietary.
- You sell to partners under contracts that restrict access.
- You want tiered discovery (e.g., trial users see only public skills).

### Skip this feature if:

- Your agent is open and meant to be discovered.
- You operate behind a corporate firewall.
- You’re early-stage and want maximum visibility.

---

## Limitations

This feature protects against:

| Threat                                   | Protected? |
|-----------------------------------------|------------|
| Random web crawlers                     | Yes        |
| Unauthenticated requests                | Yes        |
| Authenticated but unauthorized requests | Yes        |

It does NOT protect against:

| Threat                                   | Why not? |
|-----------------------------------------|----------|
| Authorized partners re-sharing skills   | Use NDAs |
| Plaintext skill descriptions in configs | By design |

---

## Where to look in the code

- **Handler**: [`bindu/server/endpoints/private_agent_card.py`](../bindu/server/endpoints/private_agent_card.py)
- **Config loader**: [`bindu/penguin/bindufy.py`](../bindu/penguin/bindufy.py)
- **Manifest fields**: [`bindu/common/models.py`](../bindu/common/models.py)
- **Tests**: [`tests/unit/server/endpoints/test_private_agent_card.py`](../tests/unit/server/endpoints/test_private_agent_card.py)
- **Example**: [`examples/private_skills_agent/`](../examples/private_skills_agent/)

---

## Related

- [SKILLS.md](./SKILLS.md): The underlying skill system.
- [AUTHENTICATION.md](./AUTHENTICATION.md): How Hydra-based auth works.
- [bugs/known-issues.md](../bugs/known-issues.md): Current limitations.
