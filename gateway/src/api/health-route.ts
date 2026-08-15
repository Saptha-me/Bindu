import { readFileSync } from "node:fs"
import { resolve as resolvePath, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { Effect } from "effect"
import type { Context as HonoContext } from "hono"
import { Service as ConfigService, type Config } from "../config"
import { Service as AgentService } from "../agent"
import * as Recipe from "../recipe"
import type { LocalIdentity } from "../bindu/identity/local"
import { parseDID } from "../bindu/protocol/identity"
import type { z } from "zod"

/**
 * GET /health — detailed liveness + config probe.
 *
 * Shape aligned with the per-agent Bindu health payload (the one a
 * ``bindufy()``-built agent returns), but with gateway-appropriate fields:
 *
 *   - ``gateway_id``/``gateway_did`` replace ``penguin_id``/``agent_did``.
 *     The gateway is a coordinator, not a penguin.
 *   - ``runtime`` reports gateway-specific knobs (planner model, recipe
 *     count, DID-signing status) in place of the agent's task-manager.
 *   - ``system`` reports Node/platform/arch/env.
 *
 * Everything here is synchronous / in-memory — no Supabase ping, no
 * outbound HTTP. /health must return quickly so it's usable as a
 * container liveness probe. Readiness checks that include downstream
 * connectivity should be layered on top of this endpoint, not baked
 * into it.
 */

type ConfigInfo = z.infer<typeof Config>

export interface HealthHandlerDeps {
  cfg: ConfigInfo
  plannerModel: string | null
  recipeCount: number
  identity: LocalIdentity | undefined
  hydraIntegrated: boolean
}

export interface PlannerInfo {
  /** Full provider-prefixed model id as configured (e.g.
   *  ``openrouter/anthropic/claude-sonnet-4.6``). Null when no planner
   *  agent is configured or the agent has no model set. */
  readonly model: string | null
  /** Provider segment (the bit before the first ``/``). Today that's
   *  ``openrouter`` or ``orcarouter`` — the gateway uses OpenAI-
   *  compatible gateways exclusively for LLM access. */
  readonly provider: string | null
  /** Upstream model id the provider understands (everything after the
   *  provider segment). For OpenRouter-proxied Anthropic models this
   *  is ``anthropic/claude-sonnet-4.6`` — the string you'd send to the
   *  OpenRouter API directly. */
  readonly model_id: string | null
  /** Sampling temperature configured on the planner agent (if any). */
  readonly temperature: number | null
  /** Nucleus sampling top_p configured on the planner agent (if any). */
  readonly top_p: number | null
  /** Maximum agentic loop steps per plan. Null when no cap is set. */
  readonly max_steps: number | null
}

export interface HealthResponse {
  readonly version: string
  readonly health: "healthy" | "degraded" | "unhealthy"
  readonly runtime: {
    readonly storage_backend: string
    readonly bus_backend: string
    readonly planner: PlannerInfo
    readonly recipe_count: number
    readonly did_signing_enabled: boolean
    readonly hydra_integrated: boolean
  }
  readonly application: {
    readonly name: string
    // Path A: stateless is the only mode. Kept as a single-variant
    // literal so consumers that inspect this field don't have to
    // change shape; the value just never alternates.
    readonly session_mode: "stateless"
    readonly gateway_did: string | null
    readonly gateway_id: string | null
    readonly author: string | null
  }
  readonly system: {
    readonly node_version: string
    readonly platform: string
    readonly architecture: string
    readonly environment: string
  }
  readonly status: "ok" | "error"
  readonly ready: boolean
  readonly uptime_seconds: number
}

/**
 * Split ``<provider>/<model-id>`` into its two halves. Provider is
 * everything up to the first ``/``; model id is the rest. Safe for
 * multi-segment model ids like ``openrouter/anthropic/claude-sonnet-4.6``
 * where model_id preserves the remaining slashes.
 */
export function splitModelId(
  model: string | null,
): { provider: string | null; modelId: string | null } {
  if (!model) return { provider: null, modelId: null }
  const idx = model.indexOf("/")
  if (idx < 0) return { provider: null, modelId: model }
  return { provider: model.slice(0, idx), modelId: model.slice(idx + 1) }
}

/**
 * Read the gateway's package.json version at startup. Synchronous by
 * design — we want this at server-init time, not per-request. If the
 * file can't be read (unusual install layouts), fall back to
 * ``0.0.0-unknown`` so the endpoint stays live.
 */
function readPackageVersion(): string {
  try {
    // import.meta.url is the URL of this compiled file; walk up to the
    // gateway package root.
    const here = dirname(fileURLToPath(import.meta.url))
    const candidates = [
      resolvePath(here, "../../package.json"), // from src/api/
      resolvePath(here, "../package.json"), // from dist/api/ (future build)
    ]
    for (const p of candidates) {
      try {
        const raw = readFileSync(p, "utf8")
        const parsed = JSON.parse(raw) as { version?: unknown; name?: unknown }
        if (parsed.name === "@bindu/gateway" && typeof parsed.version === "string") {
          return parsed.version
        }
      } catch {
        /* try next candidate */
      }
    }
  } catch {
    /* fall through */
  }
  return "0.0.0-unknown"
}

/**
 * Extract the short gateway id from a DID. For ``did:bindu:…:name:<hex>``
 * this is the final segment (typically a UUID-ish hash of the public
 * key). For ``did:key:…`` we return the multibase portion. Returns
 * ``null`` for anything we can't parse.
 *
 * Exported so unit tests can pin the mapping without driving the full
 * handler layer graph.
 */
export function deriveGatewayId(did: string | undefined): string | null {
  if (!did) return null
  const parsed = parseDID(did)
  if (!parsed) return null
  if (parsed.method === "bindu") return parsed.agentId
  if (parsed.method === "key") return parsed.publicKeyMultibase
  return null
}

/**
 * Extract the author segment from a did:bindu. LocalIdentity doesn't
 * expose author at runtime — it's baked into the DID at registration
 * time — so we recover it by parsing. Returns ``null`` for did:key,
 * non-Bindu DIDs, or when no identity is configured.
 */
export function deriveAuthor(did: string | undefined): string | null {
  if (!did) return null
  const parsed = parseDID(did)
  if (!parsed || parsed.method !== "bindu") return null
  return parsed.author
}

/**
 * Build the handler with everything needed for the response baked in.
 * The Effect factory collects the service references once at boot; the
 * returned Hono handler is a closure and can serve many requests
 * without allocating.
 */
export const buildHealthHandler = (identity: LocalIdentity | undefined, hydraIntegrated: boolean) =>
  Effect.gen(function* () {
    const cfg = yield* (yield* ConfigService).get()
    const agent = yield* AgentService
    const recipe = yield* Recipe.Service

    const plannerAgent = yield* agent.get("planner")
    const recipeList = yield* recipe.list()

    const bootTime = Date.now()
    const version = readPackageVersion()
    const plannerModel = plannerAgent?.model ?? null
    const { provider: plannerProvider, modelId: plannerModelId } = splitModelId(plannerModel)
    const plannerInfo: PlannerInfo = {
      model: plannerModel,
      provider: plannerProvider,
      model_id: plannerModelId,
      temperature: plannerAgent?.temperature ?? null,
      top_p: plannerAgent?.topP ?? null,
      max_steps: plannerAgent?.steps ?? null,
    }
    const recipeCount = recipeList.length
    const didSigningEnabled = Boolean(identity)

    const gatewayDid = identity?.did ?? null
    const gatewayId = deriveGatewayId(identity?.did)
    const author = deriveAuthor(identity?.did)
    const environment = process.env.NODE_ENV?.trim() || "development"

    return (c: HonoContext) => {
      const uptimeSeconds = Math.round(((Date.now() - bootTime) / 1000) * 100) / 100

      // Health classification. Keep this conservative — `/health` runs
      // without network calls, so we can only report what we know at
      // boot + invariants that can drift at runtime. Today those are:
      //   * `plannerModel` must exist — an agents/planner.md that
      //     resolves a model is required for every plan.
      //   * Nothing else truly breaks in-memory; Supabase/OpenRouter/
      //     Hydra failures manifest at call time, not here.
      const plannerOk = plannerModel !== null
      const ready = plannerOk
      const health: HealthResponse["health"] = plannerOk ? "healthy" : "unhealthy"
      const status: HealthResponse["status"] = plannerOk ? "ok" : "error"

      const body: HealthResponse = {
        version,
        health,
        runtime: {
          // Path A: gateway is stateless. No Supabase, no Postgres, no
          // local SQLite — sessions live in-process for the duration
          // of each /plan call and the canonical record is on the
          // client. Reported as "stateless" so operators don't go
          // looking for a DB connection.
          storage_backend: "stateless",
          bus_backend: "EffectPubSub",
          planner: plannerInfo,
          recipe_count: recipeCount,
          did_signing_enabled: didSigningEnabled,
          hydra_integrated: hydraIntegrated,
        },
        application: {
          name: "@bindu/gateway",
          session_mode: "stateless",
          gateway_did: gatewayDid,
          gateway_id: gatewayId,
          author,
        },
        system: {
          node_version: process.version,
          platform: process.platform,
          architecture: process.arch,
          environment,
        },
        status,
        ready,
        uptime_seconds: uptimeSeconds,
      }

      // Return 200 even when degraded/unhealthy — /health is an
      // information endpoint, not a gate. Consumers that want an HTTP
      // status signal can check `status` / `ready` in the body, or
      // wire a readiness endpoint separately.
      return c.json(body, 200)
    }
  })
