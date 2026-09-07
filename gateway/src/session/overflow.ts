import type { MessageWithParts } from "./message"
import { MINIMAX_MODELS } from "../provider/catalog"

/**
 * Token accounting + overflow detection for session history.
 *
 * Phase 1 keeps the accounting approximate — we use the `tokens` field
 * already tracked on assistant messages (populated from the LLM's finish
 * event). User messages and tool inputs/outputs are estimated by a cheap
 * char-count heuristic.
 *
 * OpenCode's `session/overflow.ts` uses the provider's declared `context`
 * and `input` limits. We do the same but read those from config instead of
 * from a Provider.Model (our provider service is thinner).
 */

export interface OverflowThreshold {
  /** Model-level context window in tokens. */
  contextWindow: number
  /** Reserve this many tokens for the next response. */
  reserveForOutput: number
  /** Compact when usage exceeds this fraction of (contextWindow - reserve). */
  triggerFraction: number
}

/**
 * Context-window lookup for the models we commonly run the planner
 * against, keyed by ``provider/modelId`` (i.e. the gateway's model
 * identifier). When the planner's model isn't in this table we fall
 * back to ``DEFAULT_THRESHOLD``, which is a conservative 128k — smaller
 * than every modern default, so compaction kicks in early rather than
 * letting the caller hit a provider-side ``context_length_exceeded``.
 *
 * The table is intentionally short. Adding a new entry is cheap (one
 * line + its context window), and operators who run exotic models can
 * override via ``gateway.config.json.agent.planner.contextWindow`` or
 * pass a custom ``threshold`` to ``compactIfNeeded``.
 *
 * **Numbers come from each provider's published model card**, not
 * guesses. Bindu's planner has historically assumed Claude Opus 200k
 * even after switching to different models — see
 * ``bugs/known-issues.md#context-window-hardcoded`` for the incident
 * history this table fixes.
 */
const CONTEXT_WINDOW_BY_MODEL: Record<string, number> = {
  // Anthropic — 200k across the 4.x line
  "anthropic/claude-opus-4-7": 200_000,
  "anthropic/claude-opus-4-6": 200_000,
  "anthropic/claude-opus-4-5": 200_000,
  "anthropic/claude-sonnet-4-6": 200_000,
  "anthropic/claude-sonnet-4-5": 200_000,
  "anthropic/claude-haiku-4-5": 200_000,

  // OpenAI
  "openai/gpt-4o": 128_000,
  "openai/gpt-4o-mini": 128_000,
  "openai/gpt-4.1": 1_047_576,
  "openai/gpt-4.1-mini": 1_047_576,
  "openai/o3": 200_000,
  "openai/o3-mini": 200_000,

  // MiniMax
  "minimax/MiniMax-M3": MINIMAX_MODELS[0].contextWindow,
  "minimax/MiniMax-M2.7": MINIMAX_MODELS[1].contextWindow,
}

export const DEFAULT_THRESHOLD: OverflowThreshold = {
  // 128k — smaller than every common default. Compaction fires
  // earlier than strictly necessary for larger-window models, which
  // costs a summarization call but never triggers a provider-side
  // overflow rejection. See CONTEXT_WINDOW_BY_MODEL above for the
  // happy path where the model is known.
  contextWindow: 128_000,
  reserveForOutput: 16_000,
  triggerFraction: 0.8,
}

/**
 * Resolve the right overflow threshold for a given planner model.
 *
 * Resolution order (first match wins):
 *   1. Explicit ``override`` the caller passed (used by tests and by
 *      operators with unusual models — pass
 *      ``gateway.config.json.agent.planner.contextWindow``).
 *   2. Lookup in ``CONTEXT_WINDOW_BY_MODEL`` by the full
 *      ``provider/modelId`` key.
 *   3. ``DEFAULT_THRESHOLD`` as the conservative fallback.
 *
 * The returned threshold keeps the other two fields
 * (``reserveForOutput``, ``triggerFraction``) at their conservative
 * defaults unless the override supplies replacements.
 */
export function thresholdForModel(
  model: string,
  override?: Partial<OverflowThreshold>,
): OverflowThreshold {
  const knownWindow = CONTEXT_WINDOW_BY_MODEL[model]
  return {
    contextWindow: override?.contextWindow ?? knownWindow ?? DEFAULT_THRESHOLD.contextWindow,
    reserveForOutput: override?.reserveForOutput ?? DEFAULT_THRESHOLD.reserveForOutput,
    triggerFraction: override?.triggerFraction ?? DEFAULT_THRESHOLD.triggerFraction,
  }
}

/** Very rough token estimate — 1 token ≈ 4 chars for English/code. */
export function approxTokens(text: string): number {
  if (!text) return 0
  return Math.ceil(text.length / 4)
}

export function estimatePartTokens(parts: MessageWithParts["parts"]): number {
  let total = 0
  for (const p of parts) {
    if (p.type === "text") total += approxTokens(p.text)
    if (p.type === "tool") {
      if (p.state.status === "completed") {
        total += approxTokens(p.state.output)
        total += approxTokens(JSON.stringify(p.state.input ?? ""))
      } else if (p.state.status === "error") {
        total += approxTokens(p.state.error)
      } else if ("input" in p.state) {
        total += approxTokens(JSON.stringify(p.state.input ?? ""))
      }
    }
    if (p.type === "file") total += 512 // image-ish default; file attachments rare in Phase 1
  }
  return total
}

export function estimateHistoryTokens(history: MessageWithParts[]): number {
  let total = 0
  for (const m of history) {
    if (m.info.role === "assistant" && m.info.tokens) {
      // Prefer the authoritative count when available.
      total += m.info.tokens.total || m.info.tokens.input + m.info.tokens.output
      continue
    }
    total += estimatePartTokens(m.parts)
  }
  return total
}

export function isOverflow(tokens: number, threshold: OverflowThreshold = DEFAULT_THRESHOLD): boolean {
  const usable = Math.max(0, threshold.contextWindow - threshold.reserveForOutput)
  return tokens >= usable * threshold.triggerFraction
}
