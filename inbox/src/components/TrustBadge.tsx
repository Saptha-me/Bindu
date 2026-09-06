import clsx from "clsx";

export type PeerTrustStatus = "verified" | "unknown" | "changed" | "invalid" | "blocked" | "unavailable";

const meta: Record<PeerTrustStatus, { label: string; glyph: string; description: string; classes: string }> = {
	verified: { label: "Verified", glyph: "✓", description: "Identity metadata and the latest signed message were verified.", classes: "border-emerald-300 bg-emerald-50 text-emerald-800" },
	unknown: { label: "Unknown", glyph: "?", description: "This peer has not yet completed a verified signed interaction.", classes: "border-slate-300 bg-slate-50 text-slate-700" },
	changed: { label: "Changed", glyph: "⚠", description: "Peer identity metadata changed and requires operator review.", classes: "border-amber-300 bg-amber-50 text-amber-900" },
	invalid: { label: "Invalid", glyph: "✕", description: "The latest signed message failed freshness or replay verification.", classes: "border-rose-300 bg-rose-50 text-rose-800" },
	blocked: { label: "Blocked", glyph: "⊘", description: "The operator has blocked this peer.", classes: "border-rose-400 bg-rose-50 text-rose-900" },
	unavailable: { label: "Unavailable", glyph: "—", description: "Trust information is currently unavailable.", classes: "border-slate-300 bg-slate-50 text-slate-600" },
};

export function TrustBadge({ status }: { status: PeerTrustStatus }) {
	const item = meta[status];
	return <span role="status" aria-label={`${item.label}: ${item.description}`} title={item.description} className={clsx("rounded border px-1.5 py-0.5 text-[10px] font-medium", item.classes)}>{item.glyph} {item.label}</span>;
}
