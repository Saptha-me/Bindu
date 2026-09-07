import assert from "node:assert/strict";
import { after, test } from "node:test";
import { existsSync, rmSync } from "node:fs";

const path = "/tmp/bindu-inbox-trust-test.db";
process.env.BINDU_COMMS_DB = path;
if (existsSync(path)) rmSync(path);
const { assessInboundTrust } = await import("./trust.ts");
const { getVerificationHistory, readPeerTrust, writePeerTrust } = await import("./db.ts");
const now = new Date("2026-09-06T12:00:00.000Z");
const valid = { signature_present: true, signature_timestamp: now.toISOString(), message_id: "message-one", context_id: "context-one" };

test("accepts a fresh canonical-signature verification result", () => {
	assert.equal(assessInboundTrust("peer", valid, now, true), "verified");
	assert.equal(readPeerTrust("peer").status, "verified");
});
test("records a failed signature", () => {
	assert.equal(assessInboundTrust("tampered", { ...valid, message_id: "tampered" }, now), "invalid");
	assert.equal(getVerificationHistory("tampered")[0]?.eventType, "signature_failed");
});
test("rejects stale signatures", () => {
	assert.equal(assessInboundTrust("stale", { ...valid, message_id: "stale", signature_timestamp: "2026-09-06T11:50:00.000Z" }, now, true), "invalid");
	assert.equal(getVerificationHistory("stale")[0]?.eventType, "timestamp_rejected");
});
test("rejects replayed message ids", () => {
	assert.equal(assessInboundTrust("replay", { ...valid, message_id: "replayed" }, now, true), "verified");
	assert.equal(assessInboundTrust("replay", { ...valid, message_id: "replayed" }, now, true), "invalid");
	assert.ok(getVerificationHistory("replay").some((event) => event.eventType === "replay_rejected"));
});
test("does not silently re-verify an operator-blocked peer", () => {
	writePeerTrust("blocked", "blocked", now.toISOString());
	assert.equal(assessInboundTrust("blocked", { ...valid, message_id: "blocked-message" }, now, true), "blocked");
	assert.equal(readPeerTrust("blocked").status, "blocked");
});
after(() => { if (existsSync(path)) rmSync(path); });
