import { Context, Effect, Layer } from "effect"
import { createOpenAI } from "@ai-sdk/openai"
import { createAnthropic } from "@ai-sdk/anthropic"
import type { LanguageModel } from "ai"
import { Service as ConfigService, type Config } from "../config"
import type { z } from "zod"
import {
  MINIMAX_ENDPOINTS,
  normalizeMiniMaxModelId,
  type MiniMaxProtocol,
  type MiniMaxRegion,
} from "./catalog"

/**
 * Provider service - resolves a configured provider/model pair to an AI-SDK
 * language model.
 *
 * Model IDs use ``provider/modelId``. The OpenRouter path keeps its existing
 * request-body behavior, while MiniMax can use either its OpenAI-compatible
 * or Anthropic-compatible endpoint.
 *
 * On every outbound request the gateway's fetch wrapper injects two
 * OpenRouter-specific request-body fields:
 *
 *   - ``cache_control: { type: "ephemeral" }`` — enables OpenRouter's
 *     automatic-breakpoint prompt caching. Ignored by providers that
 *     don't support caching, honored by Anthropic / Gemini.
 *   - ``models: [primary, ...fallbacks]`` + ``route: "fallback"`` —
 *     if ``provider.openrouter.fallbackModels`` is configured,
 *     OpenRouter tries each model in order on transport error.
 *     Operators keep the gateway alive when a single model goes
 *     rate-limited or upstream-down without per-call retry code.
 *
 * This is a deliberate simplification compared to OpenCode's full
 * provider abstraction. For the gateway's planner we only need: given
 * a model string, give me a model handle the AI SDK can stream.
 */

const SUPPORTED_PROVIDERS = ["openrouter", "minimax"] as const
export type ProviderId = (typeof SUPPORTED_PROVIDERS)[number]

const OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

export function parseModelId(s: string): { providerId: ProviderId; modelId: string } {
  const slash = s.indexOf("/")
  if (slash === -1) {
    throw new Error(
      `provider: model id must be "provider/model" (got "${s}"). ` +
        `Example: "openrouter/anthropic/claude-sonnet-4.6".`,
    )
  }
  const providerId = s.slice(0, slash) as ProviderId
  const modelId = s.slice(slash + 1)
  if (!(SUPPORTED_PROVIDERS as readonly string[]).includes(providerId)) {
    throw new Error(
      `provider: unsupported provider "${providerId}" ` +
        `(supported: ${SUPPORTED_PROVIDERS.join(", ")})`,
    )
  }
  return { providerId, modelId }
}

/**
 * Inject OpenRouter's prompt-caching marker at the top level of a
 * chat-completions request body.
 *
 * Per OpenRouter's spec (``docs/guides/best-practices/prompt-caching``):
 *
 *   - **OpenAI / DeepSeek / Grok / Groq / Moonshot** — ignore the
 *     ``cache_control`` field. Their caching is automatic; we send the
 *     marker for consistency but it changes nothing.
 *   - **Anthropic Claude** — top-level ``cache_control`` enables
 *     OpenRouter's *automatic breakpoint* mode, where OpenRouter
 *     places cache boundaries at the end of the growing message
 *     history. This is the minimum-code, maximum-coverage option and
 *     the right default for a planner whose system prompt + tool
 *     defs stay mostly-stable across turns.
 *   - **Google Gemini 2.5** — same marker shape; OpenRouter handles.
 *
 * Adding the marker is safe across every model — providers that
 * don't understand it strip it before the upstream call.
 */
export function injectCacheControl(bodyString: string): string {
  const parsed = safeJsonParse(bodyString)
  if (!parsed) return bodyString
  if (parsed.cache_control) return bodyString // respect explicit upstream marker
  parsed.cache_control = { type: "ephemeral" }
  return JSON.stringify(parsed)
}

/**
 * Inject OpenRouter's model-fallback array into the request body.
 *
 * Per OpenRouter's routing docs: ``models: [primary, fallback1, ...]``
 * plus ``route: "fallback"`` instructs OpenRouter to try each model in
 * order, advancing to the next only if the current one errors
 * (rate-limited, upstream-down, etc.). When ``models`` is present
 * OpenRouter ignores ``model`` — we preserve the original ``model``
 * for clarity but add ``models`` in front with the primary first.
 *
 * No-ops when ``fallbackModels`` is empty (common case — no fallback
 * configured) or when the body has no ``model`` field (shouldn't
 * happen for chat-completions, but we're defensive).
 */
export function injectFallbackModels(
  bodyString: string,
  fallbackModels: readonly string[],
): string {
  if (fallbackModels.length === 0) return bodyString
  const parsed = safeJsonParse(bodyString)
  if (!parsed) return bodyString
  const primary = typeof parsed.model === "string" ? parsed.model : null
  if (!primary) return bodyString
  if (Array.isArray(parsed.models)) return bodyString // respect upstream
  parsed.models = [primary, ...fallbackModels]
  parsed.route = "fallback"
  return JSON.stringify(parsed)
}

function safeJsonParse(s: string): Record<string, unknown> | null {
  try {
    const v = JSON.parse(s)
    return v && typeof v === "object" ? (v as Record<string, unknown>) : null
  } catch {
    return null
  }
}

/** Wrap a ``fetch`` to inject cache_control + fallback models on JSON POSTs. */
function openrouterFetch(
  opts: { fallbackModels?: readonly string[] },
  inner: typeof fetch = fetch,
): typeof fetch {
  return async (input, init) => {
    if (init?.body && typeof init.body === "string") {
      let body = injectCacheControl(init.body)
      if (opts.fallbackModels && opts.fallbackModels.length > 0) {
        body = injectFallbackModels(body, opts.fallbackModels)
      }
      return inner(input, { ...init, body })
    }
    return inner(input, init)
  }
}

export interface Interface {
  readonly model: (id: string) => Effect.Effect<LanguageModel, Error>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Provider") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const config = yield* (yield* ConfigService).get()
    const providers: z.infer<typeof Config>["provider"] = config.provider

    function build(providerId: ProviderId, modelId: string): LanguageModel {
      const providerCfg = providers[providerId] as
        | {
            apiKey?: string
            baseURL?: string
            openaiBaseURL?: string
            anthropicBaseURL?: string
            region?: MiniMaxRegion
            protocol?: MiniMaxProtocol
            fallbackModels?: readonly string[]
          }
        | undefined

      if (providerId === "minimax") {
        const region = providerCfg?.region ?? "global_en"
        const protocol = providerCfg?.protocol ?? "openai"
        const endpoints = MINIMAX_ENDPOINTS[region]
        const resolvedModelId = normalizeMiniMaxModelId(modelId)

        if (protocol === "anthropic") {
          const baseURL = providerCfg?.anthropicBaseURL ?? providerCfg?.baseURL ?? endpoints.anthropicBaseURL
          if (!baseURL.endsWith("/anthropic")) {
            throw new Error('provider: MiniMax Anthropic baseURL must end with "/anthropic"')
          }
          const p = createAnthropic({ apiKey: providerCfg?.apiKey, baseURL })
          return p(resolvedModelId)
        }

        const p = createOpenAI({
          apiKey: providerCfg?.apiKey,
          baseURL: providerCfg?.openaiBaseURL ?? providerCfg?.baseURL ?? endpoints.openaiBaseURL,
        })
        return p.chat(resolvedModelId)
      }

      // OpenRouter's API is OpenAI-compatible — one @ai-sdk/openai
      // client pointed at OpenRouter's baseURL handles every model.
      //
      // IMPORTANT: use ``.chat()`` explicitly, not the default callable.
      // ``@ai-sdk/openai`` v3 defaults to OpenAI's newer Responses API
      // (``/v1/responses``). OpenRouter only implements the older Chat
      // Completions API (``/v1/chat/completions``). Using the default
      // callable produces "Invalid Responses API request" from
      // OpenRouter at the first LLM call.
      //
      // The ``fetch`` wrapper injects cache_control + fallback models.
      // See ``injectCacheControl`` + ``injectFallbackModels`` above.
      const p = createOpenAI({
        apiKey: providerCfg?.apiKey,
        baseURL: providerCfg?.baseURL ?? OPENROUTER_DEFAULT_BASE_URL,
        fetch: openrouterFetch({ fallbackModels: providerCfg?.fallbackModels }),
      })
      return p.chat(modelId)
    }

    return Service.of({
      model: (id) =>
        Effect.try({
          try: () => {
            const { providerId, modelId } = parseModelId(id)
            return build(providerId, modelId)
          },
          catch: (e) => (e instanceof Error ? e : new Error(`provider.model: ${String(e)}`)),
        }),
    })
  }),
)
