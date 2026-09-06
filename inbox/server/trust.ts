import { claimMessageId, readPeerTrust, recordVerificationEvent, writePeerTrust, type TrustStatus } from "./db";

const MAX_CLOCK_SKEW_SECONDS = Number(process.env.BINDU_SIGNATURE_MAX_CLOCK_SKEW_SECONDS ?? "300");
const REPLAY_RETENTION_SECONDS = Number(process.env.BINDU_REPLAY_RETENTION_SECONDS ?? "86400");

function text(payload: Record<string, unknown>, key: string): string | undefined {
	return typeof payload[key] === "string" ? payload[key] : undefined;
}

/**
 * Applies deterministic, persisted replay and freshness checks to signed
 * webhook payloads. `signatureVerified` is deliberately supplied by the
 * server-side canonical-signature verifier, never read from webhook JSON.
 */
export function assessInboundTrust(peerId: string, payload: Record<string, unknown>, now = new Date(), signatureVerified = false): TrustStatus {
	const at = now.toISOString();
	const messageId = text(payload, "message_id") ?? text(payload, "messageId");
	const contextId = text(payload, "context_id") ?? text(payload, "contextId");
	if (readPeerTrust(peerId).status === "blocked") {
		recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "peer_blocked", result: "rejected", reason: "operator blocked this peer", messageId, contextId, occurredAt: at });
		return "blocked";
	}
	const signed = signatureVerified;
	if (!signed) {
		if (payload.signature_present === true) {
			writePeerTrust(peerId, "invalid", at);
			recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "signature_failed", result: "rejected", reason: "canonical DID signature verification failed", messageId, contextId, occurredAt: at });
			return "invalid";
		}
		return "unknown";
	}
	const timestamp = text(payload, "signature_timestamp") ?? text(payload, "timestamp");
	const parsed = timestamp ? Date.parse(timestamp) : Number.NaN;
	if (!Number.isFinite(parsed) || Math.abs(now.getTime() - parsed) > MAX_CLOCK_SKEW_SECONDS * 1000) {
		writePeerTrust(peerId, "invalid", at);
		recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "timestamp_rejected", result: "rejected", reason: "signature timestamp is outside the allowed clock-skew window", messageId, contextId, occurredAt: at });
		return "invalid";
	}
	if (!messageId || !claimMessageId(peerId, messageId, at, REPLAY_RETENTION_SECONDS)) {
		writePeerTrust(peerId, "invalid", at);
		recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "replay_rejected", result: "rejected", reason: "message id was already accepted", messageId, contextId, occurredAt: at });
		return "invalid";
	}
	writePeerTrust(peerId, "verified", at);
	recordVerificationEvent({ id: crypto.randomUUID(), peerId, eventType: "signature_verified", result: "accepted", messageId, contextId, occurredAt: at });
	return "verified";
}
