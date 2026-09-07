import Database from "better-sqlite3";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

const DB_PATH = process.env.BINDU_COMMS_DB ?? "data/events.db";
mkdirSync(dirname(DB_PATH), { recursive: true });

export const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");

db.exec(`
	CREATE TABLE IF NOT EXISTS events (
		id              TEXT PRIMARY KEY,
		agent_id        TEXT NOT NULL,
		received_at     TEXT NOT NULL,
		payload         TEXT NOT NULL,
		first_contact   INTEGER NOT NULL DEFAULT 0
	);
	CREATE INDEX IF NOT EXISTS events_agent_received
		ON events (agent_id, received_at DESC);

	CREATE TABLE IF NOT EXISTS agents (
		id           TEXT PRIMARY KEY,
		url          TEXT,
		did          TEXT,
		agent_card   TEXT,
		resolved_at  TEXT,
		source       TEXT NOT NULL DEFAULT 'webhook',
		added_at     TEXT
	);

	CREATE TABLE IF NOT EXISTS contexts (
		agent_id        TEXT NOT NULL,
		context_id      TEXT NOT NULL,
		first_seen_at   TEXT NOT NULL,
		PRIMARY KEY (agent_id, context_id)
	);

	CREATE TABLE IF NOT EXISTS thread_state (
		context_id      TEXT PRIMARY KEY,
		read_at         TEXT,
		unread_at       TEXT,
		archived_at     TEXT
	);

	-- Single-row config table — model + Pipedream credentials. The
	-- comms server hands these to the spawned personal agent at boot
	-- (writes them into ~/.bindu/personal/.env) and to /api/pipedream/*
	-- routes. Stored plaintext: single-user dev tool on the operator's
	-- laptop. The /api/settings GET response masks values before they
	-- ever leave the server.
	CREATE TABLE IF NOT EXISTS settings (
		id                       TEXT PRIMARY KEY DEFAULT 'global',
		openrouter_api_key       TEXT,
		openrouter_model         TEXT,
		pipedream_project_id     TEXT,
		pipedream_client_id      TEXT,
		pipedream_client_secret  TEXT,
		pipedream_environment    TEXT,
		updated_at               TEXT NOT NULL
	);

	-- Single-row table for the operator's personal agent. Key is always
	-- 'me'; we keep one row max. Persona is operator-supplied JSON
	-- stored verbatim as TEXT and parsed in helpers. DID is captured post-spawn
	-- from the bindufied agent's /.well-known/did.json. Pipedream account
	-- refs live in 'tools' JSON: { gmail?: { accountId }, notion?: { accountId } }.
	CREATE TABLE IF NOT EXISTS personal_agent (
		id           TEXT PRIMARY KEY DEFAULT 'me',
		persona      TEXT NOT NULL,
		tools        TEXT NOT NULL DEFAULT '{}',
		agent_dir    TEXT NOT NULL,
		did          TEXT,
		url          TEXT,
		pid          INTEGER,
		status       TEXT NOT NULL DEFAULT 'configuring',
		last_health  TEXT,
		created_at   TEXT NOT NULL,
		updated_at   TEXT NOT NULL
	);

	-- Trust state is intentionally separate from agent discovery. Discovering an
	-- agent card does not authenticate a peer; only an accepted signed message
	-- may move it to verified.
	CREATE TABLE IF NOT EXISTS peer_trust_state (
		peer_id TEXT PRIMARY KEY,
		status TEXT NOT NULL DEFAULT 'unknown',
		last_verified_at TEXT,
		last_contact_at TEXT,
		updated_at TEXT NOT NULL
	);
	CREATE TABLE IF NOT EXISTS verification_events (
		id TEXT PRIMARY KEY,
		peer_id TEXT NOT NULL,
		event_type TEXT NOT NULL,
		result TEXT NOT NULL,
		reason TEXT,
		message_id TEXT,
		context_id TEXT,
		occurred_at TEXT NOT NULL
	);
	CREATE INDEX IF NOT EXISTS verification_events_peer_time
		ON verification_events (peer_id, occurred_at DESC);
	CREATE TABLE IF NOT EXISTS replay_protection (
		message_id TEXT PRIMARY KEY,
		peer_id TEXT NOT NULL,
		seen_at TEXT NOT NULL
	);
	CREATE INDEX IF NOT EXISTS replay_protection_seen_at ON replay_protection (seen_at);
`);

export interface EventRow {
	id: string;
	agentId: string;
	receivedAt: string;
	payload: Record<string, unknown>;
	firstContact: boolean;
}

// Defensive: older DB files may predate first_contact. Add the column when
// missing so we don't crash on startup after the schema bump.
const eventColumns = db
	.prepare("PRAGMA table_info(events)")
	.all() as Array<{ name: string }>;
if (!eventColumns.some((c) => c.name === "first_contact")) {
	db.exec("ALTER TABLE events ADD COLUMN first_contact INTEGER NOT NULL DEFAULT 0");
}
const agentColumns = db
	.prepare("PRAGMA table_info(agents)")
	.all() as Array<{ name: string }>;
if (!agentColumns.some((c) => c.name === "source")) {
	db.exec("ALTER TABLE agents ADD COLUMN source TEXT NOT NULL DEFAULT 'webhook'");
}
if (!agentColumns.some((c) => c.name === "added_at")) {
	db.exec("ALTER TABLE agents ADD COLUMN added_at TEXT");
}

const insertEvent = db.prepare(
	"INSERT OR REPLACE INTO events (id, agent_id, received_at, payload, first_contact) VALUES (?, ?, ?, ?, ?)",
);
const trimEvents = db.prepare(
	`DELETE FROM events WHERE id IN (
		SELECT id FROM events ORDER BY received_at DESC LIMIT -1 OFFSET ?
	)`,
);
const recentEvents = db.prepare(
	"SELECT id, agent_id AS agentId, received_at AS receivedAt, payload, first_contact AS firstContact FROM events ORDER BY received_at ASC LIMIT ?",
);
const getEventById = db.prepare(
	"SELECT id, agent_id AS agentId, received_at AS receivedAt, payload, first_contact AS firstContact FROM events WHERE id = ?",
);
const upsertContext = db.prepare(
	"INSERT OR IGNORE INTO contexts (agent_id, context_id, first_seen_at) VALUES (?, ?, ?)",
);
const getAgent = db.prepare(
	"SELECT id, url, did, agent_card AS agentCard, resolved_at AS resolvedAt, source, added_at AS addedAt FROM agents WHERE id = ?",
);
const listAllAgents = db.prepare(
	"SELECT id, url, did, agent_card AS agentCard, resolved_at AS resolvedAt, source, added_at AS addedAt FROM agents ORDER BY added_at DESC, resolved_at DESC",
);
const upsertAgent = db.prepare(`
	INSERT INTO agents (id, url, did, agent_card, resolved_at, source, added_at)
	VALUES (@id, @url, @did, @agentCard, @resolvedAt, @source, @addedAt)
	ON CONFLICT(id) DO UPDATE SET
		url = COALESCE(excluded.url, agents.url),
		did = COALESCE(excluded.did, agents.did),
		agent_card = COALESCE(excluded.agent_card, agents.agent_card),
		resolved_at = excluded.resolved_at,
		source = CASE WHEN agents.source = 'manual' THEN 'manual' ELSE excluded.source END
`);

const MAX_EVENTS = 1000;
// We trim every Nth insert instead of every insert. The `DELETE … OFFSET 1000`
// query is cheap relative to the index, but at high webhook volume it still
// adds up — and the bound is soft (a buffer briefly over MAX_EVENTS does no
// harm). 32 keeps us within ~3% of the target.
const TRIM_EVERY = 32;
let insertsSinceTrim = 0;

export function recordEvent(
	id: string,
	agentId: string,
	receivedAt: string,
	payload: Record<string, unknown>,
): boolean {
	const contextId =
		typeof payload.context_id === "string" ? (payload.context_id as string) : null;
	let firstContact = false;
	if (contextId) {
		const result = upsertContext.run(agentId, contextId, receivedAt);
		firstContact = result.changes > 0;
	}
	insertEvent.run(id, agentId, receivedAt, JSON.stringify(payload), firstContact ? 1 : 0);
	if (++insertsSinceTrim >= TRIM_EVERY) {
		insertsSinceTrim = 0;
		trimEvents.run(MAX_EVENTS);
	}
	return firstContact;
}

type EventDbRow = {
	id: string;
	agentId: string;
	receivedAt: string;
	payload: string;
	firstContact: number;
};

function dbRowToEvent(r: EventDbRow): EventRow {
	return {
		id: r.id,
		agentId: r.agentId,
		receivedAt: r.receivedAt,
		payload: JSON.parse(r.payload) as Record<string, unknown>,
		firstContact: !!r.firstContact,
	};
}

export function listRecentEvents(limit = 50): EventRow[] {
	return (recentEvents.all(limit) as EventDbRow[]).map(dbRowToEvent);
}

export function readEvent(id: string): EventRow | null {
	const row = getEventById.get(id) as EventDbRow | undefined;
	return row ? dbRowToEvent(row) : null;
}

export interface AgentRecord {
	id: string;
	url?: string;
	did?: unknown;
	agentCard?: unknown;
	resolvedAt?: string;
	source?: "webhook" | "manual";
	addedAt?: string;
}

export type TrustStatus = "verified" | "unknown" | "changed" | "invalid" | "blocked" | "unavailable";
export interface VerificationEvent {
	id: string;
	peerId: string;
	eventType: string;
	result: "accepted" | "rejected" | "observed";
	reason?: string;
	messageId?: string;
	contextId?: string;
	occurredAt: string;
}
export interface PeerTrustState {
	peerId: string;
	status: TrustStatus;
	lastVerifiedAt?: string;
	lastContactAt?: string;
	updatedAt: string;
}

const trustStatus = db.prepare("SELECT peer_id AS peerId, status, last_verified_at AS lastVerifiedAt, last_contact_at AS lastContactAt, updated_at AS updatedAt FROM peer_trust_state WHERE peer_id = ?");
const trustUpsert = db.prepare("INSERT INTO peer_trust_state (peer_id,status,last_verified_at,last_contact_at,updated_at) VALUES (@peerId,@status,@lastVerifiedAt,@lastContactAt,@updatedAt) ON CONFLICT(peer_id) DO UPDATE SET status=excluded.status,last_verified_at=COALESCE(excluded.last_verified_at, peer_trust_state.last_verified_at),last_contact_at=COALESCE(excluded.last_contact_at, peer_trust_state.last_contact_at),updated_at=excluded.updated_at");
const insertVerificationEvent = db.prepare("INSERT INTO verification_events (id,peer_id,event_type,result,reason,message_id,context_id,occurred_at) VALUES (@id,@peerId,@eventType,@result,@reason,@messageId,@contextId,@occurredAt)");
const listVerificationEvents = db.prepare("SELECT id, peer_id AS peerId, event_type AS eventType, result, reason, message_id AS messageId, context_id AS contextId, occurred_at AS occurredAt FROM verification_events WHERE peer_id = ? ORDER BY occurred_at DESC LIMIT ?");
const replayInsert = db.prepare("INSERT OR IGNORE INTO replay_protection (message_id, peer_id, seen_at) VALUES (?, ?, ?)");
const replayTrim = db.prepare("DELETE FROM replay_protection WHERE seen_at < ?");

export function readPeerTrust(peerId: string): PeerTrustState {
	const row = trustStatus.get(peerId) as PeerTrustState | undefined;
	return row ?? { peerId, status: "unknown", updatedAt: new Date().toISOString() };
}
export function writePeerTrust(peerId: string, status: TrustStatus, at: string): void {
	trustUpsert.run({ peerId, status, lastVerifiedAt: status === "verified" ? at : null, lastContactAt: at, updatedAt: at });
}
export function recordVerificationEvent(event: VerificationEvent): void {
	insertVerificationEvent.run({ ...event, reason: event.reason ?? null, messageId: event.messageId ?? null, contextId: event.contextId ?? null });
}
export function getVerificationHistory(peerId: string, limit = 100): VerificationEvent[] {
	return listVerificationEvents.all(peerId, Math.min(Math.max(limit, 1), 100)) as VerificationEvent[];
}
/** Returns false when a message id was already accepted during retention. */
export function claimMessageId(peerId: string, messageId: string, now: string, retentionSeconds: number): boolean {
	replayTrim.run(new Date(Date.parse(now) - retentionSeconds * 1000).toISOString());
	return replayInsert.run(messageId, peerId, now).changes === 1;
}

type AgentRow = {
	id: string;
	url: string | null;
	did: string | null;
	agentCard: string | null;
	resolvedAt: string | null;
	source: string | null;
	addedAt: string | null;
};

function rowToRecord(row: AgentRow): AgentRecord {
	return {
		id: row.id,
		url: row.url ?? undefined,
		did: row.did ? JSON.parse(row.did) : null,
		agentCard: row.agentCard ? JSON.parse(row.agentCard) : null,
		resolvedAt: row.resolvedAt ?? undefined,
		source: (row.source as "webhook" | "manual") ?? "webhook",
		addedAt: row.addedAt ?? undefined,
	};
}

export function readAgent(id: string): AgentRecord | null {
	const row = getAgent.get(id) as AgentRow | undefined;
	return row ? rowToRecord(row) : null;
}

export function listEcosystem(): AgentRecord[] {
	return (listAllAgents.all() as AgentRow[]).map(rowToRecord);
}

export function writeAgent(rec: AgentRecord): void {
	upsertAgent.run({
		id: rec.id,
		url: rec.url ?? null,
		did: rec.did === undefined ? null : JSON.stringify(rec.did),
		agentCard:
			rec.agentCard === undefined ? null : JSON.stringify(rec.agentCard),
		resolvedAt: rec.resolvedAt ?? null,
		source: rec.source ?? "webhook",
		addedAt: rec.addedAt ?? null,
	});
}

const deleteAgentStmt = db.prepare("DELETE FROM agents WHERE id = ?");
export function deleteAgent(id: string): boolean {
	return deleteAgentStmt.run(id).changes > 0;
}

// --- thread state (read / unread / archive) -----------------------------
// Source of truth for operator triage state, replacing the previous
// localStorage-only model. Stored per-thread (context_id), independent of
// any agentId — a thread's read/archive state spans lanes.

const stateUpdate = db.prepare(`
	INSERT INTO thread_state (context_id, read_at, unread_at, archived_at)
	VALUES (@contextId, @readAt, @unreadAt, @archivedAt)
	ON CONFLICT(context_id) DO UPDATE SET
		read_at      = COALESCE(@readAt, thread_state.read_at),
		unread_at    = COALESCE(@unreadAt, thread_state.unread_at),
		archived_at  = COALESCE(@archivedAt, thread_state.archived_at)
`);

const stateClear = db.prepare(`
	UPDATE thread_state SET
		read_at      = CASE WHEN @clearRead     = 1 THEN NULL ELSE read_at END,
		unread_at    = CASE WHEN @clearUnread   = 1 THEN NULL ELSE unread_at END,
		archived_at  = CASE WHEN @clearArchived = 1 THEN NULL ELSE archived_at END
	WHERE context_id = @contextId
`);

const stateList = db.prepare(
	"SELECT context_id AS contextId, read_at AS readAt, unread_at AS unreadAt, archived_at AS archivedAt FROM thread_state",
);

export interface ThreadStateRow {
	contextId: string;
	readAt: string | null;
	unreadAt: string | null;
	archivedAt: string | null;
}

export function markThreadRead(contextId: string): void {
	const now = new Date().toISOString();
	stateUpdate.run({ contextId, readAt: now, unreadAt: null, archivedAt: null });
	// Clearing unread_at must be explicit because the upsert above only ever
	// COALESCEs new values in.
	stateClear.run({ contextId, clearRead: 0, clearUnread: 1, clearArchived: 0 });
}

export function markThreadUnread(contextId: string): void {
	const now = new Date().toISOString();
	stateUpdate.run({ contextId, readAt: null, unreadAt: now, archivedAt: null });
	stateClear.run({ contextId, clearRead: 1, clearUnread: 0, clearArchived: 0 });
}

export function archiveThread(contextId: string): void {
	const now = new Date().toISOString();
	stateUpdate.run({ contextId, readAt: null, unreadAt: null, archivedAt: now });
}

export function unarchiveThread(contextId: string): void {
	stateUpdate.run({
		contextId,
		readAt: null,
		unreadAt: null,
		archivedAt: null,
	});
	stateClear.run({ contextId, clearRead: 0, clearUnread: 0, clearArchived: 1 });
}

export function listThreadState(): ThreadStateRow[] {
	return stateList.all() as ThreadStateRow[];
}

// --- personal agent (single row, key='me') -------------------------------
// The operator's own bindufied agent. Lifecycle:
//   configuring → starting → alive ↔ down → failed
// Persona JSON is operator-supplied. `tools` records the Pipedream Connect
// account IDs we got from the OAuth flow; the spawn step turns those
// into MCP server URLs at code-gen time.

export type PersonalAgentStatus =
	| "configuring"
	| "starting"
	| "alive"
	| "down"
	| "failed";

export interface PersonalAgentTools {
	gmail?: { accountId: string };
	notion?: { accountId: string };
}

export interface PersonalAgentRow {
	persona: Record<string, unknown>;
	tools: PersonalAgentTools;
	agentDir: string;
	did: string | null;
	url: string | null;
	pid: number | null;
	status: PersonalAgentStatus;
	lastHealth: string | null;
	createdAt: string;
	updatedAt: string;
}

const getPersonalAgent = db.prepare(
	`SELECT persona, tools, agent_dir AS agentDir, did, url, pid,
	        status, last_health AS lastHealth,
	        created_at AS createdAt, updated_at AS updatedAt
	   FROM personal_agent WHERE id = 'me'`,
);

const upsertPersonalAgent = db.prepare(`
	INSERT INTO personal_agent
		(id, persona, tools, agent_dir, did, url, pid, status, last_health, created_at, updated_at)
	VALUES
		('me', @persona, @tools, @agentDir, @did, @url, @pid, @status, @lastHealth, @createdAt, @updatedAt)
	ON CONFLICT(id) DO UPDATE SET
		persona     = excluded.persona,
		tools       = excluded.tools,
		agent_dir   = excluded.agent_dir,
		did         = excluded.did,
		url         = excluded.url,
		pid         = excluded.pid,
		status      = excluded.status,
		last_health = excluded.last_health,
		updated_at  = excluded.updated_at
`);

type PersonalAgentDbRow = {
	persona: string;
	tools: string;
	agentDir: string;
	did: string | null;
	url: string | null;
	pid: number | null;
	status: string;
	lastHealth: string | null;
	createdAt: string;
	updatedAt: string;
};

export function readPersonalAgent(): PersonalAgentRow | null {
	const row = getPersonalAgent.get() as PersonalAgentDbRow | undefined;
	if (!row) return null;
	return {
		persona: JSON.parse(row.persona) as Record<string, unknown>,
		tools: JSON.parse(row.tools) as PersonalAgentTools,
		agentDir: row.agentDir,
		did: row.did,
		url: row.url,
		pid: row.pid,
		status: row.status as PersonalAgentStatus,
		lastHealth: row.lastHealth,
		createdAt: row.createdAt,
		updatedAt: row.updatedAt,
	};
}

export function writePersonalAgent(row: PersonalAgentRow): void {
	upsertPersonalAgent.run({
		persona: JSON.stringify(row.persona),
		tools: JSON.stringify(row.tools),
		agentDir: row.agentDir,
		did: row.did,
		url: row.url,
		pid: row.pid,
		status: row.status,
		lastHealth: row.lastHealth,
		createdAt: row.createdAt,
		updatedAt: row.updatedAt,
	});
}

// --- settings (single row 'global') -------------------------------------
// Model + Pipedream credentials. Each field is nullable so the operator
// can fill them in any order. Read/write helpers deal in plain values;
// masking happens in the route layer so the DB-level API stays simple.

export interface SettingsRow {
	openrouterApiKey: string | null;
	openrouterModel: string | null;
	pipedreamProjectId: string | null;
	pipedreamClientId: string | null;
	pipedreamClientSecret: string | null;
	pipedreamEnvironment: string | null;
	updatedAt: string;
}

export type SettingsField =
	| "openrouterApiKey"
	| "openrouterModel"
	| "pipedreamProjectId"
	| "pipedreamClientId"
	| "pipedreamClientSecret"
	| "pipedreamEnvironment";

// Column names, not secret values — detect-secrets matches the
// "api_key" / "secret" substrings. Marked as false-positives inline.
const SETTINGS_COLUMNS: Record<SettingsField, string> = {
	openrouterApiKey: "openrouter_api_key", // pragma: allowlist secret
	openrouterModel: "openrouter_model", // pragma: allowlist secret
	pipedreamProjectId: "pipedream_project_id",
	pipedreamClientId: "pipedream_client_id",
	pipedreamClientSecret: "pipedream_client_secret", // pragma: allowlist secret
	pipedreamEnvironment: "pipedream_environment",
};

const getSettings = db.prepare(
	`SELECT openrouter_api_key      AS openrouterApiKey,
	        openrouter_model        AS openrouterModel,
	        pipedream_project_id    AS pipedreamProjectId,
	        pipedream_client_id     AS pipedreamClientId,
	        pipedream_client_secret AS pipedreamClientSecret,
	        pipedream_environment   AS pipedreamEnvironment,
	        updated_at              AS updatedAt
	   FROM settings WHERE id = 'global'`,
);

const upsertSettings = db.prepare(`
	INSERT INTO settings
		(id, openrouter_api_key, openrouter_model,
		 pipedream_project_id, pipedream_client_id, pipedream_client_secret,
		 pipedream_environment, updated_at)
	VALUES
		('global', @openrouterApiKey, @openrouterModel,
		 @pipedreamProjectId, @pipedreamClientId, @pipedreamClientSecret,
		 @pipedreamEnvironment, @updatedAt)
	ON CONFLICT(id) DO UPDATE SET
		openrouter_api_key      = COALESCE(excluded.openrouter_api_key,      settings.openrouter_api_key),
		openrouter_model        = COALESCE(excluded.openrouter_model,        settings.openrouter_model),
		pipedream_project_id    = COALESCE(excluded.pipedream_project_id,    settings.pipedream_project_id),
		pipedream_client_id     = COALESCE(excluded.pipedream_client_id,     settings.pipedream_client_id),
		pipedream_client_secret = COALESCE(excluded.pipedream_client_secret, settings.pipedream_client_secret),
		pipedream_environment   = COALESCE(excluded.pipedream_environment,   settings.pipedream_environment),
		updated_at              = excluded.updated_at
`);

export function readSettings(): SettingsRow {
	const row = getSettings.get() as SettingsRow | undefined;
	if (!row) {
		return {
			openrouterApiKey: null,
			openrouterModel: null,
			pipedreamProjectId: null,
			pipedreamClientId: null,
			pipedreamClientSecret: null,
			pipedreamEnvironment: null,
			updatedAt: "",
		};
	}
	return row;
}

/** Upsert any subset of fields. Missing fields are left untouched —
 * the SQL uses COALESCE so passing a single field updates only that
 * one column. */
export function writeSettings(partial: Partial<Record<SettingsField, string>>): SettingsRow {
	const now = new Date().toISOString();
	upsertSettings.run({
		openrouterApiKey: partial.openrouterApiKey ?? null,
		openrouterModel: partial.openrouterModel ?? null,
		pipedreamProjectId: partial.pipedreamProjectId ?? null,
		pipedreamClientId: partial.pipedreamClientId ?? null,
		pipedreamClientSecret: partial.pipedreamClientSecret ?? null,
		pipedreamEnvironment: partial.pipedreamEnvironment ?? null,
		updatedAt: now,
	});
	return readSettings();
}

/** Clear one field. We avoid the COALESCE upsert (which would skip
 * NULL writes) by doing a direct UPDATE.  */
export function clearSetting(field: SettingsField): SettingsRow {
	const col = SETTINGS_COLUMNS[field];
	const now = new Date().toISOString();
	db.prepare(
		`INSERT INTO settings (id, ${col}, updated_at) VALUES ('global', NULL, ?)
		 ON CONFLICT(id) DO UPDATE SET ${col} = NULL, updated_at = excluded.updated_at`,
	).run(now);
	return readSettings();
}

// --- conversation history for stateless gateway ------------------------
// Path A: comms owns durability, gateway is pure compute. On every
// /api/plan call we feed the gateway the prior turns from our own
// events log so it has context without needing its own session DB.
//
// Shape we return mirrors what the gateway's planner expects in
// `PlanRequest.history`: an array of `{role, parts}` where each part is
// a tagged-union `{type, text}`. We deliberately mint the minimum the
// planner needs — no metadata, no info blocks. If the gateway later
// wants richer per-turn info (timestamps, signatures, etc.) we can
// extend without breaking the wire.

const historyForContext = db.prepare(`
	SELECT payload, received_at AS receivedAt, agent_id AS agentId
	FROM events
	WHERE json_extract(payload, '$.context_id') = ?
	  AND json_extract(payload, '$.kind') IN ('plan-question', 'plan-reply')
	ORDER BY received_at ASC
`);

const latestSummaryForContext = db.prepare(`
	SELECT payload
	FROM events
	WHERE json_extract(payload, '$.context_id') = ?
	  AND json_extract(payload, '$.kind') = 'plan-summary'
	ORDER BY received_at DESC
	LIMIT 1
`);

export interface ConversationTurn {
	role: "user" | "assistant";
	parts: Array<{ type: "text"; text: string }>;
}

/** Load the most recent `limit` turns for a plan thread.
 *
 * `plan-question` events become user turns, `plan-reply` events become
 * assistant turns. Older turns are pruned in favour of the compaction
 * summary (see `readPriorSummary`). 30 is the chosen default — see
 * the design note in /api/plan; override via env if you ever need to
 * stress-test long histories.
 */
export function listConversationHistory(
	contextId: string,
	limit = 30,
): ConversationTurn[] {
	type Row = { payload: string; receivedAt: string; agentId: string };
	const rows = historyForContext.all(contextId) as Row[];
	const turns: ConversationTurn[] = [];
	for (const r of rows) {
		let parsed: { kind?: string; text?: string };
		try {
			parsed = JSON.parse(r.payload);
		} catch {
			continue;
		}
		if (typeof parsed.text !== "string" || !parsed.text.trim()) continue;
		const role = parsed.kind === "plan-question" ? "user" : "assistant";
		turns.push({
			role,
			parts: [{ type: "text", text: parsed.text }],
		});
	}
	// Cap to the last `limit` turns. Older context survives via the
	// compaction summary the gateway emitted on a prior call.
	return turns.slice(-limit);
}

/** Latest compaction summary the gateway has emitted for this thread,
 * if any. Persisted as a `plan-summary` event under the gateway's
 * agentId. Returns undefined when no summary exists yet (cold context
 * or short conversation). */
/** Per-task latest state within a context — used by /api/compose to
 * decide whether a reply should resume an open task (input-required /
 * working / etc., per the A2A docs) or mint a new task that references
 * the prior completed/failed/canceled/rejected one via
 * `referenceTaskIds`. Without this distinction every reply minted a
 * fresh task, leaving input-required tasks paused forever and giving
 * agents no signal that a refinement was follow-up vs. a fresh ask. */
const latestTaskStatesForContext = db.prepare(`
	WITH latest AS (
		SELECT
			json_extract(payload, '$.task_id') AS task_id,
			json_extract(payload, '$.status.state') AS state,
			received_at,
			ROW_NUMBER() OVER (
				PARTITION BY json_extract(payload, '$.task_id')
				ORDER BY received_at DESC
			) AS rn
		FROM events
		WHERE json_extract(payload, '$.context_id') = ?
		  AND json_extract(payload, '$.status.state') IS NOT NULL
		  AND json_extract(payload, '$.task_id') IS NOT NULL
	)
	SELECT task_id, state
	FROM latest
	WHERE rn = 1
	ORDER BY received_at DESC
`);

export type TaskContinuation =
	| { kind: "fresh" }
	| { kind: "resume"; taskId: string }
	| { kind: "refine"; referenceTaskIds: string[] };

const OPEN_STATES = new Set([
	"submitted",
	"pending",
	"working",
	"input-required",
	"auth-required",
	"payment-required",
]);

const TERMINAL_STATES = new Set([
	"completed",
	"failed",
	"canceled",
	"rejected",
]);

/** Decide how a reply on this context should be sent.
 *
 * - `resume` when an open task exists — the reply rides the same
 *   task_id so the agent's paused execution actually resumes (the
 *   A2A docs explicitly require this for input-required).
 * - `refine` when the most recent task is terminal — the reply mints
 *   a new task that points back at the terminal one via
 *   `referenceTaskIds`, giving the agent a signal that this is a
 *   follow-up to prior work rather than a cold request.
 * - `fresh` when there are no task-bearing events in this context
 *   yet (e.g. a brand-new conversation, or a thread whose only
 *   events are gateway plumbing).
 */
export function resolveTaskContinuation(contextId: string): TaskContinuation {
	type Row = { task_id: string; state: string };
	const rows = latestTaskStatesForContext.all(contextId) as Row[];
	if (rows.length === 0) return { kind: "fresh" };
	for (const r of rows) {
		if (OPEN_STATES.has(r.state)) {
			return { kind: "resume", taskId: r.task_id };
		}
	}
	const latestTerminal = rows.find((r) => TERMINAL_STATES.has(r.state));
	if (latestTerminal) {
		return { kind: "refine", referenceTaskIds: [latestTerminal.task_id] };
	}
	return { kind: "fresh" };
}

export function readPriorSummary(contextId: string): string | undefined {
	const row = latestSummaryForContext.get(contextId) as
		| { payload: string }
		| undefined;
	if (!row) return undefined;
	try {
		const parsed = JSON.parse(row.payload) as { text?: unknown };
		if (typeof parsed.text === "string" && parsed.text.trim()) {
			return parsed.text;
		}
	} catch {
		/* malformed payload — treat as missing */
	}
	return undefined;
}
