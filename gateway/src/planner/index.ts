import { Context, Effect, Layer } from "effect"
import { randomUUID } from "crypto"
import { z } from "zod"
import { Service as SessionService, type MessageWithParts } from "../session"
import { Service as SessionPromptService } from "../session/prompt"
import { Service as SessionCompactionService } from "../session/compaction"
import { Service as BusService } from "../bus"
import { Service as BinduClientService } from "../bindu/client"
import { Service as AgentService } from "../agent"
import * as Recipe from "../recipe"
import { buildLoadRecipeTool } from "../tool/recipe"
import type { Def } from "../tool/tool"
import type { PeerDescriptor } from "../bindu/client"
import type { PeerAuth } from "../bindu/auth/resolver"
import { newMessageID, type SessionID } from "../session/schema"
import { buildSkillTool } from "./skill-tool"
import { buildPriorTaskIdLookup } from "./task-continuity"

/**
 * Planner — turns External's agent catalog into dynamic tools, then runs
 * `SessionPrompt.prompt` with them to answer the user's question.
 *
 * This is the thin layer that adapts a single /plan request into one
 * agent-loop turn. The heavy logic (loop, streaming, tool execution) lives
 * in SessionPrompt; the Bindu network I/O lives in Client. Planner just
 * stitches them together.
 *
 * Module shape:
 *   - this file: schemas + Service + layer (the public API)
 *   - ./skill-tool: the `call_<peer>_<skill>` tool factory
 *   - ./util: pure helpers (name normalization, verified-label logic,
 *     json-schema→zod, <remote_content> envelope)
 *
 * Phase 0 learning applied: peer URL comes from the caller's agent.endpoint,
 * never from AgentCard.url. Caller is the single source of truth for where
 * to reach a given agent.
 */

// Re-export util/skill-tool surface so callers and tests can import from
// `../planner` regardless of the internal file split.
export {
  normalizeToolName,
  findDuplicateToolIds,
  extractPlainTextInput,
  extractOutputText,
  computeVerifiedLabel,
  wrapRemoteContent,
  jsonSchemaToZod,
} from "./util"
export type { ToolIdCollision, VerifiedLabel } from "./util"
export type { BuildToolDeps } from "./skill-tool"

// --------------------------------------------------------------------
// Plan request shape (matches PLAN.md §API)
// --------------------------------------------------------------------

// External /plan API — agent auth descriptor.
//
// Must stay in sync with ``PeerAuth`` in ``src/bindu/auth/resolver.ts``.
// They're two schemas for the same concept: PeerAuthRequest validates
// the incoming /plan request, PeerAuth is the internal shape the peer
// resolver understands. Drift between them causes silent acceptance of
// auth types the transport can't actually execute (or, as happened
// before this comment, the reverse: /plan rejects auth types the
// transport fully supports).
export const PeerAuthRequest = z.discriminatedUnion("type", [
  z.object({ type: z.literal("none") }),
  z.object({ type: z.literal("bearer"), token: z.string() }),
  z.object({ type: z.literal("bearer_env"), envVar: z.string() }),
  z.object({
    type: z.literal("did_signed"),
    // Optional — see PeerAuth in resolver.ts for the full semantics.
    // Omit to use the gateway's auto-acquired Hydra token.
    tokenEnvVar: z.string().optional(),
  }),
])

export const SkillRequest = z.object({
  id: z.string(),
  description: z.string().optional(),
  inputSchema: z.unknown().optional(),
  outputModes: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
})
export type SkillRequest = z.infer<typeof SkillRequest>

export const AgentRequest = z.object({
  name: z.string(),
  endpoint: z.string().url(),
  auth: PeerAuthRequest.optional(),
  trust: z
    .object({
      verifyDID: z.boolean().optional(),
      pinnedDID: z.string().optional(),
    })
    .optional(),
  skills: z.array(SkillRequest).default([]),
})
export type AgentRequest = z.infer<typeof AgentRequest>

// Preferences on /plan — keys match the documented external API shape
// in gateway/openapi.yaml §PlanPreferences: snake_case. An earlier draft
// declared them camelCase (``responseFormat``/``maxHops``/``timeoutMs``/``maxSteps``);
// clients sending docs-compliant ``max_steps`` landed on undefined
// silently via ``.passthrough()``, dropping the cap and falling back
// to ``plannerAgent.steps``. Aligning the schema with the docs fixes
// the silent discard. ``.passthrough()`` stays so forward-compat
// extra keys don't break old clients.
//
// ``timeout_ms`` semantics: overall wall-clock budget for the /plan
// call. On expiry, the planner aborts in-flight LLM + peer calls and
// returns ``BinduError.aborted("deadline", …)``. Defaults and ceiling
// are enforced in ``runPlan`` (see DEFAULT_PLAN_DEADLINE_MS /
// MAX_PLAN_DEADLINE_MS below). Validation ensures requests above the
// ceiling fail fast at the API boundary rather than being silently
// clamped — callers with genuine multi-hour workloads know to ask.
export const PlanPreferences = z
  .object({
    response_format: z.string().optional(),
    max_hops: z.number().int().positive().optional(),
    timeout_ms: z
      .number()
      .int()
      .min(1000, "timeout_ms must be at least 1000 ms")
      .max(21_600_000, "timeout_ms cannot exceed 21600000 ms (6 hours)")
      .optional(),
    max_steps: z.number().int().positive().optional(),
  })
  .partial()
  .passthrough()

/** Default overall plan deadline when ``preferences.timeout_ms`` is
 *  unset. 30 min covers ordinary multi-step plans; research workloads
 *  that need longer must set ``timeout_ms`` explicitly. Omission must
 *  still be bounded — otherwise a single hung peer reintroduces the
 *  ``poll-budget-unbounded-wall-clock`` bug. */
export const DEFAULT_PLAN_DEADLINE_MS = 30 * 60 * 1000

/** Hard ceiling on ``preferences.timeout_ms``. Matches the schema
 *  validator above — declared twice on purpose: the Zod cap rejects
 *  over-ceiling requests at the API boundary, this constant documents
 *  the contract for internal callers constructing PlanRequests
 *  programmatically. */
export const MAX_PLAN_DEADLINE_MS = 6 * 60 * 60 * 1000

/** History turn shape — what the client sends on each /plan call so
 * the gateway doesn't need its own session DB. Mirrors the planner's
 * internal MessageWithParts shape, minus the metadata bookkeeping. */
const HistoryPart = z.object({
  type: z.literal("text"),
  text: z.string(),
})
const HistoryTurn = z.object({
  role: z.enum(["user", "assistant"]),
  parts: z.array(HistoryPart).min(1),
})
export type HistoryTurn = z.infer<typeof HistoryTurn>

export const PlanRequest = z.object({
  // Non-empty — Anthropic (and some other providers) reject an empty
  // user message with a 400 mid-stream, which surfaces to the caller
  // as a vague ``"Provider returned error"``. Validating here gives
  // a clean 400 with ``invalid_request`` at the API boundary instead.
  question: z.string().min(1, "question must be a non-empty string"),
  agents: z.array(AgentRequest).default([]),
  preferences: PlanPreferences.optional(),
  session_id: z.string().optional(),
  /** Path A — client-owned history. When provided, the gateway runs
   * stateless for this call: prior turns come from the request body
   * rather than a session DB lookup. Last N turns from the caller's
   * record; older context survives via `prior_summary`. */
  history: z.array(HistoryTurn).optional(),
  /** Compaction summary the gateway emitted on a prior call to this
   * session, persisted by the client. Prepended to the prompt as a
   * synthetic user turn so the planner can still reference earlier
   * conversation that was compacted away. */
  prior_summary: z.string().optional(),
  /** Per-recipient task-id continuity. Optional `{peerName: taskId}` map
   * the client supplies based on its own event log — the most recent
   * A2A `taskId` it observed for each peer in this thread on prior /plan
   * calls. The planner threads each entry into the next outbound
   * `callPeer` as `referenceTaskIds: [taskId]`, so stateful agents see
   * the new task chained to its predecessor and can recover prior
   * artifacts/state. Path A's `history` is text-only and can't carry
   * tool metadata, hence this side-channel. */
  prior_task_ids: z.record(z.string(), z.string()).optional(),
})
export type PlanRequest = z.infer<typeof PlanRequest>

// --------------------------------------------------------------------
// Planner service
// --------------------------------------------------------------------

/**
 * Session-identity slice of a plan request. Exposed via prepareSession so
 * the /plan SSE handler can learn sessionID BEFORE runPlan starts
 * publishing — required for sessionID-filtered subscribers, which prevent
 * concurrent plans from leaking frames into each other's SSE streams.
 */
export interface SessionContext {
  sessionID: SessionID
  externalSessionID: string | null
  /** true if we resumed an existing row, false if we just created one. */
  existing: boolean
}

export interface RunPlanOutcome {
  message: MessageWithParts
}

export interface StartPlanOutcome extends RunPlanOutcome {
  sessionID: SessionID
  externalSessionID: string | null
}

export interface Interface {
  /** Resolve (create or resume) the session only. No LLM work, no events. */
  readonly prepareSession: (request: PlanRequest) => Effect.Effect<SessionContext, Error>
  /** Run compaction + the prompt loop against an already-resolved session. */
  readonly runPlan: (
    ctx: SessionContext,
    request: PlanRequest,
    opts?: { abort?: AbortSignal },
  ) => Effect.Effect<RunPlanOutcome, Error>
  /** Convenience: prepareSession + runPlan in one shot. */
  readonly startPlan: (
    request: PlanRequest,
    opts?: { abort?: AbortSignal },
  ) => Effect.Effect<StartPlanOutcome, Error>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Planner") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const sessions = yield* SessionService
    const prompt = yield* SessionPromptService
    const compaction = yield* SessionCompactionService
    const bus = yield* BusService
    const client = yield* BinduClientService
    const agents = yield* AgentService
    const recipes = yield* Recipe.Service

    /**
     * Per-session serialization lock.
     *
     * Two concurrent /plan requests on the same session_id used to both
     * append messages to gateway_messages without coordination. The
     * second LLM call could observe the first's half-written tool_use
     * before its paired tool_result, breaking Anthropic / OpenAI's
     * tool-pairing invariant and corrupting the on-disk history.
     *
     * We serialize at the application layer: each call chains onto the
     * previous one's promise. The second caller waits for the first to
     * finish (success, failure, or abort) before its own runPlanBody
     * starts. Frame-level isolation between concurrent /plan calls on
     * DIFFERENT sessions is unaffected (separate map keys).
     *
     * Limitation: this is per-process state. A horizontally-scaled
     * deployment of the gateway (multiple Node processes fronting one
     * Supabase) could still race. Single-process Phase 1 is correct;
     * Phase 2 needs a Postgres advisory lock or a version column on
     * gateway_sessions with optimistic-concurrency on the message
     * insert. Same constraint as the compaction dedupe — see
     * compaction.ts for the parallel discussion.
     */
    const sessionLocks = new Map<SessionID, Promise<unknown>>()

    const prepareSession: Interface["prepareSession"] = (request) =>
      Effect.gen(function* () {
        // Path A — client-owned history. When the caller ships
        // `history` (and optionally `prior_summary`) on the request,
        // the gateway is stateless for this call: we mint a fresh
        // session row per request and seed it with the supplied turns
        // rather than resuming the prior on-disk session. The DB row
        // is effectively per-call scratch space; Stage 5 of the
        // stateless migration will delete the DB layer entirely.
        if (request.history !== undefined) {
          const sessionRow = yield* sessions.create({
            externalSessionID: request.session_id,
            agentCatalog: request.agents,
          })
          const sessionID = sessionRow.id as unknown as SessionID

          // Prepend the client-persisted compaction summary as a
          // synthetic user turn. Mirrors how session.history() injects
          // its own summary today — same prompt format, same role
          // ("user" not "system" so we don't clobber the planner's
          // system block).
          if (request.prior_summary && request.prior_summary.trim()) {
            yield* sessions.appendUser({
              sessionID,
              parts: [
                {
                  id: newMessageID() as unknown as import("../session/schema").PartID,
                  type: "text",
                  text:
                    "[Prior session context, compacted]\n\n" +
                    request.prior_summary,
                  synthetic: true,
                  time: { start: Date.now() },
                },
              ],
            })
          }

          // Seed the provided turns. Bulk-insertion goes through the
          // same appendUser/appendAssistant code path as live writes,
          // so any future bus/audit hooks fire consistently. Order
          // matters — caller sends oldest → newest.
          for (const turn of request.history) {
            const parts = turn.parts.map((p) => ({
              id: newMessageID() as unknown as import("../session/schema").PartID,
              type: "text" as const,
              text: p.text,
              time: { start: Date.now() },
            }))
            if (turn.role === "user") {
              yield* sessions.appendUser({ sessionID, parts })
            } else {
              yield* sessions.appendAssistant({
                sessionID,
                info: {
                  id: newMessageID(),
                  sessionID,
                  role: "assistant",
                  time: { created: Date.now() },
                },
                parts,
              })
            }
          }

          return {
            sessionID,
            externalSessionID: sessionRow.external_session_id,
            existing: false,
          }
        }

        // Stateless fallback — when the caller doesn't ship `history`,
        // we mint a fresh empty session for this call. There's no
        // resumption: `session_id` becomes a correlation tag only, not
        // a key into a durable store. The previous `db.getSession()`
        // path was deleted with the DB layer.
        const sessionRow = yield* sessions.create({
          externalSessionID: request.session_id,
          agentCatalog: request.agents,
        })
        return {
          sessionID: sessionRow.id as unknown as SessionID,
          externalSessionID: sessionRow.external_session_id,
          existing: false,
        }
      })

    const runPlan: Interface["runPlan"] = (ctx, request, opts) =>
      withSessionLock(sessionLocks, ctx.sessionID, runPlanBody(ctx, request, opts))

    const runPlanBody = (
      ctx: SessionContext,
      request: PlanRequest,
      opts: { abort?: AbortSignal } | undefined,
    ): Effect.Effect<RunPlanOutcome, Error> =>
      Effect.gen(function* () {
        const plannerAgent = yield* agents.get("planner")
        if (!plannerAgent) {
          return yield* Effect.fail(new Error('planner: no "planner" agent configured'))
        }

        // Build the plan-level abort signal: client-disconnect (opts.abort)
        // OR deadline expiry, whichever fires first. The merged signal is
        // threaded into compaction, the prompt loop, and — transitively
        // via ctx.abort in each tool's execute() — every peer call's
        // sendAndPoll. A single abort stops the entire plan.
        const deadlineMs = Math.min(
          request.preferences?.timeout_ms ?? DEFAULT_PLAN_DEADLINE_MS,
          MAX_PLAN_DEADLINE_MS,
        )
        const deadline = makePlanDeadline(opts?.abort, deadlineMs)

        const model = plannerAgent.model ?? "openrouter/anthropic/claude-sonnet-4.6"
        try {
          yield* compaction
            .compactIfNeeded({
              sessionID: ctx.sessionID,
              model,
              abortSignal: deadline.signal,
            })
            .pipe(
              Effect.catch((e: Error) =>
                bus.publish(
                  { type: "planner.compaction.failed", properties: z.object({ message: z.string() }) } as any,
                  { message: e.message } as any,
                ),
              ),
            )

          const contextId = ctx.sessionID
          const tools: Def[] = []

          // Resolve the prior-task lookup for cross-turn continuity. Two
          // sources, in order:
          //   1. `request.prior_task_ids` — the client (e.g. inbox-server)
          //      explicitly tells us each peer's most-recent taskId from
          //      its own event log. Authoritative when present because
          //      the client owns the cross-call audit trail.
          //   2. Session-history walk via buildPriorTaskIdLookup. Useful
          //      in future modes where the gateway persists tool parts
          //      with metadata; harmless today (Path A history is text-
          //      only, so the walk returns no entries).
          // Errors are non-fatal: continuity is a nice-to-have, not a
          // correctness requirement — silently degrade to "fresh task
          // per call" so a load-bearing read can't kill the request.
          const priorTaskIdMap = request.prior_task_ids ?? {}
          const priorTaskIdFromHistory = yield* sessions
            .history(ctx.sessionID)
            .pipe(
              Effect.map(buildPriorTaskIdLookup),
              Effect.catch(() =>
                Effect.succeed(((_: string) => undefined) as ReturnType<typeof buildPriorTaskIdLookup>),
              ),
            )
          const priorTaskId = (peerName: string): string | undefined =>
            priorTaskIdMap[peerName] ?? priorTaskIdFromHistory(peerName)

          for (const ag of request.agents) {
            const peer: PeerDescriptor = {
              name: ag.name,
              url: ag.endpoint,
              auth: ag.auth as PeerAuth | undefined,
              trust: ag.trust,
            }
            for (const sk of ag.skills) {
              tools.push(
                buildSkillTool(peer, sk, {
                  client,
                  contextId,
                  priorTaskId: priorTaskId(ag.name),
                }),
              )
            }
          }

          // Recipes (progressive-disclosure playbooks) are filtered through
          // the planner agent's permission rules; an empty list means either
          // no recipes on disk or all denied. In either case we skip the
          // system-prompt block and the tool description falls back to
          // "no recipes available" — no noise injected.
          const recipeList = yield* recipes.available(plannerAgent)
          tools.push(buildLoadRecipeTool(recipes, recipeList))
          const recipeSummary =
            recipeList.length > 0 ? Recipe.fmt(recipeList, { verbose: true }) : undefined

          const message = yield* prompt.prompt({
            sessionID: ctx.sessionID,
            agent: "planner",
            parts: [
              {
                id: randomUUID() as any,
                type: "text",
                text: request.question,
                time: { start: Date.now() },
              },
            ],
            tools,
            modelOverride: plannerAgent.model,
            stepsOverride: request.preferences?.max_steps ?? plannerAgent.steps,
            abort: deadline.signal,
            recipeSummary,
          }).pipe(
            // Re-label a generic abort error with the deadline reason so
            // the SSE handler can tell "user gave up" from "budget
            // exceeded". Anything else passes through.
            Effect.mapError((e) => {
              if (deadline.reason === "deadline" && isAbortLikeError(e)) {
                return new PlanDeadlineExceededError(deadlineMs, e)
              }
              return e
            }),
          )

          return { message }
        } finally {
          deadline.cleanup()
        }
      })

    const startPlan: Interface["startPlan"] = (request, opts) =>
      Effect.gen(function* () {
        const ctx = yield* prepareSession(request)
        const result = yield* runPlan(ctx, request, opts)
        return {
          sessionID: ctx.sessionID,
          externalSessionID: ctx.externalSessionID,
          message: result.message,
        }
      })

    return Service.of({ prepareSession, runPlan, startPlan })
  }),
)

// --------------------------------------------------------------------
// Session serialization lock
// --------------------------------------------------------------------

/**
 * Serialize execution of `inner` by sessionID. If another call is
 * already holding the lock for this session, this one waits — chained
 * onto the previous tail — and proceeds when the prior holder finishes
 * (success, failure, or interruption).
 *
 * Implementation is a per-key promise chain: each caller installs a
 * fresh promise as the new tail, awaits the prior tail (errors
 * swallowed so a failed prior caller doesn't poison the chain), then
 * runs `inner`. `Effect.ensuring` releases the lock unconditionally,
 * so an interrupted runPlan does not deadlock subsequent callers. The
 * tail entry is removed only if it's still ours — if a later caller
 * already chained on, the entry stays so they can find it.
 *
 * Exported for the regression test, which exercises the same wrapper
 * shape against a hand-rolled producer (mirrors compaction-dedupe.test.ts).
 */
export const withSessionLock = <R, E>(
  locks: Map<SessionID, Promise<unknown>>,
  sessionID: SessionID,
  inner: Effect.Effect<R, E>,
): Effect.Effect<R, E> =>
  Effect.suspend(() => {
    const prev = locks.get(sessionID) ?? Promise.resolve<unknown>(undefined)
    let release: () => void = () => {}
    const held = new Promise<void>((resolve) => {
      release = resolve
    })
    locks.set(sessionID, held)

    return Effect.tryPromise({
      try: () => prev.catch(() => undefined),
      catch: (e) => (e instanceof Error ? e : new Error(String(e))),
    }).pipe(
      Effect.flatMap(() => inner as Effect.Effect<R, Error>),
      Effect.ensuring(
        Effect.sync(() => {
          release()
          if (locks.get(sessionID) === held) locks.delete(sessionID)
        }),
      ),
    ) as Effect.Effect<R, E>
  })

// --------------------------------------------------------------------
// Plan-level deadline helpers
// --------------------------------------------------------------------

/**
 * Thrown when the plan's wall-clock budget
 * (``preferences.timeout_ms``, clamped to ``MAX_PLAN_DEADLINE_MS``)
 * expired before the planner loop completed. The SSE handler turns this
 * into a typed error frame so callers can distinguish a budget-exceeded
 * failure from a client-disconnect abort or a peer error.
 */
export class PlanDeadlineExceededError extends Error {
  readonly deadlineMs: number
  constructor(deadlineMs: number, cause?: unknown) {
    super(`plan deadline exceeded after ${deadlineMs} ms`, cause ? { cause } : undefined)
    this.name = "PlanDeadlineExceededError"
    this.deadlineMs = deadlineMs
  }
}

interface PlanDeadline {
  signal: AbortSignal
  /** ``"deadline"`` once the timer fired; ``"signal"`` if the caller's
   *  abort fired first; ``null`` until something fires. */
  reason: "signal" | "deadline" | null
  cleanup: () => void
}

/**
 * Merge the caller's optional abort signal with an internal deadline
 * timer into a single ``AbortSignal``. Whichever fires first wins —
 * ``reason`` records which one so the caller can pick the right error
 * shape on the way out.
 *
 * Semantically parallel to ``mergeAbort`` in
 * ``gateway/src/bindu/client/poll.ts`` but operates at the plan level,
 * not a single peer call.
 */
function makePlanDeadline(
  caller: AbortSignal | undefined,
  deadlineMs: number,
): PlanDeadline {
  const ac = new AbortController()
  const state: PlanDeadline = { signal: ac.signal, reason: null, cleanup: () => {} }

  const onCallerAbort = () => {
    if (state.reason === null) state.reason = "signal"
    ac.abort()
  }
  if (caller) {
    if (caller.aborted) {
      state.reason = "signal"
      ac.abort()
    } else {
      caller.addEventListener("abort", onCallerAbort, { once: true })
    }
  }

  let timer: ReturnType<typeof setTimeout> | null = null
  if (!ac.signal.aborted && deadlineMs > 0) {
    timer = setTimeout(() => {
      if (state.reason === null) state.reason = "deadline"
      ac.abort()
    }, deadlineMs)
  }

  state.cleanup = () => {
    if (timer) clearTimeout(timer)
    if (caller) caller.removeEventListener("abort", onCallerAbort)
  }
  return state
}

/**
 * Detect an error that likely originated from an abort — covers the
 * BinduError.aborted() we raise inside sendAndPoll, the generic
 * AbortError from fetch(), and Error("aborted") from abortableSleep.
 * Used by runPlan to decide whether to re-label the error as a
 * deadline exceeded when the deadline timer fired.
 */
function isAbortLikeError(e: unknown): boolean {
  if (!e || typeof e !== "object") return false
  const err = e as { name?: string; code?: number; message?: string }
  if (err.name === "AbortError") return true
  if (err.code === -32040 /* ErrorCode.AbortedByCaller */) return true
  if (typeof err.message === "string" && /abort/i.test(err.message)) return true
  return false
}
