import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { type ChildProcess, spawn } from "node:child_process";
import crypto from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { resolve as pathResolve } from "node:path";
import {
	type AgentRecord,
	type EventRow,
	type PersonalAgentRow,
	type PersonalAgentTools,
	type SettingsField,
	type SettingsRow,
	archiveThread,
	clearSetting,
	deleteAgent,
	listConversationHistory,
	listEcosystem,
	listRecentEvents,
	listThreadState,
	markThreadRead,
	markThreadUnread,
	readAgent,
	readEvent,
	readPersonalAgent,
	readPriorSummary,
	readSettings,
	readPeerTrust,
	getVerificationHistory,
	recordVerificationEvent,
	writePeerTrust,
	recordEvent,
	resolveTaskContinuation,
	unarchiveThread,
	writeAgent,
	writePersonalAgent,
	writeSettings,
} from "./db";
import { assessInboundTrust } from "./trust";
import { spawnPersonalAgent, stopPersonalAgent } from "./personal-agent";
// `dispatcherFetch` MUST be used whenever an undici dispatcher is passed —
// Node's bundled undici (6.x) global fetch and our pinned undici@8 dispatcher
// don't interop. See utils.ts.
import {
	buildPeerDispatcher,
	dispatcherFetch,
	insecureLoopbackDispatcher,
	isLoopbackHttpsUrl,
	pickFreePort,
	pickPeerDispatcher,
	pollHealth,
} from "./utils";

// Path A: comms is the canonical record, gateway is stateless. We send
// the most recent N user/assistant turns on every /api/plan call;
// anything older lives in the compaction summary the gateway emits and
// we persist as a `plan-summary` event. Override via env if you need to
// stress-test longer histories.
const MAX_HISTORY_TURNS = Number(
	process.env.BINDU_COMMS_MAX_HISTORY ?? "30",
);

// agentId → base URL for callbacks. Two sources, env wins over DB:
//
//   1. Rows in the `agents` table (anything the operator added via the
//      Contacts + button, or that comms previously resolved). Survives
//      restart.
//   2. `BINDU_AGENT_URLS` env var — comma-separated `id=url` pairs for
//      ops overrides:
//        BINDU_AGENT_URLS="joke_agent=http://10.0.0.5:5773,my-agent=http://x:9000"
//
// We used to hardcode a `AGENT_URL_DEFAULTS` map for the dev fleet, but
// that went stale every time a port moved (and silently misrouted
// callbacks when an old port mapping outlived the agent on it). Drop it:
// operators register agents the same way in dev and prod — by URL,
// once. First-touch agents that fire webhooks before being registered
// are recorded with no URL until the operator adds one through the UI.
function loadAgentUrls(): Record<string, string> {
	const out: Record<string, string> = {};
	for (const a of listEcosystem()) {
		if (a.url) out[a.id] = a.url;
	}
	const raw = process.env.BINDU_AGENT_URLS;
	if (raw) {
		for (const pair of raw.split(",")) {
			const eq = pair.indexOf("=");
			if (eq <= 0) continue;
			const id = pair.slice(0, eq).trim();
			const url = pair.slice(eq + 1).trim();
			if (id && url) out[id] = url;
		}
	}
	return out;
}

const AGENT_URLS = loadAgentUrls();

const subscribers = new Set<(e: EventRow) => void>();

// Optional dev-time bearer token gate. When BINDU_COMMS_TOKEN is set, /api/*
// requires Authorization: Bearer <token> (or ?token=<token> for SSE, since
// browser EventSource can't set headers).
const REQUIRED_TOKEN = process.env.BINDU_COMMS_TOKEN ?? "";

// Optional webhook auth. When BINDU_WEBHOOK_TOKEN is set, agents must
// include `Authorization: Bearer <token>` on every webhook POST — which is
// what the Bindu agent does when global_webhook_token is configured (see
// bindu/utils/notifications.py:_build_headers). Mismatched / missing →
// 401. When unset, webhooks stay open (current dev behavior).
const WEBHOOK_TOKEN = process.env.BINDU_WEBHOOK_TOKEN ?? "";

/** Resolve the bearer token comms uses to call the gateway's /plan.
 *
 * The gateway gates /plan with `auth.mode = "bearer"` and reads its
 * accepted token from `GATEWAY_API_KEY` (see gateway/src/config/loader.ts
 * and gateway/.env.example). Without a matching header on the upstream
 * call, the gateway returns `{"error":"unauthorized"}` and the plan
 * trace dies with no agents called.
 *
 * Resolution order:
 *   1. comms's own GATEWAY_API_KEY env var — explicit override.
 *   2. Read gateway/.env.local (or .env) and grep for the key — same
 *      directory comms already locates for spawning the gateway. Lets
 *      operators avoid duplicating the secret across two .env files.
 *
 * Returns "" when the token can't be found; the upstream call then
 * goes out without an Authorization header (preserves the prior
 * behavior when the gateway runs with `auth.mode = "none"`). */
function loadGatewayApiKey(): string {
	if (process.env.GATEWAY_API_KEY) return process.env.GATEWAY_API_KEY;
	const gatewayDir = process.env.BINDU_GATEWAY_DIR
		? pathResolve(process.env.BINDU_GATEWAY_DIR)
		: pathResolve(process.cwd(), "..", "gateway");
	for (const fname of [".env.local", ".env"]) {
		const fpath = `${gatewayDir}/${fname}`;
		if (!existsSync(fpath)) continue;
		try {
			const txt = readFileSync(fpath, "utf-8");
			const m = txt.match(/^\s*GATEWAY_API_KEY\s*=\s*(.+)$/m);
			if (m) return m[1].trim().replace(/^["']|["']$/g, "");
		} catch {
			/* unreadable — keep looking */
		}
	}
	return "";
}
const GATEWAY_API_KEY = loadGatewayApiKey();
if (GATEWAY_API_KEY) {
	console.log(
		`[inbox] gateway bearer token loaded (${GATEWAY_API_KEY.length} chars)`,
	);
} else {
	console.warn(
		"[inbox] GATEWAY_API_KEY not set — /api/plan will fail with 401 if the gateway has auth.mode=bearer",
	);
}

// Webhook agentId comes off the URL path, so we constrain the shape to
// rule out traversal-style inputs and pathological lengths.
const AGENT_ID_RE = /^[a-zA-Z0-9_-]{1,64}$/;


async function fetchWellKnown(base: string) {
	// Discovery hits the peer's HTTPS endpoint when the peer is
	// mTLS-enabled. Present our personal-agent cert if we have one
	// (peers may require client cert); otherwise fall back to the
	// insecure-loopback dispatcher for spawned 127.0.0.1 children
	// (their cert SAN is a DID, not the hostname); plain global
	// fetch for HTTP peers and HTTPS peers with publicly-trusted
	// certs.
	//
	// Route through dispatcherFetch whenever a dispatcher is in
	// play — Node 22's bundled undici 6.x global fetch can't accept
	// our pinned undici 8.x dispatcher and throws an opaque
	// "fetch failed".
	const peerCertDispatcher = buildPeerDispatcher();
	const dispatcher =
		peerCertDispatcher ??
		(isLoopbackHttpsUrl(base) ? insecureLoopbackDispatcher : undefined);

	const get = (path: string) =>
		(dispatcher
			? dispatcherFetch(`${base}${path}`, { dispatcher })
			: fetch(`${base}${path}`)
		).then((r) => (r.ok ? r.json() : null));

	const [didR, cardR] = await Promise.all([
		get("/.well-known/did.json"),
		get("/.well-known/agent.json"),
	]);
	return { did: didR as unknown, agentCard: cardR as unknown };
}

/** Pull the DID string for a given agentId, normalising between the two
 *  shapes the inbox stores DIDs in:
 *    - `me` (personal agent): a flat string in personal_agent.did
 *    - everyone else: a parsed DID document object in agents.did with `.id`
 *  Used by pickPeerDispatcher() callers to enable Option C identity
 *  pinning when the DID is known, with insecure-loopback fallback during
 *  the cold-start window when it isn't. Returns null when no DID is on
 *  record (typical for HTTP peers, ecosystem agents the inbox hasn't
 *  resolved yet, etc.). */
function resolveExpectedDid(
	agentId: string,
	row?: AgentRecord | null,
): string | null {
	if (agentId === "me") return readPersonalAgent()?.did ?? null;
	const did = (row?.did as { id?: string } | null)?.id;
	return typeof did === "string" ? did : null;
}

async function resolveAgent(
	agentId: string,
	cached?: AgentRecord | null,
): Promise<AgentRecord> {
	// Callers that already have the DB row (e.g. the webhook handler that
	// just read it to decide whether to write) can hand it in so we don't
	// redo the SELECT.
	const row = cached === undefined ? readAgent(agentId) : cached;
	if (row?.did && row?.agentCard) return row;
	const base = row?.url ?? AGENT_URLS[agentId];
	const rec: AgentRecord = row ?? { id: agentId, url: base, source: "webhook" };
	if (!base) {
		writeAgent(rec);
		return rec;
	}
	try {
		const { did, agentCard } = await fetchWellKnown(base);
		rec.did = did;
		rec.agentCard = agentCard;
		rec.url = base;
		rec.resolvedAt = new Date().toISOString();
	} catch (err) {
		console.warn(`[resolve] ${agentId} failed:`, (err as Error).message);
	}
	writeAgent(rec);
	return rec;
}

function slugify(s: string): string {
	// Preserve underscores — agno agents commonly use snake_case names
	// like `joke_agent`, `bindu_docs_agent`. Their lifecycle webhooks
	// arrive at `/webhooks/bindu/joke_agent` verbatim, so if we collapse
	// underscores to hyphens here we end up with two Contacts rows for
	// the same agent (one with URL from manual add, one without from
	// the webhook auto-create). Mirrors `src/lib/format.ts:slugify`.
	const cleaned = s
		.toLowerCase()
		.replace(/[^a-z0-9_]+/g, "-")
		.replace(/(^-|-$)/g, "");
	return cleaned || `agent-${Math.random().toString(36).slice(2, 6)}`;
}

const app = new Hono();

// Operator-side auth. Every /api/* route used to do this inline; the
// middleware below collapses that into one rule. Token comes from the
// BINDU_COMMS_TOKEN env var — when unset the inbox is open (single-user
// dev default). Webhooks have their own auth (WEBHOOK_TOKEN) on the
// /webhooks/* path and are not covered by this middleware.
app.use("/api/*", async (c, next) => {
	if (!REQUIRED_TOKEN) return next();
	const header = c.req.header("authorization") ?? "";
	const query = c.req.query("token") ?? "";
	if (header === `Bearer ${REQUIRED_TOKEN}` || query === REQUIRED_TOKEN) {
		return next();
	}
	return c.json({ error: "unauthorized" }, 401);
});

app.post("/webhooks/bindu/:agentId", async (c) => {
	if (WEBHOOK_TOKEN) {
		const header = c.req.header("authorization") ?? "";
		if (header !== `Bearer ${WEBHOOK_TOKEN}`) {
			return c.json({ error: "unauthorized" }, 401);
		}
	}
	const agentId = c.req.param("agentId");
	if (!AGENT_ID_RE.test(agentId)) {
		return c.json({ error: "invalid-agent-id" }, 400);
	}
	const payload = (await c.req.json()) as Record<string, unknown>;
	const id = String(payload.event_id ?? crypto.randomUUID());
	const receivedAt = new Date().toISOString();
	const firstContact = recordEvent(id, agentId, receivedAt, payload);
	assessInboundTrust(agentId, payload, new Date(receivedAt));
	const ev: EventRow = { id, agentId, receivedAt, payload, firstContact };
	for (const cb of subscribers) cb(ev);
	console.log(
		`[webhook] ${agentId} ${payload.kind ?? "?"} ${payload.task_id ?? ""}${firstContact ? " (first-contact)" : ""}`,
	);
	const seen = readAgent(agentId);
	if (!seen) {
		writeAgent({
			id: agentId,
			url: AGENT_URLS[agentId],
			source: "webhook",
			addedAt: new Date().toISOString(),
		});
	}
	if (!seen?.agentCard) {
		// Hand `seen` through so resolveAgent skips a redundant SELECT.
		resolveAgent(agentId, seen).catch(() => {});
	}
	return c.json({ ok: true });
});

app.get("/api/events/stream", (c) => {
	const agentFilter = c.req.query("agentId");
	const stream = new ReadableStream({
		start(controller) {
			const enc = new TextEncoder();
			const send = (e: EventRow) => {
				if (agentFilter && e.agentId !== agentFilter) return;
				controller.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
			};
			for (const e of listRecentEvents(50)) send(e);
			subscribers.add(send);
			c.req.raw.signal.addEventListener("abort", () => {
				subscribers.delete(send);
				controller.close();
			});
		},
	});
	return new Response(stream, {
		headers: {
			"content-type": "text/event-stream",
			"cache-control": "no-cache",
			connection: "keep-alive",
		},
	});
});

app.get("/api/agents/:agentId", async (c) => {
	const rec = await resolveAgent(c.req.param("agentId"));
	return c.json(rec);
});

app.get("/api/peers/:peerId/trust", (c) => {
	const peerId = c.req.param("peerId");
	if (!AGENT_ID_RE.test(peerId)) return c.json({ error: "invalid-peer-id" }, 400);
	return c.json(readPeerTrust(peerId));
});
app.get("/api/peers/:peerId/verification-history", (c) => {
	const peerId = c.req.param("peerId");
	if (!AGENT_ID_RE.test(peerId)) return c.json({ error: "invalid-peer-id" }, 400);
	return c.json(getVerificationHistory(peerId));
});
app.post("/api/peers/:peerId/block", (c) => {
	const peerId = c.req.param("peerId");
	if (!AGENT_ID_RE.test(peerId)) return c.json({ error: "invalid-peer-id" }, 400);
	const at = new Date().toISOString();
	writePeerTrust(peerId, "blocked", at);
	recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "peer_blocked", result: "accepted", occurredAt: at });
	return c.json(readPeerTrust(peerId));
});
app.post("/api/peers/:peerId/unblock", (c) => {
	const peerId = c.req.param("peerId");
	if (!AGENT_ID_RE.test(peerId)) return c.json({ error: "invalid-peer-id" }, 400);
	const at = new Date().toISOString();
	writePeerTrust(peerId, "unknown", at);
	recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "peer_unblocked", result: "accepted", occurredAt: at });
	return c.json(readPeerTrust(peerId));
});

/**
 * Live agent inspector. Hits four Bindu endpoints in parallel and
 * returns a combined snapshot:
 *   - /.well-known/agent.json   (agent card)
 *   - /.well-known/did.json     (DID document)
 *   - /agent/skills             (skill summaries, docs.getbindu.com)
 *   - /health                   (liveness + readiness)
 *
 * Proxied (rather than fetched from the browser) so the operator UI
 * doesn't run into per-endpoint CORS surprises — many agents only
 * configure cors_origins on the A2A JSON-RPC root. `allSettled` keeps
 * partial failures from blanking the panel: each section reports its
 * own ok/error so the modal can render what it has.
 */
app.get("/api/agents/:agentId/live", async (c) => {
	const id = c.req.param("agentId");
	if (!AGENT_ID_RE.test(id)) return c.json({ error: "invalid-agent-id" }, 400);
	const row = readAgent(id);
	const base = (row?.url ?? AGENT_URLS[id])?.replace(/\/+$/, "");
	if (!base) {
		return c.json({ error: "no-url-for-agent", id }, 404);
	}

	// pickPeerDispatcher handles three cases: DID-pinned for known-DID
	// loopback children, insecure-loopback fallback during the cold-start
	// window, and undefined (default fetch with system CA roots) for
	// external peers. See utils.ts for the matrix.
	const expectedDid = resolveExpectedDid(id, row);
	const dispatcher = pickPeerDispatcher(base, expectedDid);

	const fetchJson = async (path: string) => {
		// When the personal agent serves HTTPS (mTLS on), `dispatcher` is the
		// DID-pinned loopback agent; global `fetch` (Node-bundled undici 6.x)
		// can't accept our pinned undici 8.x dispatcher and throws an opaque
		// "fetch failed". Route through dispatcherFetch (undici.fetch) when
		// we have one; fall back to global fetch on plain HTTP for external
		// peers that don't need a dispatcher.
		const r = dispatcher
			? await dispatcherFetch(`${base}${path}`, { dispatcher })
			: await fetch(`${base}${path}`);
		if (!r.ok) throw new Error(`${path} → HTTP ${r.status}`);
		return r.json();
	};
	const [card, did, skills, health] = await Promise.allSettled([
		fetchJson("/.well-known/agent.json"),
		fetchJson("/.well-known/did.json"),
		fetchJson("/agent/skills"),
		fetchJson("/health"),
	]);
	const settle = (r: PromiseSettledResult<unknown>) =>
		r.status === "fulfilled"
			? { ok: true as const, data: r.value }
			: { ok: false as const, error: (r.reason as Error).message };
	return c.json({
		id,
		url: base,
		agentCard: settle(card),
		didDocument: settle(did),
		skills: settle(skills),
		health: settle(health),
	});
});

// Ecosystem — every known agent (webhook-seen + manually added). The Gmail-
// shaped inbox uses this list as the "Contacts / Senders" surface. POST
// here to add a third-party agent by URL; the server fetches its well-known
// docs and stores a slugified record.
app.get("/api/ecosystem", (c) => {
	return c.json(listEcosystem());
});

app.delete("/api/ecosystem/:agentId", (c) => {
	const id = c.req.param("agentId");
	if (!AGENT_ID_RE.test(id)) return c.json({ error: "invalid-agent-id" }, 400);
	const removed = deleteAgent(id);
	return c.json({ ok: true, removed });
});

app.post("/api/ecosystem", async (c) => {
	const body = (await c.req.json().catch(() => ({}))) as {
		url?: string;
		id?: string;
	};
	const url = (body.url ?? "").replace(/\/+$/, "");
	if (!/^https?:\/\//.test(url)) {
		return c.json({ error: "invalid-url" }, 400);
	}
	let did: unknown = null;
	let agentCard: unknown = null;
	try {
		const r = await fetchWellKnown(url);
		did = r.did;
		agentCard = r.agentCard;
	} catch (err) {
		return c.json({ error: "fetch-failed", detail: (err as Error).message }, 502);
	}
	const cardObj = (agentCard ?? {}) as Record<string, unknown>;
	const name =
		typeof cardObj.name === "string" && cardObj.name.length > 0
			? (cardObj.name as string)
			: typeof cardObj.id === "string"
				? (cardObj.id as string)
				: "agent";
	const id = body.id && AGENT_ID_RE.test(body.id) ? body.id : slugify(name);
	if (!AGENT_ID_RE.test(id)) {
		return c.json({ error: "could-not-derive-id" }, 400);
	}
	const now = new Date().toISOString();
	const rec: AgentRecord = {
		id,
		url,
		did,
		agentCard,
		resolvedAt: now,
		source: "manual",
		addedAt: now,
	};
	writeAgent(rec);
	if (!(id in AGENT_URLS)) AGENT_URLS[id] = url;
	return c.json(rec, 201);
});

// Thread state — operator-side triage flags (read / unread / archived)
// keyed by context_id. Source of truth lives in SQLite; the frontend's
// localStorage caches are gone in favor of this.
app.get("/api/threads/state", (c) => {
	return c.json(listThreadState());
});

app.post("/api/threads/:contextId/:action", async (c) => {
	const contextId = c.req.param("contextId");
	const action = c.req.param("action");
	if (!contextId) return c.json({ error: "missing-context" }, 400);
	switch (action) {
		case "read":
			markThreadRead(contextId);
			break;
		case "unread":
			markThreadUnread(contextId);
			break;
		case "archive":
			archiveThread(contextId);
			break;
		case "unarchive":
			unarchiveThread(contextId);
			break;
		default:
			return c.json({ error: "unknown-action" }, 400);
	}
	return c.json({ ok: true });
});

// Step 2: compose. Operator sends an outbound `message/send` to a known
// agent. We record it locally under agentId="outbox" so the new thread
// shows up immediately in the inbox UI (the recipient's lifecycle
// webhooks, if it's configured to push back to us, will arrive later
// against its own agentId, so they appear as a separate thread on that
// agent's lane — that's a known dev-surface duality we'll fix when we
// teach comms to correlate outbound→inbound by context_id across agents).
const OUTBOX_AGENT_ID = "outbox";
const OPERATOR_DID =
	process.env.BINDU_COMMS_OPERATOR_DID ?? "did:bindu:operator:local";

// ─── outbound A2A auth ───────────────────────────────────────────────
// Peer agents run with AUTH__ENABLED=true and reject unauthenticated
// JSON-RPC with -32009. They introspect tokens against the shared Hydra
// at HYDRA__PUBLIC_URL, so any valid bearer token minted via
// client_credentials is accepted.
//
// We reuse the personal agent's OAuth client (registered during
// onboarding at ~/.bindu/personal/.bindu/oauth_credentials.json). The
// token is cached in memory and refreshed `TOKEN_LEEWAY_MS` before
// expiry. If creds are missing (personal agent never set up) we send
// without an Authorization header — the peer will reject and the
// existing -32009 surfaces in the UI as before, which is the right
// failure mode for that configuration.

const HYDRA_PUBLIC_URL =
	process.env.HYDRA__PUBLIC_URL ?? "https://hydra.getbindu.com";
const OAUTH_CREDS_PATH = pathResolve(
	`${process.env.BINDU_PERSONAL_DIR ?? `${process.env.HOME ?? "."}/.bindu/personal`}/.bindu/oauth_credentials.json`,
);
const TOKEN_LEEWAY_MS = 60_000;

type OAuthClientRecord = {
	client_id: string;
	client_secret: string;
	scopes?: string[];
};
let cachedToken: { token: string; expiresAt: number } | null = null;
let inflightTokenFetch: Promise<string | null> | null = null;

function readOAuthCreds(): OAuthClientRecord | null {
	try {
		if (!existsSync(OAUTH_CREDS_PATH)) return null;
		const map = JSON.parse(readFileSync(OAUTH_CREDS_PATH, "utf-8")) as Record<
			string,
			OAuthClientRecord
		>;
		const first = Object.values(map)[0];
		return first?.client_id && first.client_secret ? first : null;
	} catch {
		return null;
	}
}

async function mintHydraToken(): Promise<string | null> {
	const now = Date.now();
	if (cachedToken && cachedToken.expiresAt > now + TOKEN_LEEWAY_MS) {
		return cachedToken.token;
	}
	if (inflightTokenFetch) return inflightTokenFetch;

	inflightTokenFetch = (async () => {
		try {
			const creds = readOAuthCreds();
			if (!creds) return null;
			// Drop openid/offline — those are user-flow scopes; service-to-
			// service introspection only needs the agent:* scopes.
			const scope = (creds.scopes ?? ["agent:read", "agent:write"])
				.filter((s) => s !== "openid" && s !== "offline")
				.join(" ");
			const body = new URLSearchParams({
				grant_type: "client_credentials",
				client_id: creds.client_id,
				client_secret: creds.client_secret,
				...(scope ? { scope } : {}),
			});
			const r = await fetch(`${HYDRA_PUBLIC_URL}/oauth2/token`, {
				method: "POST",
				headers: { "content-type": "application/x-www-form-urlencoded" },
				body: body.toString(),
			});
			if (!r.ok) {
				console.warn(
					`[inbox] hydra token mint failed: ${r.status}`,
				);
				return null;
			}
			const j = (await r.json()) as {
				access_token?: string;
				expires_in?: number;
			};
			if (!j.access_token) return null;
			const ttlMs = (j.expires_in ?? 300) * 1000;
			cachedToken = {
				token: j.access_token,
				expiresAt: Date.now() + ttlMs,
			};
			return j.access_token;
		} catch (err) {
			console.warn(
				`[inbox] hydra token mint error: ${(err as Error).message}`,
			);
			return null;
		} finally {
			inflightTokenFetch = null;
		}
	})();
	return inflightTokenFetch;
}

// ─── DID signature ────────────────────────────────────────────────────
// The agent's auth middleware enforces a second layer once the JWT's
// `client_id` starts with `did:`: every request must carry X-DID,
// X-DID-Signature, X-DID-Timestamp, with the signature being a base58
// Ed25519 sign over
//     json.dumps({"body": <bytes-on-wire>, "did": <did>, "timestamp": <ts>},
//                sort_keys=True)  # ensure_ascii=True, ', ' / ': ' seps
// using the private key whose public key the agent registered in its
// Hydra client metadata. We reuse the personal agent's keypair (the same
// identity whose OAuth client we just minted a token for) so X-DID
// always matches the JWT `sub`, which the agent verifies.

const PRIVATE_KEY_PATH = pathResolve(
	`${process.env.BINDU_PERSONAL_DIR ?? `${process.env.HOME ?? "."}/.bindu/personal`}/.bindu/private.pem`,
);
let cachedPrivateKey: crypto.KeyObject | null | undefined = undefined;

function loadPrivateKey(): crypto.KeyObject | null {
	if (cachedPrivateKey !== undefined) return cachedPrivateKey;
	try {
		if (!existsSync(PRIVATE_KEY_PATH)) {
			cachedPrivateKey = null;
			return null;
		}
		cachedPrivateKey = crypto.createPrivateKey(
			readFileSync(PRIVATE_KEY_PATH, "utf-8"),
		);
		return cachedPrivateKey;
	} catch {
		cachedPrivateKey = null;
		return null;
	}
}

const BASE58_ALPHABET =
	"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"; // pragma: allowlist secret

function base58Encode(bytes: Buffer): string {
	let n = 0n;
	for (const b of bytes) n = (n << 8n) | BigInt(b);
	let out = "";
	while (n > 0n) {
		out = BASE58_ALPHABET[Number(n % 58n)] + out;
		n /= 58n;
	}
	for (const b of bytes) {
		if (b === 0) out = "1" + out;
		else break;
	}
	return out || "1";
}

// Python-compatible JSON string escape (ensure_ascii=True). Embeds all
// non-ASCII as \uXXXX so the signer/verifier byte-for-byte agree even
// when message text contains non-Latin characters.
function pyJsonString(s: string): string {
	const escaped = JSON.stringify(s).replace(
		/[-￿]/g,
		(c) => `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`,
	);
	return escaped;
}

function buildSignaturePayload(
	body: string,
	did: string,
	timestamp: number,
): string {
	// json.dumps default: separators=(', ', ': '), sort_keys=True. Keys are
	// alphabetical: body, did, timestamp.
	return `{"body": ${pyJsonString(body)}, "did": ${pyJsonString(did)}, "timestamp": ${timestamp}}`;
}

function signA2ARequest(
	body: string,
	did: string,
): Record<string, string> | null {
	const key = loadPrivateKey();
	if (!key) return null;
	const timestamp = Math.floor(Date.now() / 1000);
	const payload = buildSignaturePayload(body, did, timestamp);
	const signature = crypto.sign(null, Buffer.from(payload, "utf-8"), key);
	return {
		"x-did": did,
		"x-did-signature": base58Encode(signature),
		"x-did-timestamp": String(timestamp),
	};
}

async function a2aHeaders(body: string): Promise<Record<string, string>> {
	const headers: Record<string, string> = {
		"content-type": "application/json",
	};
	const token = await mintHydraToken();
	if (!token) return headers;
	headers.authorization = `Bearer ${token}`;
	// X-DID must equal the JWT's client_id (verifier rejects on mismatch),
	// so derive it from the same creds file we minted the token from.
	const creds = readOAuthCreds();
	if (creds) {
		const sig = signA2ARequest(body, creds.client_id);
		if (sig) Object.assign(headers, sig);
	}
	return headers;
}

/** Pick the DID to stamp on outbound messages.
 *
 * When the operator has a personal agent that's `alive`, use its DID so
 * peers receive traffic attributed to the operator's real bindufied
 * identity (the one that serves /.well-known/agent.json and signs
 * artifacts). When the agent is down, fall back to OPERATOR_DID — the
 * inbox still works as an observer, just without a verifiable sender.
 *
 * Returns both the DID and a short reason so the route layer can echo
 * back what was used (handy for the compose UI's "Sending from …" hint
 * and for debugging "why does this peer see did:bindu:operator:local").
 *
 * Note: this stamps the DID in metadata only — true end-to-end signing
 * would route the message THROUGH the personal agent (Phase 6 work).
 * For now peers see the correct attribution and can resolve the DID
 * via the agent card to verify subsequent signed artifacts. */
function effectiveFromDid(): { did: string; reason: "agent" | "fallback" } {
	const me = readPersonalAgent();
	if (me?.status === "alive" && me.did) {
		return { did: me.did, reason: "agent" };
	}
	return { did: OPERATOR_DID, reason: "fallback" };
}

app.post("/api/compose", async (c) => {
	const body = (await c.req.json().catch(() => ({}))) as {
		agentId?: string;
		text?: string;
		contextId?: string;
	};
	const targetId = (body.agentId ?? "").trim();
	const text = (body.text ?? "").trim();
	if (!targetId || !AGENT_ID_RE.test(targetId)) {
		return c.json({ error: "invalid-agent-id" }, 400);
	}
	if (!text) {
		return c.json({ error: "empty-text" }, 400);
	}
	const target = readAgent(targetId);
	const base = target?.url ?? AGENT_URLS[targetId];
	if (!base) {
		return c.json({ error: "unknown-agent", detail: targetId }, 404);
	}

	const contextId = body.contextId ?? crypto.randomUUID();
	const messageId = crypto.randomUUID();

	// Decide whether this reply resumes an open task, refines a
	// terminal one (with referenceTaskIds), or starts fresh — per the
	// A2A task lifecycle docs. Without this every reply minted a new
	// task, so input-required pauses never actually resumed and the
	// agent had no signal that a follow-up was a refinement.
	const continuation = body.contextId
		? resolveTaskContinuation(body.contextId)
		: { kind: "fresh" as const };
	const taskId =
		continuation.kind === "resume"
			? continuation.taskId
			: crypto.randomUUID();
	const referenceTaskIds =
		continuation.kind === "refine" ? continuation.referenceTaskIds : undefined;

	// Stamp the real DID when the personal agent is alive; fall back to
	// OPERATOR_DID otherwise. The peer's task storage will record this
	// as the sender, so the inbox on the other side shows "from
	// <persona name>" instead of an anonymous operator placeholder.
	const sender = effectiveFromDid();
	const messageParams: Record<string, unknown> = {
		role: "user",
		kind: "message",
		parts: [{ kind: "text", text }],
		messageId,
		contextId,
		taskId,
		metadata: { from_did: sender.did },
	};
	if (referenceTaskIds && referenceTaskIds.length > 0) {
		messageParams.referenceTaskIds = referenceTaskIds;
	}
	const rpc = {
		jsonrpc: "2.0",
		id: crypto.randomUUID(),
		method: "message/send",
		params: {
			message: messageParams,
			configuration: { acceptedOutputModes: ["application/json"] },
		},
	};

	// Capture timestamp + persist the outbox event BEFORE the upstream
	// fetch. Bindu emits lifecycle webhooks during task processing
	// (often before its own HTTP 200 reaches us), and those carry the
	// agent's clock. If we waited until after the fetch to stamp our
	// outbox event, the webhook payload.timestamp could legitimately
	// be earlier — and thread-grouping would mis-attribute origin to
	// the peer, landing the conversation in Inbox instead of Sent.
	// `upstream_status`/`upstream_error` are patched in after the fetch
	// via a second recordEvent call with the same id (INSERT OR REPLACE).
	const now = new Date().toISOString();
	const eventId = crypto.randomUUID();
	const outboundEvent: Record<string, unknown> = {
		event_id: eventId,
		timestamp: now,
		kind: "outbound",
		direction: "out",
		from_did: sender.did,
		from_did_reason: sender.reason,
		to_agent_id: targetId,
		to_did: target?.did
			? (target.did as { id?: string }).id ?? null
			: null,
		context_id: contextId,
		task_id: taskId,
		message_id: messageId,
		text,
		// `continuation` lets the inbox (and any future audit) tell
		// resume-vs-refine-vs-fresh apart without re-walking history.
		// `reference_task_ids` is stored snake_case so the info-icon
		// strip in the UI picks it up via the same payloadJson path
		// the agent webhooks use.
		continuation: continuation.kind,
		...(referenceTaskIds && referenceTaskIds.length > 0
			? { reference_task_ids: referenceTaskIds }
			: {}),
		upstream_status: 0,
		upstream_error: null,
	};
	// First DB write — placeholder upstream values. This pins our
	// payload.timestamp BEFORE the fetch, which is what thread-grouping
	// uses to attribute "operator-initiated" vs "other-initiated". The
	// SSE broadcast for this event happens after the fetch (below) with
	// the final upstream status, so SSE consumers see exactly one row.
	recordEvent(eventId, OUTBOX_AGENT_ID, now, outboundEvent);

	let upstreamStatus = 0;
	let upstreamBody: unknown = null;
	let upstreamError: string | null = null;
	try {
		const rpcBody = JSON.stringify(rpc);
		const peerDispatcher = buildPeerDispatcher();
		// Dispatcher path goes through undici's fetch (must match the
		// Agent's undici version); the no-dispatcher branch keeps global
		// fetch so we don't shadow it for the whole file.
		const r = peerDispatcher
			? await dispatcherFetch(base, {
					method: "POST",
					headers: await a2aHeaders(rpcBody),
					body: rpcBody,
					dispatcher: peerDispatcher,
				})
			: await fetch(base, {
					method: "POST",
					headers: await a2aHeaders(rpcBody),
					body: rpcBody,
				});
		upstreamStatus = r.status;
		upstreamBody = await r.json().catch(() => null);
	} catch (err) {
		upstreamError = (err as Error).message;
	}

	// Patch the outbox row with the final upstream result. Same id +
	// `INSERT OR REPLACE` semantics in `recordEvent` overwrite the
	// earlier placeholder. Timestamp stays at `now` (pre-fetch) so
	// ordering is unchanged.
	outboundEvent.upstream_status = upstreamStatus;
	outboundEvent.upstream_error = upstreamError;
	recordEvent(eventId, OUTBOX_AGENT_ID, now, outboundEvent);
	for (const cb of subscribers) {
		cb({
			id: eventId,
			agentId: OUTBOX_AGENT_ID,
			receivedAt: now,
			payload: outboundEvent,
			firstContact: true,
		});
	}
	if (!readAgent(OUTBOX_AGENT_ID)) {
		writeAgent({
			id: OUTBOX_AGENT_ID,
			source: "webhook",
			addedAt: now,
		});
	}

	if (upstreamError) {
		return c.json(
			{ ok: false, error: "send-failed", detail: upstreamError, contextId, taskId },
			502,
		);
	}
	return c.json({
		ok: upstreamStatus >= 200 && upstreamStatus < 300,
		status: upstreamStatus,
		contextId,
		taskId,
		response: upstreamBody,
	});
});

/**
 * Spawn a gateway from the local monorepo as a child process.
 *
 * Used when the operator picks 2+ agents in Compose and has no
 * gateway in Contacts yet — instead of asking them to `cd gateway &&
 * npm start` in another terminal, comms launches it directly.
 *
 * Flow:
 *   1. Locate `gateway/` (env override BINDU_GATEWAY_DIR, else
 *      `../gateway` relative to the comms cwd).
 *   2. Verify `.env.local` or `.env` exists — the gateway needs
 *      OPENROUTER_API_KEY + Supabase creds at minimum.
 *   3. Pick a free port via OS-assignment (bind to :0, read back).
 *   4. Spawn `npm start` (not `dev` — we don't want tsx --watch
 *      restart loops on file edits). Override `GATEWAY_PORT` so the
 *      gateway lands on our chosen port.
 *   5. Poll the child's /health endpoint until it returns 200 or 30s
 *      elapse; kill on timeout.
 *   6. Register the new gateway in the ecosystem table with
 *      source=manual + a stable spawned id, hand the child reference
 *      to a Map so we can clean up on comms exit.
 *
 * The spawned process is bound to the comms server lifetime — when
 * comms exits, SIGTERM cascades. We intentionally don't try to
 * persist these across restarts; that's a phase-3 concern.
 */
interface SpawnedGateway {
	child: ChildProcess;
	/** True iff this gateway was started with BINDU_GATEWAY_TLS_* in its
	 * env (Phase C). False means it serves plain HTTP and presents no
	 * client cert on outbound A2A. We track this so that when the personal
	 * agent comes up AFTER a gateway was already spawned, recycleStaleGateways
	 * can SIGTERM the HTTP one so the next /api/plan respawns it with TLS. */
	hasTls: boolean;
}
const spawnedGateways = new Map<string, SpawnedGateway>();

type GatewayHandle =
	| {
			ok: true;
			id: string;
			url: string;
			reused: boolean;
			spawned: boolean;
			warnings: string[];
	  }
	| { ok: false; error: string; detail: string };

/** Hydra-admin reachability probe.
 *
 * Hydra's `/health/alive` returns 200 quickly when the service is up.
 * If it's unreachable, the gateway's boot will hang on
 * `ensureHydraClient` and eventually die with a TLS or fetch error —
 * we'd rather catch that here, in 3 seconds, and let the gateway
 * boot in degraded mode (no Hydra → no `did_signed` peers) than
 * make the operator wait for a 30-second spawn timeout to find out.
 *
 * We treat 401/404 as "Hydra is up, just not happy with our probe" —
 * still reachable, so the gateway's own registration attempt with
 * proper credentials might succeed. Only network-level failures
 * (ECONNREFUSED, TLS errors, timeout) count as unreachable. */
async function isHydraReachable(adminUrl: string): Promise<boolean> {
	try {
		const r = await fetch(`${adminUrl.replace(/\/+$/, "")}/health/alive`, {
			signal: AbortSignal.timeout(3000),
		});
		// Any HTTP response (200, 401, 404, 500) means we got through the
		// TLS handshake and TCP socket — Hydra is *reachable* even if it
		// doesn't like our probe. Network failures throw instead.
		return r.status > 0;
	} catch {
		return false;
	}
}

/** Look in Contacts for a live gateway. Returns null if either no
 * row matches the gateway heuristic or its /health doesn't respond
 * inside `healthTimeoutMs`. The caller decides whether to spawn. */
async function findLiveGateway(
	healthTimeoutMs = 1500,
): Promise<{ id: string; url: string } | null> {
	const eco = listEcosystem();
	for (const a of eco) {
		if (!a.url) continue;
		const id = a.id.toLowerCase();
		const name = (
			(a.agentCard as { name?: string } | null)?.name ?? ""
		).toLowerCase();
		if (!/gateway/.test(id) && !/gateway/.test(name)) continue;
		const alive = await pollHealth(a.url, healthTimeoutMs);
		if (alive) return { id: a.id, url: a.url };
	}
	return null;
}

/** Spawn the gateway from the monorepo and register it. Pure helper
 * — no Hono context. Returns a discriminated result so callers can
 * surface the stderr tail when boot fails. */
async function spawnGatewayProcess(): Promise<GatewayHandle> {
	const gatewayDir = process.env.BINDU_GATEWAY_DIR
		? pathResolve(process.env.BINDU_GATEWAY_DIR)
		: pathResolve(process.cwd(), "..", "gateway");
	if (!existsSync(`${gatewayDir}/package.json`)) {
		return {
			ok: false,
			error: "gateway-not-found",
			detail: `No package.json at ${gatewayDir}. Set BINDU_GATEWAY_DIR.`,
		};
	}
	if (
		!existsSync(`${gatewayDir}/.env.local`) &&
		!existsSync(`${gatewayDir}/.env`)
	) {
		return {
			ok: false,
			error: "gateway-no-env",
			detail: `${gatewayDir} needs .env.local with OPENROUTER_API_KEY + Supabase creds.`,
		};
	}

	// Idempotency: reuse an alive spawned gateway if we have one.
	// Misclick-protection; also makes a second /api/plan call within a
	// session land on the same process so session continuity holds.
	for (const [id, entry] of spawnedGateways.entries()) {
		const row = readAgent(id);
		if (row?.url && entry.child.exitCode === null) {
			const alive = await pollHealth(row.url, 1000);
			if (alive) {
				return {
					ok: true,
					id,
					url: row.url,
					reused: true,
					spawned: false,
					warnings: [],
				};
			}
		}
	}

	// Hydra pre-flight. The gateway's `setupHydraIntegration` blocks
	// boot if Hydra is configured-but-unreachable (throws → process
	// exits → spawn fails). When the operator's `.env.local` points at
	// a Hydra they can't currently reach (different network, service
	// down, expired cert) we'd rather start the gateway in degraded
	// mode than block them. The probe is a 3-second budget.
	const warnings: string[] = [];
	const hydraAdmin = process.env.BINDU_GATEWAY_HYDRA_ADMIN_URL;
	const hydraOverride: Record<string, string> = {};
	if (hydraAdmin) {
		const reachable = await isHydraReachable(hydraAdmin);
		if (!reachable) {
			// Blank both URLs in the child env. The gateway's
			// setupHydraIntegration treats "neither set" as "Hydra not
			// configured" and skips registration entirely.
			hydraOverride.BINDU_GATEWAY_HYDRA_ADMIN_URL = "";
			hydraOverride.BINDU_GATEWAY_HYDRA_TOKEN_URL = "";
			warnings.push("hydra-unreachable");
		}
	}

	let port: number;
	try {
		port = await pickFreePort();
	} catch (err) {
		return {
			ok: false,
			error: "no-free-port",
			detail: (err as Error).message,
		};
	}

	// Phase C: if the personal agent has bootstrapped a cert from
	// step-ca, pass its paths into the gateway env so the gateway can
	// serve over TLS and present the cert on outbound A2A. The
	// gateway shares the personal agent's identity ("co-opt"
	// model) — same DID, same cert, simpler rotation. Phase C2 will
	// give the gateway its own identity.
	//
	// Soft fallback: no cert files → plain HTTP gateway (today's
	// behavior). The inbox handles both via insecureLoopbackDispatcher
	// for loopback calls regardless of scheme.
	const personalPkiDir =
		process.env.BINDU_PERSONAL_PKI_DIR ??
		`${process.env.HOME}/.bindu/personal/.bindu`;
	const personalCert = `${personalPkiDir}/tls_cert.pem`;
	const personalKey = `${personalPkiDir}/tls_key.pem`;
	const personalCa = `${personalPkiDir}/ca_bundle.pem`;
	const haveCert =
		existsSync(personalCert) &&
		existsSync(personalKey) &&
		existsSync(personalCa);
	const scheme = haveCert ? "https" : "http";
	const tlsEnv: Record<string, string> = haveCert
		? {
				BINDU_GATEWAY_TLS_CERT: personalCert,
				BINDU_GATEWAY_TLS_KEY: personalKey,
				BINDU_GATEWAY_TLS_CA: personalCa,
			}
		: {};

	const baseUrl = `${scheme}://127.0.0.1:${port}`;
	const id = `gateway-spawned-${port}`;
	const child = spawn("npm", ["start"], {
		cwd: gatewayDir,
		env: {
			...process.env,
			GATEWAY_PORT: String(port),
			NODE_NO_WARNINGS: "1",
			// Honored by tsx --env-file-if-exists: already-set env wins
			// over file values, so passing empty strings here suppresses
			// the .env.local Hydra URLs (only when our pre-flight said
			// Hydra was unreachable). When Hydra is healthy, this object
			// is empty and the gateway uses whatever's in .env.local.
			...hydraOverride,
			...tlsEnv,
		},
		stdio: ["ignore", "pipe", "pipe"],
		detached: false,
	});

	let lastStderr = "";
	child.stderr?.on("data", (b: Buffer) => {
		const chunk = b.toString();
		const filtered = chunk
			.split("\n")
			.filter((l) => !/not found\. Continuing without it/.test(l))
			.join("\n");
		lastStderr += filtered;
		if (lastStderr.length > 8000) lastStderr = lastStderr.slice(-4000);
	});

	const exited = new Promise<number>((res) => {
		child.once("exit", (code) => res(code ?? -1));
	});
	const ready = await Promise.race([
		pollHealth(baseUrl, 30_000),
		exited.then(() => false),
	]);

	if (!ready) {
		if (child.exitCode === null) child.kill("SIGTERM");
		return {
			ok: false,
			error: "gateway-boot-failed",
			detail: lastStderr.slice(-1000) || "timeout waiting for /health",
		};
	}

	const addedAt = new Date().toISOString();
	writeAgent({ id, url: baseUrl, source: "manual", addedAt });
	resolveAgent(id).catch(() => {});

	spawnedGateways.set(id, { child, hasTls: haveCert });
	child.once("exit", () => {
		spawnedGateways.delete(id);
		// Drop the row from Contacts too — otherwise the sidebar keeps
		// showing a dead "Gateways" entry until the operator removes it
		// by hand. The ecosystem poll picks this up within 5s.
		try {
			deleteAgent(id);
		} catch {
			/* DB closed during shutdown — nothing to clean up */
		}
	});

	return { ok: true, id, url: baseUrl, reused: false, spawned: true, warnings };
}

/** "I need a gateway right now" — checks Contacts first, spawns if
 * nothing's alive. Single-call coalescing via `inFlightSpawn` so two
 * concurrent /api/plan requests don't kick off two gateway processes
 * on a cold start. */
let inFlightSpawn: Promise<GatewayHandle> | null = null;
async function ensureGateway(): Promise<GatewayHandle> {
	const existing = await findLiveGateway();
	if (existing) {
		return {
			ok: true,
			id: existing.id,
			url: existing.url,
			reused: true,
			spawned: false,
			warnings: [],
		};
	}
	if (!inFlightSpawn) {
		inFlightSpawn = spawnGatewayProcess().finally(() => {
			inFlightSpawn = null;
		});
	}
	return inFlightSpawn;
}

// Best-effort cleanup: SIGTERM all spawned gateways when comms exits.
// Without this, child processes outlive their parent and the operator
// has to `pkill -f 'gateway/src/index.ts'` to clean up.
const cleanupSpawned = () => {
	for (const { child } of spawnedGateways.values()) {
		if (child.exitCode === null) {
			try {
				child.kill("SIGTERM");
			} catch {
				/* already exiting — ignore */
			}
		}
	}
	// Same treatment for the personal agent. Calling stopPersonalAgent
	// is safe even if nothing's running.
	stopPersonalAgent();
};

/** SIGTERM any spawned gateway that was started before the personal
 *  agent had a cert on disk. These gateways serve plain HTTP and
 *  present no client cert outbound — once the personal agent is up
 *  with mTLS the next /api/plan would route to a stale HTTP gateway,
 *  silently losing Phase C end-to-end. We kill them so the next
 *  spawnGatewayProcess re-evaluates `haveCert` and boots over TLS.
 *
 *  Safe to call repeatedly: gateways already on TLS are left alone,
 *  and a freshly-killed gateway's `exit` listener cleans up the map
 *  + the Contacts row. */
function recycleStaleGateways(): number {
	let killed = 0;
	for (const { child, hasTls } of spawnedGateways.values()) {
		if (hasTls) continue;
		if (child.exitCode !== null) continue;
		try {
			child.kill("SIGTERM");
			killed += 1;
		} catch {
			/* already exiting — ignore */
		}
	}
	return killed;
}
process.once("SIGINT", () => {
	cleanupSpawned();
	process.exit(0);
});
process.once("SIGTERM", () => {
	cleanupSpawned();
	process.exit(0);
});

/**
 * Multi-agent compose. Streams SSE from byte zero so the browser can
 * show "what we're doing right now" while we:
 *
 *   1. Validate the request.
 *   2. Ensure a gateway is alive — find an existing one in Contacts
 *      or spawn one from the monorepo if needed. The operator never
 *      sees a separate "spawn first" step; it just happens.
 *   3. Build the planner catalog (cached card name + live
 *      /agent/skills per peer).
 *   4. POST the question to the gateway's /plan endpoint.
 *   5. Pipe the upstream SSE through, tapping text.delta so we can
 *      persist the planner's final answer on `done`.
 *
 * Status frames emitted before the upstream stream starts:
 *   event: status   data: { phase: "preparing"        }
 *   event: status   data: { phase: "spawning-gateway" }   ← only if we spawn
 *   event: status   data: { phase: "building-catalog" }
 *   event: status   data: { phase: "planning"         }
 *
 * After "planning" we forward upstream bytes verbatim — the gateway's
 * own event stream (session, plan, task.started, task.artifact,
 * task.finished, text.delta, final, done) takes over. We still emit
 * `event: error` + `event: done` ourselves if anything goes wrong
 * before "planning" lands. */
app.post("/api/plan", async (c) => {
	const body = (await c.req.json().catch(() => ({}))) as {
		question?: string;
		agentIds?: string[];
		sessionId?: string;
	};
	const question = (body.question ?? "").trim();
	const agentIds = Array.isArray(body.agentIds)
		? (body.agentIds.filter((id) => typeof id === "string") as string[])
		: [];
	if (!question) return c.json({ error: "empty-question" }, 400);
	if (agentIds.length < 2) {
		return c.json(
			{
				error: "need-multi-agent",
				detail: "Use /api/compose for single-agent sends.",
			},
			400,
		);
	}

	const contextId = body.sessionId ?? crypto.randomUUID();
	const encoder = new TextEncoder();

	const stream = new ReadableStream<Uint8Array>({
		async start(controller) {
			const frame = (event: string, data: unknown) => {
				controller.enqueue(
					encoder.encode(
						`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`,
					),
				);
			};
			const fatal = (message: string, error = "plan-failed") => {
				frame("error", { error, message });
				frame("done", {});
				controller.close();
			};

			try {
				frame("status", { phase: "preparing" });

				// --- ensure gateway -----------------------------------
				const existing = await findLiveGateway();
				let gateway: { id: string; url: string };
				if (existing) {
					gateway = existing;
				} else {
					frame("status", { phase: "spawning-gateway" });
					const spawnRes = await ensureGateway();
					if (!spawnRes.ok) {
						fatal(spawnRes.detail, spawnRes.error);
						return;
					}
					gateway = { id: spawnRes.id, url: spawnRes.url };
					frame("status", {
						phase: "gateway-ready",
						gatewayId: spawnRes.id,
						spawned: spawnRes.spawned,
						warnings: spawnRes.warnings,
					});
				}
				const gatewayUrl = gateway.url.replace(/\/+$/, "");

				// --- build catalog ------------------------------------
				frame("status", { phase: "building-catalog" });
				type SkillDescriptor = {
					id: string;
					description: string;
					tags?: string[];
				};
				type CatalogAgent = {
					name: string;
					endpoint: string;
					// Peer agents enforce AUTH__ENABLED=true (Hydra JWT +
					// DID signature). Tell the gateway to use its own
					// DID-signed flow — it has BINDU_GATEWAY_DID_SEED and
					// auto-acquires a Hydra token (no tokenEnvVar needed).
					auth: { type: "did_signed" };
					skills: SkillDescriptor[];
				};
				const catalog: CatalogAgent[] = [];
				for (const id of agentIds) {
					const row = readAgent(id);
					if (!row?.url) continue;
					let skills: SkillDescriptor[] = [];
					// Same dispatcher selection as /api/agents/:id/live —
					// without it, fetching /agent/skills on an HTTPS loopback
					// agent (the personal agent under Phase A) fails TLS verify
					// and the skill catalog quietly empties. The planner's
					// "fewer than two callable agents" gate then trips.
					const skillsBase = row.url.replace(/\/+$/, "");
					const skillsDispatcher = pickPeerDispatcher(
						skillsBase,
						resolveExpectedDid(id, row),
					);
					try {
						const r = skillsDispatcher
							? await dispatcherFetch(`${skillsBase}/agent/skills`, {
									dispatcher: skillsDispatcher,
								})
							: await fetch(`${skillsBase}/agent/skills`);
						if (r.ok) {
							// Bindu's /agent/skills returns `{skills: [...], total: N}`
							// (wrapped object). Earlier code assumed a bare array and
							// silently dropped every skill — every plan request hit
							// "Fewer than two of the selected agents publish skills"
							// even when agents had skills declared. Accept both
							// shapes so a future agent that returns a bare array
							// keeps working too.
							const j = (await r.json()) as unknown;
							const arr: unknown[] = Array.isArray(j)
								? j
								: Array.isArray((j as { skills?: unknown })?.skills)
									? ((j as { skills: unknown[] }).skills)
									: [];
							skills = arr
								.filter(
									(s): s is Record<string, unknown> =>
										!!s && typeof s === "object" && typeof (s as Record<string, unknown>).id === "string",
								)
								.map((s) => ({
									id: s.id as string,
									description:
										typeof s.description === "string"
											? s.description
											: "",
									tags: Array.isArray(s.tags)
										? (s.tags as string[])
										: undefined,
								}));
						}
					} catch {
						/* leave empty */
					}
					const card = (row.agentCard ?? null) as { name?: unknown } | null;
					catalog.push({
						name: typeof card?.name === "string" ? card.name : id,
						endpoint: row.url,
						auth: { type: "did_signed" },
						skills,
					});
				}
				const reachableWithSkills = catalog.filter(
					(a) => a.skills.length > 0,
				);
				if (reachableWithSkills.length < 2) {
					fatal(
						"Fewer than two of the selected agents publish skills at /agent/skills.",
						"insufficient-callable-agents",
					);
					return;
				}

				// --- record outbox so the question persists -----------
				const planSender = effectiveFromDid();
				const now = new Date().toISOString();
				const questionEventId = crypto.randomUUID();
				const questionEvent: Record<string, unknown> = {
					event_id: questionEventId,
					timestamp: now,
					kind: "plan-question",
					direction: "out",
					from_did: planSender.did,
					from_did_reason: planSender.reason,
					context_id: contextId,
					text: question,
					plan_agents: agentIds,
					gateway: gateway.id,
				};
				recordEvent(questionEventId, OUTBOX_AGENT_ID, now, questionEvent);
				for (const cb of subscribers) {
					cb({
						id: questionEventId,
						agentId: OUTBOX_AGENT_ID,
						receivedAt: now,
						payload: questionEvent,
						firstContact: true,
					});
				}
				if (!readAgent(OUTBOX_AGENT_ID)) {
					writeAgent({
						id: OUTBOX_AGENT_ID,
						source: "webhook",
						addedAt: now,
					});
				}

				// --- upstream plan request ----------------------------
				// Path A wire format: we ship the gateway the full prior
				// history and the latest compaction summary so it can run
				// without its own session DB. Excluding the just-recorded
				// question from history — the gateway adds it itself from
				// `question` on the request, so including it here would
				// duplicate the user turn in the LLM prompt.
				frame("status", { phase: "planning" });
				const fullHistory = listConversationHistory(
					contextId,
					MAX_HISTORY_TURNS,
				).slice(0, -1); // drop the just-recorded `plan-question`
				const priorSummary = readPriorSummary(contextId);
				let upstream: Response;
				try {
					const planHeaders: Record<string, string> = {
						"Content-Type": "application/json",
					};
					if (GATEWAY_API_KEY) {
						planHeaders.Authorization = `Bearer ${GATEWAY_API_KEY}`;
					}
					// Spawned gateway may be HTTPS now (Phase C — see
					// spawnGatewayProcess). Its cert SAN is the DID, not
					// 127.0.0.1, so we route loopback calls through the
					// insecure dispatcher that skips hostname verify.
					upstream = await dispatcherFetch(`${gatewayUrl}/plan`, {
						method: "POST",
						headers: planHeaders,
						body: JSON.stringify({
							question,
							agents: catalog,
							session_id: contextId,
							history: fullHistory,
							prior_summary: priorSummary,
						}),
						dispatcher: insecureLoopbackDispatcher,
					});
				} catch (err) {
					fatal((err as Error).message, "gateway-unreachable");
					return;
				}
				if (!upstream.ok || !upstream.body) {
					const detail = await upstream.text().catch(() => "");
					fatal(
						detail || `HTTP ${upstream.status}`,
						"gateway-error",
					);
					return;
				}

				// --- pipe + tap relevant frames ----------------------
				// We forward every byte to the client untouched and also
				// keep our own ledger of what happened:
				//
				//   text.delta            → accumulate into finalText
				//                           (persisted as `plan-reply` on done)
				//   task.started/         → persist each as its own event so
				//   task.artifact/         the inbox can later show the trace
				//   task.finished           per thread without re-running the plan
				//
				//   compaction-summary    → persist as `plan-summary` so the
				//                           next /api/plan call's
				//                           `readPriorSummary(contextId)` picks
				//                           it up and sends it back to the
				//                           gateway as `prior_summary`. This
				//                           is the loop that keeps the
				//                           stateless gateway useful across
				//                           long sessions.
				const decoder = new TextDecoder();
				const reader = upstream.body.getReader();
				let buffer = "";
				let finalText = "";

				const persistTraceEvent = (
					kind:
						| "task-started"
						| "task-artifact"
						| "task-finished"
						| "plan-summary",
					data: Record<string, unknown>,
				) => {
					const id = crypto.randomUUID();
					const at = new Date().toISOString();
					const payload: Record<string, unknown> = {
						event_id: id,
						timestamp: at,
						kind,
						direction: "in",
						from_agent_id: gateway.id,
						context_id: contextId,
						...data,
					};
					recordEvent(id, gateway.id, at, payload);
					for (const cb of subscribers) {
						cb({
							id,
							agentId: gateway.id,
							receivedAt: at,
							payload,
							firstContact: false,
						});
					}
				};

				try {
					while (true) {
						const { done, value } = await reader.read();
						if (done) break;
						controller.enqueue(value);
						buffer += decoder.decode(value, { stream: true });
						let idx: number;
						while ((idx = buffer.indexOf("\n\n")) !== -1) {
							const sseFrame = buffer.slice(0, idx);
							buffer = buffer.slice(idx + 2);
							const evLine = sseFrame
								.split("\n")
								.find((l) => l.startsWith("event:"));
							const dataLine = sseFrame
								.split("\n")
								.find((l) => l.startsWith("data:"));
							if (!evLine || !dataLine) continue;
							const evType = evLine.slice("event:".length).trim();
							let parsed: Record<string, unknown> = {};
							try {
								parsed = JSON.parse(
									dataLine.slice("data:".length).trim(),
								) as Record<string, unknown>;
							} catch {
								continue;
							}

							if (evType === "text.delta") {
								if (typeof parsed.delta === "string") {
									finalText += parsed.delta;
								}
							} else if (evType === "task.started") {
								persistTraceEvent("task-started", {
									task_id: parsed.task_id ?? null,
									agent: parsed.agent ?? null,
									agent_did: parsed.agent_did ?? null,
									skill: parsed.skill ?? null,
									input: parsed.input ?? null,
								});
							} else if (evType === "task.artifact") {
								persistTraceEvent("task-artifact", {
									task_id: parsed.task_id ?? null,
									agent: parsed.agent ?? null,
									agent_did: parsed.agent_did ?? null,
									content: parsed.content ?? null,
									title: parsed.title ?? null,
									signatures: parsed.signatures ?? null,
								});
							} else if (evType === "task.finished") {
								persistTraceEvent("task-finished", {
									task_id: parsed.task_id ?? null,
									agent: parsed.agent ?? null,
									agent_did: parsed.agent_did ?? null,
									state: parsed.state ?? null,
									signatures: parsed.signatures ?? null,
									error: parsed.error ?? null,
								});
							} else if (evType === "compaction-summary") {
								// Stage 4: gateway emits this when it
								// summarises overflowed history. We record
								// it under `plan-summary` so the next call's
								// readPriorSummary() picks it up.
								if (typeof parsed.summary === "string") {
									persistTraceEvent("plan-summary", {
										text: parsed.summary,
										tokens_before: parsed.tokens_before ?? null,
										tokens_after: parsed.tokens_after ?? null,
									});
								}
							}
						}
					}
				} catch (err) {
					fatal(
						(err as Error).message,
						"plan-stream-broken",
					);
					return;
				}

				// --- persist final answer -----------------------------
				if (finalText.trim()) {
					const replyId = crypto.randomUUID();
					const replyAt = new Date().toISOString();
					const replyEvent: Record<string, unknown> = {
						event_id: replyId,
						timestamp: replyAt,
						kind: "plan-reply",
						direction: "in",
						from_agent_id: gateway.id,
						context_id: contextId,
						text: finalText,
					};
					recordEvent(replyId, gateway.id, replyAt, replyEvent);
					for (const cb of subscribers) {
						cb({
							id: replyId,
							agentId: gateway.id,
							receivedAt: replyAt,
							payload: replyEvent,
							firstContact: false,
						});
					}
				}
				controller.close();
			} catch (err) {
				fatal((err as Error).message);
			}
		},
	});

	return new Response(stream, {
		status: 200,
		headers: {
			"Content-Type": "text/event-stream",
			"Cache-Control": "no-cache",
			Connection: "keep-alive",
			"X-Plan-Context-Id": contextId,
		},
	});
});

// Phase 5: action callbacks. Looks up the source agent, sends a follow-up
// JSON-RPC message on the same context/task. Only `input` is meaningful end-
// to-end today; `approve`/`pay`/`decline` are recorded but not yet wired to
// the underlying protocol moves (we say so honestly in the response).
app.post("/api/events/:id/action", async (c) => {
	const evId = c.req.param("id");
	const ev = readEvent(evId);
	if (!ev) return c.json({ error: "event-not-found" }, 404);
	const body = (await c.req.json().catch(() => ({}))) as {
		kind?: "approve" | "decline" | "input" | "pay";
		text?: string;
	};
	const kind = body.kind ?? "approve";
	const base = AGENT_URLS[ev.agentId];
	const taskId = ev.payload.task_id as string | undefined;
	const contextId = ev.payload.context_id as string | undefined;
	console.log(`[action] ${kind} on ${evId} (agent=${ev.agentId} task=${taskId})`);

	if (kind === "input" && base && taskId && contextId) {
		const msg = {
			jsonrpc: "2.0",
			id: crypto.randomUUID(),
			method: "message/send",
			params: {
				message: {
					role: "user",
					kind: "message",
					parts: [{ kind: "text", text: body.text ?? "(continue)" }],
					messageId: crypto.randomUUID(),
					contextId,
					taskId,
				},
				configuration: { acceptedOutputModes: ["application/json"] },
			},
		};
		try {
			const msgBody = JSON.stringify(msg);
			const peerDispatcher = buildPeerDispatcher();
			const r = peerDispatcher
				? await dispatcherFetch(base, {
						method: "POST",
						headers: await a2aHeaders(msgBody),
						body: msgBody,
						dispatcher: peerDispatcher,
					})
				: await fetch(base, {
						method: "POST",
						headers: await a2aHeaders(msgBody),
						body: msgBody,
					});
			return c.json({ ok: r.ok, status: r.status, delivered: r.ok });
		} catch (err) {
			return c.json({ ok: false, error: (err as Error).message }, 502);
		}
	}
	return c.json({
		ok: true,
		kind,
		recorded: true,
		protocolMovePending: true,
	});
});

// ─── personal agent ────────────────────────────────────────────────────
// Phase 1: persistence + read/write. Spawn lifecycle (Phase 3) lands
// next; for now the spawn/stop endpoints just toggle status fields so
// the frontend wizard can build against the real API contract.

const PERSONAL_AGENT_DIR = pathResolve(
	process.env.BINDU_PERSONAL_DIR ??
		`${process.env.HOME ?? "."}/.bindu/personal`,
);

function isPersonaShape(p: unknown): p is Record<string, unknown> {
	if (!p || typeof p !== "object") return false;
	const obj = p as Record<string, unknown>;
	// Minimum viable persona: must have a name. Everything else is
	// optional so the wizard can save in-progress drafts.
	return typeof obj.name === "string" && obj.name.length > 0;
}

function isToolsShape(t: unknown): t is PersonalAgentTools {
	if (!t || typeof t !== "object") return false;
	const obj = t as PersonalAgentTools;
	const ok = (v: unknown) =>
		v === undefined ||
		(typeof v === "object" &&
			v !== null &&
			typeof (v as { accountId?: unknown }).accountId === "string");
	return ok(obj.gmail) && ok(obj.notion);
}

app.get("/api/me", (c) => {
	return c.json(readPersonalAgent());
});

app.post("/api/me", async (c) => {
	const body = (await c.req.json().catch(() => ({}))) as {
		persona?: unknown;
		tools?: unknown;
	};
	if (!isPersonaShape(body.persona)) {
		return c.json({ error: "invalid-persona", detail: "persona.name required" }, 400);
	}
	const tools = body.tools === undefined ? {} : body.tools;
	if (!isToolsShape(tools)) {
		return c.json({ error: "invalid-tools" }, 400);
	}
	const existing = readPersonalAgent();
	const now = new Date().toISOString();
	const row: PersonalAgentRow = {
		persona: body.persona,
		tools,
		agentDir: existing?.agentDir ?? PERSONAL_AGENT_DIR,
		// Preserve any spawn-time fields on a re-save (e.g. user edits
		// persona while the agent is running — we keep the DID + URL).
		did: existing?.did ?? null,
		url: existing?.url ?? null,
		pid: existing?.pid ?? null,
		status: existing?.status ?? "configuring",
		lastHealth: existing?.lastHealth ?? null,
		createdAt: existing?.createdAt ?? now,
		updatedAt: now,
	};
	writePersonalAgent(row);
	return c.json(row);
});

// Spawn / stop the personal agent. The heavy lifting lives in
// `personal-agent.ts`; the route just translates the result shape into
// HTTP. Spawning may take 30-60s (uv resolves deps, bindufy boots a
// uvicorn server, polls health) so the wizard's "Save" button shows a
// spinner during this call. We never stream progress — if the request
// is still pending after 60s, the agent's boot itself timed out and
// the response will carry the captured stderr.
app.post("/api/me/spawn", async (c) => {
	const row = readPersonalAgent();
	if (!row) return c.json({ error: "no-personal-agent" }, 404);
	const result = await spawnPersonalAgent();
	if (!result.ok) {
		return c.json({ error: result.error, detail: result.detail }, 500);
	}
	// Teach the AGENT_URLS map about ourselves so /api/compose can
	// route outbound through the personal agent (Phase 5).
	if (result.row.url) {
		AGENT_URLS["me"] = result.row.url;
		// Also sync the ecosystem `agents` row. Each spawn picks a fresh
		// free port, so the prior row's url goes stale immediately and
		// the inspector (`/api/agents/:id/live`, which reads from this
		// table) ends up fetching a dead port and surfacing "fetch
		// failed" across all four panels.
		writeAgent({
			id: "me",
			url: result.row.url,
			did: result.row.did ?? undefined,
			resolvedAt: new Date().toISOString(),
			source: "manual",
		});
	}
	// Phase C cold-start fix: if a gateway was already running on plain
	// HTTP (spawned before the personal agent had a cert), SIGTERM it so
	// the next /api/plan respawns it with BINDU_GATEWAY_TLS_* env. Without
	// this the gateway stays HTTP for its whole lifetime, silently
	// disabling Phase C even after the personal agent comes up healthy.
	const recycled = recycleStaleGateways();
	if (recycled > 0) {
		console.log(
			`[me/spawn] recycled ${recycled} HTTP gateway(s) so next plan respawns with TLS`,
		);
	}
	return c.json(result.row);
});

app.post("/api/me/stop", (c) => {
	const row = readPersonalAgent();
	if (!row) return c.json({ error: "no-personal-agent" }, 404);
	const result = stopPersonalAgent();
	return c.json(result);
});

// Pipedream Connect token endpoint. The frontend calls this, then
// passes the returned `token` to Pipedream's Connect SDK to open the
// OAuth popup. Project credentials live in comms env — never shipped
// to the browser.
//
// Pipedream's mint API expects an OAuth client-credentials exchange
// first (POST /v1/oauth/token with client_id/client_secret), then a
// project-scoped POST /v1/connect/{project_id}/tokens that returns
// the short-lived Connect token. We cache the OAuth access token in
// memory until ~60s before its expiry — Connect tokens themselves are
// per-popup and never cached.
let pdOAuth: { accessToken: string; expiresAt: number } | null = null;

async function pipedreamOAuthToken(
	clientId: string,
	clientSecret: string,
): Promise<string> {
	if (pdOAuth && Date.now() < pdOAuth.expiresAt - 60_000) {
		return pdOAuth.accessToken;
	}
	const r = await fetch("https://api.pipedream.com/v1/oauth/token", {
		method: "POST",
		headers: { "content-type": "application/json" },
		body: JSON.stringify({
			grant_type: "client_credentials",
			client_id: clientId,
			client_secret: clientSecret,
		}),
	});
	if (!r.ok) {
		throw new Error(`pipedream oauth ${r.status}: ${await r.text()}`);
	}
	const j = (await r.json()) as { access_token: string; expires_in: number };
	pdOAuth = {
		accessToken: j.access_token,
		expiresAt: Date.now() + j.expires_in * 1000,
	};
	return j.access_token;
}

app.post("/api/pipedream/connect-token", async (c) => {
	// Settings table wins; env vars are a fallback for the shell-env
	// workflow we shipped pre-Settings-tab.
	const s = readSettings();
	const projectId = s.pipedreamProjectId || process.env.PIPEDREAM_PROJECT_ID || "";
	const clientId = s.pipedreamClientId || process.env.PIPEDREAM_CLIENT_ID || "";
	const clientSecret =
		s.pipedreamClientSecret || process.env.PIPEDREAM_CLIENT_SECRET || "";
	if (!projectId || !clientId || !clientSecret) {
		return c.json(
			{
				error: "pipedream-not-configured",
				detail:
					"Set Pipedream Project ID, Client ID, and Client Secret in the Settings tab (gear icon, top of sidebar).",
			},
			501,
		);
	}
	const body = (await c.req.json().catch(() => ({}))) as {
		external_user_id?: string;
	};
	const externalUserId = body.external_user_id ?? "comms-operator";
	const environment =
		s.pipedreamEnvironment || process.env.PIPEDREAM_ENVIRONMENT || "development";
	let accessToken: string;
	try {
		accessToken = await pipedreamOAuthToken(clientId, clientSecret);
	} catch (err) {
		return c.json(
			{ error: "pipedream-oauth-failed", detail: (err as Error).message },
			502,
		);
	}
	try {
		// Pipedream's Connect mint requires `x-pd-environment` on the
		// request itself (NOT just in the body). Without it we get back
		// `400: Environment missing` even though the project has its own
		// environment configured server-side. Allowed values: `development`
		// or `production` — defaults match what the operator picked in
		// the Settings tab.
		const mint = await fetch(
			`https://api.pipedream.com/v1/connect/${encodeURIComponent(projectId)}/tokens`,
			{
				method: "POST",
				headers: {
					authorization: `Bearer ${accessToken}`,
					"content-type": "application/json",
					"x-pd-environment": environment,
				},
				body: JSON.stringify({
					external_user_id: externalUserId,
					allowed_origins: [
						"http://localhost:3775",
						"http://127.0.0.1:3775",
					],
				}),
			},
		);
		if (!mint.ok) {
			return c.json(
				{
					error: "pipedream-mint-failed",
					detail: `${mint.status}: ${(await mint.text()).slice(0, 400)}`,
				},
				502,
			);
		}
		const j = (await mint.json()) as Record<string, unknown>;
		return c.json(j);
	} catch (err) {
		return c.json(
			{ error: "pipedream-mint-error", detail: (err as Error).message },
			502,
		);
	}
});

// ─── settings ──────────────────────────────────────────────────────────
// Operator-supplied secrets that the personal agent + Pipedream-mint
// route consume. Single global row. Field shape mirrors `SettingsRow`
// from db.ts; the GET response masks each secret so we never re-leak
// what was stored.

/** Mask a secret for display. Keeps the first 6 chars (so the user can
 * recognise their own value: `sk-or-` vs `sk-` vs random) and the last
 * 4 (for a recency check against their password manager). Returns null
 * if the value is empty.  */
function maskSecret(v: string | null): string | null {
	if (!v) return null;
	if (v.length <= 12) return "•".repeat(v.length);
	return `${v.slice(0, 6)}…${v.slice(-4)}`;
}

interface MaskedSettings {
	openrouterApiKey: string | null;
	openrouterModel: string | null;
	pipedreamProjectId: string | null;
	pipedreamClientId: string | null;
	pipedreamClientSecret: string | null;
	pipedreamEnvironment: string | null;
	updatedAt: string;
	/** Convenience flags so the UI doesn't have to re-derive presence
	 * from the masked strings. */
	have: Record<SettingsField, boolean>;
}

function maskSettings(row: SettingsRow): MaskedSettings {
	return {
		// Project ID is publishable per Pipedream docs — show plain.
		openrouterApiKey: maskSecret(row.openrouterApiKey),
		openrouterModel: row.openrouterModel,
		pipedreamProjectId: row.pipedreamProjectId,
		pipedreamClientId: maskSecret(row.pipedreamClientId),
		pipedreamClientSecret: maskSecret(row.pipedreamClientSecret),
		pipedreamEnvironment: row.pipedreamEnvironment,
		updatedAt: row.updatedAt,
		have: {
			openrouterApiKey: !!row.openrouterApiKey,
			openrouterModel: !!row.openrouterModel,
			pipedreamProjectId: !!row.pipedreamProjectId,
			pipedreamClientId: !!row.pipedreamClientId,
			pipedreamClientSecret: !!row.pipedreamClientSecret,
			pipedreamEnvironment: !!row.pipedreamEnvironment,
		},
	};
}

const SETTINGS_FIELD_NAMES: SettingsField[] = [
	"openrouterApiKey",
	"openrouterModel",
	"pipedreamProjectId",
	"pipedreamClientId",
	"pipedreamClientSecret",
	"pipedreamEnvironment",
];

app.get("/api/settings", (c) => {
	return c.json(maskSettings(readSettings()));
});

app.post("/api/settings", async (c) => {
	const body = (await c.req.json().catch(() => ({}))) as Record<string, unknown>;
	const partial: Partial<Record<SettingsField, string>> = {};
	for (const field of SETTINGS_FIELD_NAMES) {
		const v = body[field];
		if (typeof v === "string" && v.trim().length > 0) {
			partial[field] = v.trim();
		}
	}
	if (Object.keys(partial).length === 0) {
		return c.json({ error: "no-fields-to-update" }, 400);
	}
	return c.json(maskSettings(writeSettings(partial)));
});

app.delete("/api/settings/:field", (c) => {
	const field = c.req.param("field") as SettingsField;
	if (!SETTINGS_FIELD_NAMES.includes(field)) {
		return c.json({ error: "unknown-field", detail: field }, 400);
	}
	return c.json(maskSettings(clearSetting(field)));
});

serve({ fetch: app.fetch, port: 3787 }, (info) => {
	console.log(`[inbox] api on http://127.0.0.1:${info.port}`);
	if (REQUIRED_TOKEN) {
		console.log(`[inbox] /api/* requires Bearer token`);
	}
	if (WEBHOOK_TOKEN) {
		console.log(`[inbox] webhooks require Bearer token`);
	}
});
