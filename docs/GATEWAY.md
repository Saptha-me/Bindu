# The Bindu Gateway — an end-to-end story

You've heard the words. *Agent. Planner. A2A. Multi-agent orchestration.*
By the end of this document you'll have run all of those things yourself,
watched them talk to each other, and taught them a new trick. No prior
knowledge of AI agents required — we'll introduce each idea when you need
it, and never before.

Budget about **45 minutes** if you're reading straight through and running
the commands. If you skip the commands and just read, ~15 minutes.

---

## Table of contents

1. [Why a gateway exists](#chapter-1--why-a-gateway-exists)
2. [Hello, gateway](#chapter-2--hello-gateway)
3. [Adding a second agent](#chapter-3--adding-a-second-agent)
4. [Teaching it a pattern (recipes)](#chapter-4--teaching-it-a-pattern-recipes)
5. [Giving it an identity (DID signing)](#chapter-5--giving-it-an-identity-did-signing)
6. [What's next](#chapter-6--whats-next)

---

## Chapter 1 — Why a gateway exists

Imagine you've built three AI agents. Each is a small program that listens
on an HTTP port and answers specific kinds of questions:

- A **research agent** that searches the web for facts.
- A **math agent** that solves numerical problems.
- A **poet agent** that writes short verse.

Now a user asks: *"Look up the population of Tokyo, then calculate 0.5% of
it, then write a four-line poem about that number of people."*

Without a gateway, **you** — the programmer — have to:

1. Decide the question needs all three agents.
2. Write code that calls the research agent first.
3. Parse the answer to extract "36.95 million".
4. Pass that to the math agent.
5. Parse "184,750".
6. Pass that to the poet agent.
7. Collect and return the final poem.

That's not hard for one question. But what about the next hundred questions?
Each one needs its own chain, its own parsing, its own error handling. And
as soon as a new agent joins the roster, every existing chain might want to
use it.

**The gateway is the thing that does steps 1-7 for you.** You hand it a
question and a list of agents. It figures out which agents to call, in what
order, with what input. You get back a stream of what happened and, at the
end, a final answer.

### How does it "figure it out"?

The gateway has one trick: it uses an LLM — a large language model, like
Claude or GPT — as a **planner**. The planner sees:

- The user's question
- A short description of each available agent
- Its own system prompt (general instructions the gateway operator wrote)

Then it decides, turn by turn, which agent to call next. The output of each
call feeds back into the planner's context, and it decides whether to call
another agent, write a final answer, or ask the user a clarifying question.

Modern LLMs are surprisingly good at this. Anthropic calls it
["tool use"](https://docs.anthropic.com/claude/docs/tool-use), OpenAI calls
it "function calling" — same idea. The gateway wires your agents up as
"tools" the planner can invoke and lets the LLM drive.

### What the gateway is not

- **It's not another agent.** It doesn't generate answers itself. It
  orchestrates the ones you already have.
- **It doesn't host agents.** You give it a list of agents per request.
  The agents run wherever they run — your laptop, a cluster, a third-party
  service. The gateway just calls them.
- **It doesn't have opinions about your agents.** As long as each agent
  speaks [A2A](https://github.com/GetBindu/Bindu) (a small JSON-RPC 2.0
  protocol), the gateway can call it. The Bindu team authored A2A, and
  `bindufy()`-built agents speak it out of the box.

### What you'll build by the end of this document

By Chapter 3 you'll have three agents running locally, and you'll watch the
gateway chain them automatically to answer a multi-part question.

By Chapter 4 you'll have written a **recipe** — a short markdown file that
teaches the planner a reusable pattern without writing any code.

By Chapter 5 you'll have given your gateway a **cryptographic identity**
and watched its outbound calls get signed, so downstream agents can verify
the calls are really coming from your gateway and not from an impostor.

Let's go.

---

## Chapter 2 — Hello, gateway

This chapter has seven steps. Follow them in order.

### Step 1 — What you need

You need three things before starting. You may already have them; skim and
decide.

- **Node.js 22+**. The gateway is TypeScript; we run it with `tsx`, which
  doesn't require a separate build step. Check yours:
  ```bash
  node --version    # should print v22.x or higher
  ```
- **An OpenRouter API key**. OpenRouter is a paid service that proxies to
  dozens of language models under one API. The gateway uses it for the
  planner LLM. Sign up at [openrouter.ai](https://openrouter.ai), add a
  few dollars of credit, and copy the key from the *API* section. It
  looks like `sk-or-v1-<long random string>`.
- **…or an OrcaRouter API key.** [OrcaRouter](https://www.orcarouter.ai)
  is an alternative OpenAI-compatible gateway the gateway can use for
  the planner instead of OpenRouter. Sign up and grab a key from the
  console; it looks like `sk-orca-<long random string>`. Throughout
  this guide, set either `OPENROUTER_API_KEY` or `ORCAROUTER_API_KEY` —
  whichever gateway you configure — and reference models as
  `openrouter/<model-id>` or `orcarouter/<model-id>`.
- **A Supabase project**. Supabase is a hosted Postgres service with a
  free tier. The gateway uses it to store conversation history between
  turns. Create a project at [supabase.com](https://supabase.com), then
  grab two values from *Project Settings → API*:
  - Project URL (looks like `https://abcdef.supabase.co`)
  - Service role key (starts with `eyJ...`, this is sensitive — don't
    paste it in chat apps)

### Step 2 — Get the code and install

```bash
git clone https://github.com/GetBindu/Bindu
cd Bindu

# Python side — runs the small sample agents we'll call
uv sync --dev --extra agents

# TypeScript side — runs the gateway
cd gateway
npm install
cd ..
```

The `uv sync` line uses [uv](https://github.com/astral-sh/uv), a fast
Python package manager. If you don't have it, `curl -LsSf
https://astral.sh/uv/install.sh | sh` installs it in a few seconds.

### Step 3 — Apply the database schema

The gateway expects two tables in your Supabase project. From the Supabase
web UI, go to *SQL Editor*, then run the two files in this order:

```
gateway/migrations/001_init.sql
gateway/migrations/002_compaction_revert.sql
```

These create `gateway_sessions`, `gateway_messages`, and `gateway_tasks`
tables with row-level security policies appropriate for a service-role
caller. You won't edit these tables directly — the gateway reads and writes
them.

### Step 4 — Configure the gateway

Create `gateway/.env.local` from the template:

```bash
cp gateway/.env.example gateway/.env.local
```

Open `gateway/.env.local` in an editor. Fill in:

```bash
# Supabase (session store)
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your service role key, starts with "eyJ...">

# One bearer token the caller must send to talk to the gateway.
# Generate a strong one:
#   openssl rand -base64 32 | tr -d '=' | tr '+/' '-_'
# Paste the output here:
GATEWAY_API_KEY=<paste generated token>

# The planner AI
OPENROUTER_API_KEY=sk-or-v1-<your key>
# …or use OrcaRouter instead (whichever gateway you pick):
# ORCAROUTER_API_KEY=sk-orca-<your key>

# Gateway listens here
GATEWAY_PORT=3774
GATEWAY_HOSTNAME=0.0.0.0
```

And `examples/.env` (used by the sample Python agents — the file already
exists, you just add the key):

```bash
# examples/.env
OPENROUTER_API_KEY=sk-or-v1-<same key>
```

> **Aside — what's a "bearer token"?**
> Think of `GATEWAY_API_KEY` like the password on a movie ticket booth.
> Whoever holds this string can ask the gateway to do work on their
> behalf. The gateway checks it on every request by hashing both sides and
> comparing the hashes in constant time (so neither a timing nor a length
> attack can recover the token). Don't paste it into chat apps or commit
> it to a public repo. Rotate it when you suspect it leaked.

### Step 5 — Start one agent

Open a terminal. Start the joke agent — it's one Python file that listens
on port 3773 and answers with jokes:

```bash
python3 examples/gateway_test_fleet/joke_agent.py
```

You'll see output like:

```
[joke_agent] starting on http://0.0.0.0:3773
[joke_agent] DID: did:bindu:...
[joke_agent] ready.
```

Leave that terminal running.

### Step 6 — Start the gateway

In a **second** terminal:

```bash
cd gateway
npm run dev
```

Expected output:

```
[bindu-gateway] no DID identity configured (set BINDU_GATEWAY_DID_SEED...)
[bindu-gateway] listening on http://0.0.0.0:3774
[bindu-gateway] session mode: stateful
```

The "no DID identity configured" line is fine for now. Chapter 5 will
turn on cryptographic signing. Leave this terminal running too.

### Step 7 — Ask a question

In a **third** terminal, load your gateway token into the shell so you
don't have to copy-paste it every time:

```bash
set -a && source gateway/.env.local && set +a
```

Now send the request:

```bash
curl -N http://localhost:3774/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me a joke about databases.",
    "agents": [
      {
        "name": "joke",
        "endpoint": "http://localhost:3773",
        "auth": { "type": "none" },
        "skills": [{ "id": "tell_joke", "description": "Tell a joke" }]
      }
    ]
  }'
```

The `-N` flag tells curl not to buffer — you'll see output appear one line
at a time over about 5 seconds:

```
event: session
data: {"session_id":"s_01H...","external_session_id":null,"created":true}

event: plan
data: {"plan_id":"m_01H...","session_id":"s_01H..."}

event: task.started
data: {"task_id":"call_01H...","agent":"joke","skill":"tell_joke","input":{"input":"Tell me a joke about databases."}}

event: task.artifact
data: {"task_id":"call_01H...","content":"<remote_content agent=\"joke\" verified=\"unknown\">Why did the database admin break up? Because they had too many relationships!</remote_content>"}

event: task.finished
data: {"task_id":"call_01H...","state":"completed"}

event: text.delta
data: {"session_id":"s_01H...","part_id":"p_01H...","delta":"Here"}

event: text.delta
data: {"session_id":"s_01H...","part_id":"p_01H...","delta":"'s a joke..."}
... (many more deltas) ...

event: final
data: {"session_id":"s_01H...","stop_reason":"stop","usage":{"inputTokens":1130,"outputTokens":52,"totalTokens":1182,"cachedInputTokens":0}}

event: done
data: {}
```

You made a plan.

### Reading the output line by line

That output format is called **Server-Sent Events** (SSE). It's plain HTTP,
but the server keeps the connection open and writes events one at a time
instead of sending one big response at the end. Two parts per event: a
label (`event: session`) and a JSON payload (`data: {...}`).

What each event means, in the order they arrived:

1. **`session`** — the gateway opened a conversation. `session_id` is the
   unique handle; you can pass it back later to resume.
2. **`plan`** — the planner started its first turn.
3. **`task.started`** — the planner decided to call the joke agent.
   `input: {input: "..."}` is what it's sending.
4. **`task.artifact`** — the agent replied. The text inside
   `<remote_content>` is the real answer. That envelope is there so the
   planner (and you) remember this is *untrusted* data — the agent could
   be anything, and we shouldn't let its reply execute instructions that
   weren't in the original user question.
5. **`task.finished`** — that call is complete.
6. **`text.delta`** (many) — the planner is now writing its own final
   answer, streamed a word or two at a time. Concatenate them in order
   (they all share a `part_id`) to reconstruct the full text.
7. **`final`** — done. `stop_reason: "stop"` means "natural end".
   `usage` reports token counts for billing.
8. **`done`** — last event. Close the connection.

### What's actually running

You now have three things talking to each other:

```
┌─────────────┐   bearer-auth POST /plan   ┌────────────────────┐
│   curl      │ ─────────────────────────▶ │  Bindu Gateway     │
│             │ ◀───  SSE event stream ─── │  port 3774         │
└─────────────┘                             │  (planner LLM ───▶ OpenRouter / OrcaRouter)
                                            │  (sessions ─────▶ Supabase)
                                            └──┬─────────────────┘
                                               │ A2A (JSON-RPC)
                                               ▼
                                            ┌──────────────────┐
                                            │ joke_agent.py    │
                                            │ port 3773        │
                                            └──────────────────┘
```

The gateway is a **coordinator**. It doesn't answer the question itself;
it picks an agent, sends the question, gets the reply, writes a final
summary using its own planner LLM.

If this is the moment the idea clicks — great. Next chapter we'll add a
second agent so the gateway has a real choice to make.

---

## Chapter 3 — Adding a second agent

Stop the joke agent (Ctrl-C in its terminal). We'll start both it and
four more using a helper script:

```bash
./examples/gateway_test_fleet/start_fleet.sh
```

Expected output:

```
  [joke_agent]      started, pid=64945
  [math_agent]      started, pid=64958
  [poet_agent]      started, pid=64969
  [research_agent]  started, pid=64980
  [faq_agent]       started, pid=64993
```

Five agents now, each on its own port:

| Agent | Port | Does |
|---|---|---|
| joke_agent | 3773 | Tells jokes |
| math_agent | 3775 | Solves math problems step-by-step |
| poet_agent | 3776 | Writes short poems |
| research_agent | 3777 | Web search + summarize a factual question |
| faq_agent | 3778 | Answers from a canned FAQ |

Each is ~60 lines of Python. Open any one — say
[joke_agent.py](../examples/gateway_test_fleet/joke_agent.py) — and you'll see
a small configuration that wires a language model (`openai/gpt-4o-mini`)
to a few lines of instructions ("tell jokes, refuse other requests").
Narrow scope on purpose so mistakes are visible.

The gateway is already running from Chapter 2; don't restart it.

### A three-agent question

Paste this into your curl terminal. It asks something that genuinely needs
three agents to answer:

```bash
curl -N http://localhost:3774/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "First research the current approximate population of Tokyo. Then compute what exactly 0.5% of that population is. Finally write a 4-line poem celebrating that number of people.",
    "agents": [
      {
        "name": "research", "endpoint": "http://localhost:3777",
        "auth": { "type": "none" },
        "skills": [{ "id": "web_research", "description": "Web search and summarize a factual question" }]
      },
      {
        "name": "math", "endpoint": "http://localhost:3775",
        "auth": { "type": "none" },
        "skills": [{ "id": "solve", "description": "Solve math problems step-by-step" }]
      },
      {
        "name": "poet", "endpoint": "http://localhost:3776",
        "auth": { "type": "none" },
        "skills": [{ "id": "write_poem", "description": "Write a short poem" }]
      }
    ]
  }'
```

This takes around 15 seconds and produces three `task.started` events,
in order — research first, then math, then poet. Real output from a
recent run (abbreviated):

```
task.started  → research called with "What is the current population of Tokyo?"
task.artifact → "Tokyo's metropolitan area has approximately 36.95 million people..."
task.finished → completed

task.started  → math called with "Compute 0.5% of 36,950,000"
task.artifact → "0.005 × 36,950,000 = 184,750"
task.finished → completed

task.started  → poet called with "Write a 4-line poem about 184,750 people"
task.artifact → "In Tokyo's heart, where dreams align, / 184,750 souls brightly shine, / ..."
task.finished → completed

text.delta    → "Step 1 — Population: 36.95 million..."
...
final
done
```

**The gateway chose the order, extracted the right number from each
reply, and passed it to the next agent — all without you writing a single
line of glue code.** That's the whole point.

### How it chose

The planner saw three tools available (one per agent-skill combination):

| Tool name | Description |
|---|---|
| `call_research_web_research` | Web search and summarize a factual question |
| `call_math_solve` | Solve math problems step-by-step |
| `call_poet_write_poem` | Write a short poem |

(You might wonder where those tool names came from. The gateway builds
them automatically from the `name` and `skills[].id` fields in your
request: `call_<agent-name>_<skill-id>`.)

Then the planner read the question: *"First research… Then compute… Finally
write a 4-line poem…"* The word "First" strongly suggests research is
step 1, and the LLM picked `call_research_web_research`. It waited for the
reply, re-read the question with the new context, decided the next step
was math, picked `call_math_solve`, and so on.

This all happens inside one HTTP request. The SSE stream is the gateway
narrating what the planner decided.

### What if you added a fourth agent it doesn't need?

Try it. Add the joke agent to the catalog above and re-run:

```json
{
  "name": "joke", "endpoint": "http://localhost:3773",
  "auth": { "type": "none" },
  "skills": [{ "id": "tell_joke", "description": "Tell a joke" }]
}
```

The SSE output is the same — three `task.started` events for research,
math, poet. The joke tool sat there unused. **The planner only calls what
it needs.** This matters in production: you can hand the gateway a
catalog of 50 agents, and only the 2 or 3 relevant to a given question
will actually be invoked.

### An aside — what is the planner, actually?

Inside the gateway, there's a single agent configuration file called
`gateway/agents/planner.md`. It's a markdown file with some frontmatter:

```yaml
---
name: planner
model: openrouter/anthropic/claude-sonnet-4.6
steps: 10
permission:
  ...
---

# System prompt body — the planner's own instructions.
```

(The `model` value can be any supported provider/model pair — e.g.
`openrouter/anthropic/claude-sonnet-4.6` or
`orcarouter/anthropic/claude-opus-4.7`.)

The body is the system prompt. On each `/plan` request, the gateway:

1. Reads the planner's system prompt.
2. Adds the user's question as a new "user" message.
3. Builds the tool list from your `agents[]` catalog.
4. Hands all of that to the configured gateway (OpenRouter or OrcaRouter)
   with `streamText()`.
5. Streams the output back to you as SSE.

Inside OpenRouter or OrcaRouter, Claude (or whichever model you configured)
runs its agentic loop — text → tool call → tool result → more text →
another tool call → final text. The gateway's job is just to execute the
tool calls against your real agents and plumb the results back.

Open `gateway/agents/planner.md` and read the body. That's the instructions
the coordinator AI follows. You can edit it and the next plan will see the
changes — the file is loaded on every request, not cached.

---

## Chapter 4 — Teaching it a pattern (recipes)

The three-agent chain from Chapter 3 worked because the planner figured
the plan out from scratch. That's fine once, but let's say your team keeps
asking the same class of question: "research this, compute some percentage
of it, write a poem about the result." Every plan the planner re-derives
the same steps. You pay for the LLM time every time.

What if you could write the plan down *once*, in plain markdown, and have
the planner load it on demand when it recognizes a match?

That's a **recipe**.

### The core idea: progressive disclosure

You could try solving this by dumping a big "how to coordinate these
agents" paragraph into the planner's system prompt. Fine for one pattern.
Doesn't scale — after 20 patterns, your system prompt is 20,000 tokens and
the planner is paying to read it all on every request, even the ones that
don't need any of them.

Recipes fix this with a technique called **progressive disclosure**. At
every turn the planner sees:

- The *name* and *one-line description* of every recipe (cheap — a few
  hundred tokens even for dozens of recipes).
- A tool called `load_recipe({name})` in its toolbox.

Only when the planner recognizes a match does it call `load_recipe`. The
tool's reply is the full recipe body — typically a 2-3 KB markdown
playbook — injected into the conversation. The planner then follows the
body for the rest of the turn.

You paid for the body's tokens exactly once per plan, and only when the
recipe was actually relevant.

### Your first recipe

Let's write one. Create a file at
`gateway/recipes/research-math-poem/RECIPE.md` with this content:

```markdown
---
name: research-math-poem
description: Research a factual number, compute a percentage of it, and write a short poem about the result. Load when the user asks a three-part question combining research, arithmetic, and creative writing.
tags: [research, math, creative]
triggers: [research and compute, percentage poem, population percent]
---

# Recipe: research-math-poem

Use this when the user's question has three distinct phases:

  1. A factual lookup (population, revenue, distance, etc.)
  2. A percentage or fraction applied to that number
  3. A short creative response about the result

## Flow

1. **Research.** Call `call_research_web_research` with the user's exact
   factual question. Don't translate or summarize it.
2. **Extract the number.** In your own reasoning (not as a tool call),
   pull the headline figure from the research reply. Prefer the
   *headline* number the user asked about, not incidental figures.
3. **Compute.** Call `call_math_solve` with the computation stated
   explicitly: "Compute 0.5% of 36,950,000". Don't ask the math agent
   to interpret — give it the exact expression.
4. **Create.** Call `call_poet_write_poem` with the computed number
   and the user's creative framing (line count, mood, subject).
5. **Respond.** Write a final message that shows all three steps
   briefly and ends with the poem.

## Constraints

- **Do not parallelize** the calls. The math depends on the research;
  the poem depends on the math.
- **Do not invent the number** if research returns ambiguous output.
  Ask the user to clarify which population/revenue/etc. they mean.
- **Do not skip the poem** if the user asked for one. If
  `call_poet_write_poem` fails, surface the failure; don't silently
  produce prose.
```

### Watching it load

Restart the gateway (Ctrl-C in its terminal, `npm run dev` again). You'll
see a new log line on boot:

```
[recipe] loaded 3 recipes
```

(Three because two recipes shipped with the gateway by default —
`multi-agent-research` and `payment-required-flow` — plus your new one.)

Now fire the same three-agent question from Chapter 3. In the SSE stream
you should see an extra event early on:

```
event: task.started
data: {"task_id":"call_xyz...","agent":"load_recipe","skill":"","input":{"name":"research-math-poem"}}

event: task.artifact
data: {"task_id":"call_xyz...","content":"<recipe_content name=\"research-math-poem\">\n# Recipe: research-math-poem\n\nUse this when the user's question has three distinct phases: ...</recipe_content>"}

event: task.finished
data: {"task_id":"call_xyz...","state":"completed"}
```

The planner recognized the match, called `load_recipe`, and now has your
playbook in context. The rest of the plan — research, math, poet —
follows the recipe.

### Does it actually change behavior?

Sometimes yes, sometimes no. The planner was already good at this class
of question; the recipe mostly pins the behavior (forces the specific
tool order, specific call shapes) rather than enabling something new.

Where recipes shine:

- **Edge-case handling.** A recipe that says "if you see `state:
  payment-required`, surface the payment URL to the user and STOP — do
  not retry" is a policy the planner wouldn't invent on its own. See the
  seed recipe at
  [gateway/recipes/payment-required-flow/RECIPE.md](../gateway/recipes/payment-required-flow/RECIPE.md)
  for a real example.
- **Tenant-specific rules.** A recipe visible only to a certain agent
  can encode rules like "always include a disclaimer" or "always call
  the compliance agent first."
- **Multi-hop orchestration with state.** A recipe describing a 5-step
  workflow is a document your team can review, version, and reason about.
  Inline planner reasoning isn't.

### Recipe layouts

Two supported shapes:

```
gateway/recipes/foo.md                    flat — no bundled files
gateway/recipes/bar/RECIPE.md             bundled — siblings like
gateway/recipes/bar/scripts/run.sh        scripts/, reference/ are
gateway/recipes/bar/reference/notes.md    surfaced to the planner
```

When the planner loads a bundled recipe, the `load_recipe` tool result
includes a `<recipe_files>` listing of the sibling files (capped at 10
for token sanity). The planner can refer to them by relative path in its
response or follow instructions in the body like "run
`scripts/validate.sh` before responding."

### Frontmatter reference

```yaml
---
name: unique-identifier          # required; cannot start with "call_"
description: one-line summary    # required (non-empty) — this is the hook
tags: [tag1, tag2]               # optional; surfaced in verbose listings
triggers: [phrase, phrase]       # optional; planner hints (not enforced)
---
```

Two rules the loader enforces:

1. **Unique `name`.** Duplicate recipe names cause boot to fail with a
   clear error — silent precedence would make behavior depend on
   filesystem order.
2. **No `call_` prefix.** Planner tool ids look like `call_agent_skill`;
   a recipe named `call_anything` would visually collide in the
   `load_recipe` tool description. Rejected at load time.

### Per-agent recipe visibility

The gateway's agent configs (in `gateway/agents/*.md`) have a
`permission:` block. You can use it to scope recipes:

```yaml
permission:
  recipe:
    "internal-*": "deny"      # this agent can't load recipes matching "internal-*"
    "*": "allow"              # everything else is fine
```

The planner only sees (and can only load) recipes matching its allowed
patterns. Default is `allow` — agents with no `recipe:` rules see
everything.

### The full recipe authoring loop

1. Create `gateway/recipes/<name>.md` or
   `gateway/recipes/<name>/RECIPE.md`.
2. Restart the gateway. The loader scans on boot (no hot reload yet).
3. Fire a `/plan` request that should trigger the recipe.
4. Read the SSE stream for a `load_recipe` tool call.
5. If the planner *didn't* load the recipe when you expected, tighten
   the `description` — that's what the planner reads. Add specific
   keywords the user question likely contains.

Recipes are the single highest-leverage operator tool in the gateway.
Spend an afternoon writing five for your common question shapes and
you'll notice your planner's behavior firming up across the board.

---

## Chapter 5 — Giving it an identity (DID signing)

Everything so far has been running on `localhost`. The agents accept
unsigned requests because `"auth": { "type": "none" }` tells the gateway
not to sign them. That's fine for development — there's no attacker
between you and your own laptop.

In production it isn't. If your gateway calls an agent over the public
internet, **anyone who can reach that agent's URL can pretend to be your
gateway**. They can feed it garbage, steal its output, or (if the agent
does anything side-effectful like sending email or moving money) cause
real damage.

The fix is: the gateway gets a cryptographic identity and signs every
outbound request. Agents verify the signature before processing. If an
attacker tries to forge a request, the signature won't match the
gateway's registered public key, and the agent rejects the call.

### What's a DID?

**DID** stands for *Decentralized Identifier*. It's a string that looks
like `did:bindu:alice_at_example_com:gateway:abc123` and uniquely
identifies an agent or a gateway. Paired with it is an **Ed25519 key
pair** — a private key (secret, 32 bytes, lives in an env var) and a
public key (safe to share, published at a `.well-known` URL).

You sign outbound requests with the private key. Recipients verify with
the public key. Standard public-key cryptography — what puts the green
lock in your browser.

### The three env vars

Generate a private key seed (once, keep it secret):

```bash
python3 -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())'
```

Add to `gateway/.env.local`:

```bash
BINDU_GATEWAY_DID_SEED=<paste the output>
BINDU_GATEWAY_AUTHOR=you@example.com
BINDU_GATEWAY_NAME=gateway
```

That's enough for the gateway to have an identity. It won't be *useful*
yet — we also need to tell the gateway where to publish its public key
so agents can fetch it. That's the next piece.

### Hydra — the registration server

[Ory Hydra](https://www.ory.sh/hydra/) is an open-source OAuth 2.0 / OIDC
server. The Bindu team runs one at `hydra-admin.getbindu.com` that any
Bindu gateway or agent can register with. You register once at boot; the
registry stores your DID + public key; agents that want to talk to you
fetch your public key by DID and verify your signatures with it.

Two more env vars:

```bash
BINDU_GATEWAY_HYDRA_ADMIN_URL=https://hydra-admin.getbindu.com
BINDU_GATEWAY_HYDRA_TOKEN_URL=https://hydra.getbindu.com/oauth2/token
```

Restart `npm run dev`. You'll now see:

```
[bindu-gateway] DID identity loaded: did:bindu:you_at_example_com:gateway:<uuid>
[bindu-gateway] public key (base58): 6MkjQ2r...
[bindu-gateway] registering with Hydra at https://hydra-admin.getbindu.com...
[bindu-gateway] Hydra registration confirmed for did:bindu:...
[bindu-gateway] publishing DID document at /.well-known/did.json
[bindu-gateway] listening on http://0.0.0.0:3774
```

Three things just happened:

1. The gateway derived a DID and public key from your seed.
2. It POSTed to Hydra's admin API to register as an OAuth client, with
   its DID as the `client_id` and its public key in the metadata. This
   is idempotent — safe to restart as many times as you like.
3. It exchanged its client credentials for an OAuth access token. That
   token is now cached in memory and refreshed 30 seconds before
   expiry.

The gateway also published its own DID document at
`http://localhost:3774/.well-known/did.json`. Curl it:

```bash
curl http://localhost:3774/.well-known/did.json
```

```json
{
  "@context": ["https://www.w3.org/ns/did/v1", "https://getbindu.com/ns/v1"],
  "id": "did:bindu:you_at_example_com:gateway:abc123",
  "authentication": [
    {
      "id": "did:bindu:you_at_example_com:gateway:abc123#key-1",
      "type": "Ed25519VerificationKey2020",
      "controller": "did:bindu:you_at_example_com:gateway:abc123",
      "publicKeyBase58": "6MkjQ2r..."
    }
  ]
}
```

That's your gateway's public key, served over HTTP, signed by no one but
vouching for itself. Any agent that receives a signed request claiming to
be from your DID can fetch this document, extract the public key, and
verify the signature.

### Flipping a peer to signed mode

Change the `/plan` request:

```json
"auth": { "type": "did_signed" }
```

(No `token` or `envVar` — the gateway will use its own Hydra token
automatically.)

Re-fire. On the wire, three things change:

- **The request body is signed.** The gateway computes a canonical JSON
  representation of the body, signs it with its Ed25519 private key, and
  attaches the signature as a header (`X-Bindu-Signature`) along with
  the DID in another header (`X-Bindu-DID`).
- **An OAuth access token is attached** as `Authorization: Bearer <token>`.
  The agent will introspect this token against Hydra to confirm it's
  real and unexpired.
- **The gateway records the signing result** on the task in Supabase, so
  you have an audit trail: "at time T, gateway signed body hash H to
  reach agent DID D."

On the receiving side, the agent:

- Fetches the gateway's `/.well-known/did.json` (or caches the DID→key
  mapping from a previous interaction).
- Verifies the signature matches the body with the gateway's public key.
- Introspects the bearer token against Hydra.
- Only then processes the request.

If *any* of those three checks fail — signature mismatch, unknown DID,
invalid token — the agent returns HTTP 401 and the gateway surfaces
that as `event: task.finished` with `state: failed` and a useful error
message.

### Two modes: auto vs manual

What I described is **auto mode** — one Hydra, shared by the gateway and
its peers, handles all the registration and token exchange.

There's also **manual mode** for federated setups where different peers
trust different Hydra instances:

- Set only the DID env vars (`SEED`, `AUTHOR`, `NAME`), not the Hydra
  URLs.
- For each peer, pre-register your gateway's DID with *that peer's*
  Hydra (out of band) and obtain an access token.
- Store the tokens in env vars per peer.
- In `/plan`, use `"auth": {"type": "did_signed", "tokenEnvVar":
  "PEER_A_TOKEN"}` to tell the gateway which env var to read for each
  peer.

Auto mode is the default because it's less moving parts. Use manual mode
when a peer insists on their own Hydra.

### Chapter takeaway

For local development: keep `auth.type: "none"`. For anything running
across a network you don't fully control: configure the DID identity and
flip peers to `did_signed`. The token and signature are automatic once
the env vars are set; you don't touch cryptography code.

If something in this chapter isn't working, the most common cause is a
missing env var — the gateway logs exactly which one on boot when a
partial config is detected.

---

## Chapter 6 — What's next

You've seen the gateway end-to-end. What to read, what to try, what to
skip.

### Reference material

- **[gateway/openapi.yaml](../gateway/openapi.yaml)** — the machine-readable
  contract for `/plan`, `/health`, and `/.well-known/did.json`. Paste it
  into [Swagger UI](https://editor.swagger.io) or
  [Stoplight](https://stoplight.io) to click through every field,
  response, and example. This is the source of truth; this document is
  the prose.
- **[gateway/README.md](../gateway/README.md)** — the operator's reference:
  configuration knobs, environment variables, the `/health` payload,
  troubleshooting, and where vendored code came from (OpenCode). Short
  and targeted — most of the narrative moved into this story.
- **[gateway/agents/planner.md](../gateway/agents/planner.md)** — the planner
  LLM's system prompt. If the gateway is doing something you don't
  expect, start here.
- **[gateway/recipes/](../gateway/recipes)** — the two seed recipes
  (`multi-agent-research`, `payment-required-flow`) plus whatever you
  authored in Chapter 4. Each one is a complete example.

### Hands-on next steps

- **Run the full matrix.** The `gateway_test_fleet` example has 13
  prebuilt test cases covering edge behaviors (empty question, wrong
  bearer token on a peer, timeout, ambiguous question, nonexistent
  skill). Run them all:
  ```bash
  ./examples/gateway_test_fleet/run_matrix.sh
  ```
  Each produces a full SSE log in
  `examples/gateway_test_fleet/logs/<case>.sse` — open one and read it
  end to end, it's unusually readable once you know the event types.
- **Write a second recipe.** The one from Chapter 4 was generic. Try a
  tenant-specific policy: "always prepend a compliance disclaimer to
  the final message," or "for any question about PII, refuse and point
  at the legal agent."
- **Add a new agent.** Copy `examples/joke_agent.py`, change the
  instructions, run it on port 3779, add it to a `/plan` request. Watch
  the planner pick it up without any gateway-side config change.
- **Edit the planner's system prompt.** Open
  `gateway/agents/planner.md` and tighten or loosen its instructions.
  Changes take effect on the next plan — no restart needed.

### Going to production

If you're moving this past localhost:

1. **Turn on DID signing** (Chapter 5) for every peer.
2. **Rotate `GATEWAY_API_KEY`** from the dev value to a generated
   secret. Distribute via your usual secret-management tool, not
   `.env.local`.
3. **Pin the planner model.** Add `model:
   openrouter/anthropic/claude-sonnet-4.6` (or whichever you want,
   e.g. `orcarouter/anthropic/claude-opus-4.7`) to
   `gateway/agents/planner.md` frontmatter so upgrades are explicit.
4. **Set `max_steps`** on your `/plan` requests so a runaway planner
   can't loop 100 times at your expense.
5. **Watch the `usage` field** on the `final` SSE event — that's where
   you see token counts per plan. Log them.

### When you're stuck

- Gateway won't boot: re-read the env var section of
  [gateway/README.md](../gateway/README.md). Partial DID or Hydra config fails
  fast with a message naming the missing var.
- Planner never calls a tool: the descriptions you gave for
  `agents[].skills[].description` are probably too short or too vague.
  Anthropic's docs say tool descriptions are "by far the most important
  factor in tool performance" — 3-4 sentences on intent, inputs,
  outputs, and when to use it.
- Agent returns "User not found": your `OPENROUTER_API_KEY` (or
  `ORCAROUTER_API_KEY`, whichever gateway you configured) is invalid
  or out of credit.
- `event: error` with "Invalid Responses API request": you're on an
  older gateway commit. `git pull`.

---

**That's the whole story.** You have a gateway, five agents, the ability
to add more, the ability to teach patterns via recipes, and the ability
to sign outbound calls for production. Everything else in this repo is
either reference material for one of those five concepts, or internal
implementation detail you don't need to read until you're ready to
extend the gateway itself.

Go build something.
