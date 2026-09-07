/** Client-side mirror of an agent record returned by /api/ecosystem and
 * /api/agents/:id. Kept structurally permissive — the server is the
 * source of truth (see `server/db.ts:AgentRecord`), and the UI only
 * reads a subset of each field. */
export interface EcosystemAgent {
	id: string;
	url?: string;
	did?: {
		id?: string;
		verificationMethod?: Array<Record<string, unknown>>;
	} | null;
	agentCard?: {
		name?: string;
		capabilities?: {
			extensions?: Array<{ uri?: string }>;
		} | unknown;
		skills?: unknown;
	} | null;
	resolvedAt?: string;
	source?: "webhook" | "manual";
}

export interface PeerTrust {
	peerId: string;
	status: "verified" | "unknown" | "changed" | "invalid" | "blocked" | "unavailable";
	lastVerifiedAt?: string;
	lastContactAt?: string;
	updatedAt: string;
}
export interface VerificationEvent { id: string; eventType: string; result: "accepted" | "rejected" | "observed"; reason?: string; messageId?: string; contextId?: string; occurredAt: string; }

// --- personal agent ----------------------------------------------------
// Mirrors `server/db.ts:PersonalAgentRow`. The wizard owns the persona
// shape so we keep it flexible — server only enforces persona.name; the
// rest is a suggestion, not a requirement. Stored verbatim.

export type PersonalAgentStatus =
	| "configuring"
	| "starting"
	| "alive"
	| "down"
	| "failed";

export interface PersonalAgentOccupation {
	title?: string;
	organization?: string;
	description?: string;
}

/** Operator persona. Every field except `name` is optional so the
 * wizard can save in-progress drafts and the user can fill in only
 * what matters to them. */
export interface Persona {
	name: string;
	age?: number;
	nationality?: string;
	country_of_residence?: string;
	occupation?: PersonalAgentOccupation;
	personality_traits?: string[];
	interests?: string[];
	relationships?: string[];
	other_facts?: string[];
}

export interface PersonalAgentTools {
	gmail?: { accountId: string };
	notion?: { accountId: string };
}

export interface PersonalAgent {
	persona: Persona;
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

// --- settings ----------------------------------------------------------
// Mirrors `server/db.ts:SettingsRow` but with masking applied in
// `MaskedSettings` — what the GET endpoint returns. The `have` map lets
// the UI tell "saved but masked" from "never set" without parsing the
// masked string.

export type SettingsField =
	| "openrouterApiKey"
	| "openrouterModel"
	| "pipedreamProjectId"
	| "pipedreamClientId"
	| "pipedreamClientSecret"
	| "pipedreamEnvironment";

export interface MaskedSettings {
	openrouterApiKey: string | null;
	openrouterModel: string | null;
	pipedreamProjectId: string | null;
	pipedreamClientId: string | null;
	pipedreamClientSecret: string | null;
	pipedreamEnvironment: string | null;
	updatedAt: string;
	have: Record<SettingsField, boolean>;
}
