import { useEffect, useState } from "react";
import clsx from "clsx";
import { useUI } from "~/state";
import { useAllEvents } from "~/lib/hooks";
import { stateMeta, trustMeta } from "~/lib/format";
import { postJson } from "~/lib/fetch";
import type { EcosystemAgent } from "~/lib/api-types";
import type { PeerTrust, VerificationEvent } from "~/lib/api-types";
import { TrustBadge } from "./TrustBadge";
import type { DetailTab } from "~/types";

function useResolvedAgent(agentId: string | undefined): EcosystemAgent | null {
	const [data, setData] = useState<EcosystemAgent | null>(null);
	useEffect(() => {
		if (!agentId) return setData(null);
		setData(null);
		const ctrl = new AbortController();
		fetch(`/api/agents/${encodeURIComponent(agentId)}`, { signal: ctrl.signal })
			.then((r) => (r.ok ? r.json() : null))
			.then((j) => setData(j))
			.catch(() => {});
		return () => ctrl.abort();
	}, [agentId]);
	return data;
}

const TABS: { k: DetailTab; label: string; hint: string }[] = [
	{ k: "glance", label: "Glance", hint: "operator" },
	{ k: "verify", label: "Verify", hint: "auditor" },
	{ k: "inspect", label: "Inspect", hint: "developer" },
];

export function DetailRail() {
	const selectedEventId = useUI((s) => s.selectedEventId);
	const detailTab = useUI((s) => s.detailTab);
	const setDetailTab = useUI((s) => s.setDetailTab);
	const allEvents = useAllEvents();
	const event = allEvents.find((e) => e.id === selectedEventId) ?? null;

	if (!event) {
		return (
			<aside className="flex w-[400px] shrink-0 flex-col border-l border-(--color-border-soft) bg-(--color-rail)">
				<div className="flex flex-1 items-center justify-center p-6 text-center text-[12px] text-fg-dim">
					Select an event to inspect it
				</div>
			</aside>
		);
	}

	const tb = trustMeta[event.counterparty.trust];
	const sb = event.state ? stateMeta[event.state] : null;

	return (
		<aside className="flex w-[400px] shrink-0 flex-col border-l border-(--color-border-soft) bg-(--color-rail)">
			{/* Summary header */}
			<div className="border-b border-(--color-border-soft) px-5 py-4">
				<div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.15em] text-fg-dim">
					<span>{event.kind}</span>
					<span>·</span>
					<span>{event.relTs}</span>
				</div>
				<div className="mt-1 text-[13px] font-medium text-fg">
					{event.summary}
				</div>
				<div className="mt-2 flex flex-wrap items-center gap-2">
					<span
						className={clsx(
							"rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
							tb.bg,
							tb.color,
							tb.border,
						)}
					>
						{tb.label}
					</span>
					{sb && event.state && (
						<span
							className={clsx(
								"rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
								sb.bg,
								sb.color,
								sb.border,
							)}
						>
							{event.state}
						</span>
					)}
					{event.signed && (
						<span className="text-[10px] text-(--color-cobalt)">✓ signed</span>
					)}
				</div>
			</div>

			{/* Tabs */}
			<div className="flex border-b border-(--color-border-soft)">
				{TABS.map((t) => (
					<button
						key={t.k}
						type="button"
						onClick={() => setDetailTab(t.k)}
						className={clsx(
							"flex flex-1 flex-col items-center border-b-2 px-4 py-2 transition",
							detailTab === t.k
								? "border-(--color-cobalt) text-fg"
								: "border-transparent text-fg-dim hover:text-fg-muted",
						)}
					>
						<span className="text-[12px]">{t.label}</span>
						<span className="text-[9px] text-fg-dim">{t.hint}</span>
					</button>
				))}
			</div>

			{/* Body */}
			<div className="scrollbar flex-1 overflow-y-auto px-5 py-4">
				{detailTab === "glance" && <GlanceBody />}
				{detailTab === "verify" && <VerifyBody />}
				{detailTab === "inspect" && <InspectBody />}
			</div>
		</aside>
	);
}

function GlanceBody() {
	const selectedEventId = useUI((s) => s.selectedEventId);
	const event = useAllEvents().find((e) => e.id === selectedEventId);
	if (!event) return null;

	return (
		<div className="space-y-4">
			<Section label="Counterparty">
				<div className="text-[13px] text-fg">{event.counterparty.name}</div>
				<div className="break-all text-[11px] text-fg-dim">
					{event.counterparty.did}
				</div>
			</Section>

			{event.action && <ActionPanel eventId={event.id} actionKind={event.action.kind} actionLabel={event.action.label} />}
		</div>
	);
}

function VerifyBody() {
	const selectedEventId = useUI((s) => s.selectedEventId);
	const event = useAllEvents().find((e) => e.id === selectedEventId);
	const resolved = useResolvedAgent(event?.agentId);
	const [trust, setTrust] = useState<PeerTrust | null>(null);
	const [history, setHistory] = useState<VerificationEvent[]>([]);
	useEffect(() => {
		if (!event?.agentId) return;
		fetch(`/api/peers/${encodeURIComponent(event.agentId)}/trust`).then((r) => r.ok ? r.json() : null).then(setTrust).catch(() => setTrust(null));
		fetch(`/api/peers/${encodeURIComponent(event.agentId)}/verification-history`).then((r) => r.ok ? r.json() : []).then(setHistory).catch(() => setHistory([]));
	}, [event?.agentId]);
	if (!event) return null;

	const resolvedDidId = resolved?.did?.id;
	const resolvedDoc = resolved?.did
		? JSON.stringify(resolved.did, null, 2)
		: null;

	return (
		<div className="space-y-1 text-[12px]">
			<Section label="Agent trust">
				<div className="flex items-center gap-2"><TrustBadge status={trust?.status ?? "unavailable"} /><span className="text-fg-muted">{trust?.lastVerifiedAt ? `last verified ${trust.lastVerifiedAt}` : "No verified signed interaction yet."}</span></div>
			</Section>
			<VerifyRow
				label="Signature"
				value={
					event.verify.signature
						? "✓ verified"
						: "— no signature on this event (transport-authenticated only)"
				}
				ok={event.verify.signature}
				neutralWhenFalse
			/>
			<VerifyRow
				label="Resolved agent DID"
				value={resolvedDidId ?? "resolving… (or no /.well-known/did.json)"}
				ok={!!resolvedDidId}
				neutralWhenFalse
				mono
			/>
			<VerifyRow label="Event nonce" value={event.verify.nonce} ok mono />
			<VerifyRow label="Timestamp" value={event.ts} ok mono />

			<div className="mt-4 rounded-md border border-(--color-border-soft) bg-slate-50 p-3">
				<div className="text-[10px] uppercase tracking-[0.15em] text-fg-dim">
					Resolved DID document
				</div>
				{resolvedDoc ? (
					<pre className="mt-2 overflow-x-auto text-[10px] text-slate-700">{resolvedDoc}</pre>
				) : (
					<div className="mt-2 text-[11px] text-fg-dim">
						No DID document published by this agent (or comms hasn't mapped its URL).
					</div>
				)}
			</div>
			<Section label="Verification history">
				{history.length === 0 ? <div className="text-fg-dim">No verification events recorded.</div> : <ol className="space-y-2">{history.map((item) => <li key={item.id}><span className="font-medium">{item.result === "accepted" ? "✓" : "✕"} {item.eventType.replaceAll("_", " ")}</span><div className="text-fg-dim">{item.occurredAt}{item.reason ? ` — ${item.reason}` : ""}</div></li>)}</ol>}
			</Section>
		</div>
	);
}

function InspectBody() {
	const selectedEventId = useUI((s) => s.selectedEventId);
	const event = useAllEvents().find((e) => e.id === selectedEventId);
	if (!event) return null;

	return (
		<div className="space-y-4">
			<Section label="Raw JSON-RPC">
				<pre className="mt-1 overflow-x-auto rounded-md border border-(--color-border-soft) bg-slate-900 p-3 text-[10px] text-slate-100">
					{event.payload ?? "(no payload captured)"}
				</pre>
			</Section>
			<Section label="Timing">
				<div className="text-[11px] text-fg-muted">
					received {event.ts} · processed in 41ms
				</div>
			</Section>
			<Section label="Request ID">
				<div className="text-[11px] text-fg-muted">
					req_{event.id}_{event.verify.nonce}
				</div>
			</Section>
		</div>
	);
}

function ActionPanel({
	eventId,
	actionKind,
	actionLabel,
}: {
	eventId: string;
	actionKind: "approve" | "input" | "pay";
	actionLabel: string;
}) {
	const [text, setText] = useState("");
	const [status, setStatus] = useState<"idle" | "sending" | "delivered" | "recorded" | "error">("idle");
	const [errMsg, setErrMsg] = useState<string | null>(null);

	async function send(kind: "approve" | "decline" | "input" | "pay", body?: { text?: string }) {
		setStatus("sending");
		setErrMsg(null);
		const r = await postJson<{ delivered?: boolean; protocolMovePending?: boolean }>(
			`/api/events/${encodeURIComponent(eventId)}/action`,
			{ kind, ...body },
		);
		if (!r.ok) {
			setStatus("error");
			setErrMsg(r.errMsg);
			return;
		}
		if (r.data?.protocolMovePending) {
			setStatus("recorded");
		} else {
			setStatus("delivered");
			setText("");
		}
	}

	return (
		<div className="rounded-md border border-yellow-300 bg-yellow-50 p-3">
			<div className="text-[10px] uppercase tracking-[0.15em] text-yellow-800">
				Action required
			</div>
			{actionKind === "input" && (
				<textarea
					value={text}
					onChange={(e) => setText(e.target.value)}
					placeholder="Type your response…"
					rows={2}
					className="mt-2 w-full resize-none rounded-md border border-yellow-200 bg-white px-2 py-1.5 text-[12px] text-fg placeholder-fg-faint outline-none focus:border-yellow-500"
				/>
			)}
			<div className="mt-2 flex gap-2">
				<button
					type="button"
					disabled={status === "sending" || (actionKind === "input" && !text.trim())}
					onClick={() => send(actionKind, actionKind === "input" ? { text } : undefined)}
					className="rounded-md bg-(--color-sunflower) px-3 py-1.5 text-[12px] font-medium text-yellow-900 transition hover:bg-(--color-sunflower-strong) disabled:opacity-50"
				>
					{status === "sending" ? "Sending…" : actionLabel}
				</button>
				<button
					type="button"
					disabled={status === "sending"}
					onClick={() => send("decline")}
					className="rounded-md border border-(--color-border) bg-white px-3 py-1.5 text-[12px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
				>
					Decline
				</button>
			</div>
			{status === "delivered" && (
				<div className="mt-2 text-[10px] text-(--color-cobalt)">
					✓ delivered to agent
				</div>
			)}
			{status === "recorded" && (
				<div className="mt-2 text-[10px] text-fg-muted">
					✓ recorded — protocol callback not wired yet (approve/decline/pay land in a later phase)
				</div>
			)}
			{status === "error" && (
				<div className="mt-2 text-[10px] text-rose-700">✗ {errMsg}</div>
			)}
		</div>
	);
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
	return (
		<div>
			<div className="text-[10px] uppercase tracking-[0.15em] text-fg-dim">
				{label}
			</div>
			<div className="mt-1">{children}</div>
		</div>
	);
}

function VerifyRow({
	label,
	value,
	ok,
	mono,
	neutralWhenFalse,
}: {
	label: string;
	value: string;
	ok: boolean;
	mono?: boolean;
	neutralWhenFalse?: boolean;
}) {
	return (
		<div className="flex items-start justify-between gap-3 border-b border-(--color-border-soft) py-2">
			<span className="text-[10px] uppercase tracking-[0.15em] text-fg-dim">
				{label}
			</span>
			<span
				className={clsx(
					"text-right text-[11px]",
					mono && "font-mono",
					ok
						? "text-(--color-cobalt)"
						: neutralWhenFalse
							? "text-fg-muted"
							: "text-rose-700",
				)}
			>
				{value}
			</span>
		</div>
	);
}
